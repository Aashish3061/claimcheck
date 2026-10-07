"""Gemini wrapper: structured JSON calls, a manual function-calling loop, embeddings, and per-call cost logging.
No temperature/top_p/top_k are ever sent (deprecated 21 Jul 2026)."""
import contextvars, os, time
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError
from claimcheck import config, db

_client = None
_acc: contextvars.ContextVar = contextvars.ContextVar("acc", default=None)


class LLMError(Exception):
    pass


def client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


# ---------- per-request accounting ----------
def start_request(session_id: str | None, version: str | None = None):
    _acc.set({"session_id": session_id, "version": version or config.PIPELINE_VERSION, "rows": [],
              "cost": 0.0, "tokens": 0})


def acc() -> dict:
    a = _acc.get()
    if a is None:
        start_request(None)
        a = _acc.get()
    return a


def record(stage, model, um, latency_ms, ok=True, error_code=None, thinking=None, extra=None):
    g = lambda k: (getattr(um, k, None) or 0) if um is not None else 0
    p, o, t, c, tp = g("prompt_token_count"), g("candidates_token_count"), g("thoughts_token_count"), \
        g("cached_content_token_count"), g("tool_use_prompt_token_count")
    cost = config.cost_inr(model, p, o, t, c, tp)
    a = acc()
    a["cost"] += cost
    a["tokens"] += p + o + t + tp
    row = dict(session_id=a["session_id"], stage=stage, pipeline_version=a["version"], model=model,
               thinking_level=thinking, prompt_tokens=p, output_tokens=o, thoughts_tokens=t, cached_tokens=c,
               tool_prompt_tokens=tp, latency_ms=int(latency_ms), cost_inr=round(cost, 6), ok=ok,
               error_code=error_code)
    if extra:
        row.update(extra)
    a["rows"].append(row)
    return cost


def flush(verdict_counts: dict | None = None):
    """Write this request's rows to `runs` (best effort, never raises). No document content is logged."""
    a = _acc.get()
    if not a or not a["rows"] or not db.configured():
        return
    for r in a["rows"]:
        r.setdefault("verdict_counts", None)
    if verdict_counts:
        a["rows"][-1]["verdict_counts"] = verdict_counts
    try:
        db.insert("runs", a["rows"], timeout=8)
    except Exception:
        pass
    a["rows"] = []


# ---------- helpers ----------
def _thinking(level):
    return types.ThinkingConfig(thinking_level=types.ThinkingLevel(level.upper())) if level else None


def user(*parts) -> types.Content:
    ps = [types.Part.from_text(text=p) if isinstance(p, str) else p for p in parts]
    return types.Content(role="user", parts=ps)


def file_part(data: bytes, mime: str) -> types.Part:
    return types.Part.from_bytes(data=data, mime_type=mime)


def generate_json(stage: str, contents: list, schema: type[BaseModel], system: str, model: str | None = None,
                  thinking: str | None = None):
    model = model or config.MODELS.get(stage, config.MODELS["generate"])
    thinking = thinking if thinking is not None else config.THINKING.get(stage)
    cfg = types.GenerateContentConfig(system_instruction=system, response_mime_type="application/json",
                                      response_json_schema=schema.model_json_schema(),
                                      thinking_config=_thinking(thinking))
    msgs = [c if isinstance(c, types.Content) else user(c) for c in contents]
    last_err = "unknown"
    for attempt in range(2):
        t0 = time.time()
        try:
            resp = client().models.generate_content(model=model, contents=msgs, config=cfg)
        except Exception as e:  # network / quota / 4xx
            record(stage, model, None, (time.time() - t0) * 1000, ok=False, error_code=type(e).__name__[:40], thinking=thinking)
            last_err = f"{type(e).__name__}: {str(e)[:200]}"
            d = _retry_delay(e)
            if d:
                time.sleep(min(d, 30))
            continue
        record(stage, model, resp.usage_metadata, (time.time() - t0) * 1000, thinking=thinking)
        txt = resp.text or ""
        try:
            return schema.model_validate_json(txt)
        except ValidationError as e:
            last_err = "invalid_json"
            msgs = msgs + [types.Content(role="model", parts=[types.Part.from_text(text=txt or "{}")]),
                           user(f"That output failed validation: {str(e)[:600]}. Return corrected JSON only.")]
    raise LLMError(last_err)


def tool_loop(stage: str, system: str, first: str, fns: dict, model: str | None = None, thinking: str | None = None,
              max_rounds: int = config.MAX_TOOL_ROUNDS) -> list[dict]:
    """Manual function-calling loop. Returns the list of tool results (each a dict) gathered across rounds.
    Automatic function calling is disabled so every round's usage is logged and capped."""
    model = model or config.MODELS["reason"]
    thinking = thinking if thinking is not None else config.THINKING.get(stage)
    decls = [types.FunctionDeclaration.from_callable(client=client()._api_client, callable=f) for f in fns.values()]
    cfg = types.GenerateContentConfig(system_instruction=system, tools=[types.Tool(function_declarations=decls)],
                                      automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                                      thinking_config=_thinking(thinking))
    msgs = [user(first)]
    results = []
    for _ in range(max_rounds):
        t0 = time.time()
        try:
            resp = client().models.generate_content(model=model, contents=msgs, config=cfg)
        except Exception as e:
            record(stage, model, None, (time.time() - t0) * 1000, ok=False, error_code=type(e).__name__[:40], thinking=thinking)
            break
        record(stage, model, resp.usage_metadata, (time.time() - t0) * 1000, thinking=thinking)
        calls = resp.function_calls or []
        if not calls:
            break
        msgs.append(resp.candidates[0].content)  # keep thought signatures intact
        parts = []
        for c in calls:
            try:
                out = fns[c.name](**(c.args or {}))
            except Exception as e:
                out = {"error": f"{type(e).__name__}"}
            results.append({"tool": c.name, "args": dict(c.args or {}), "result": out})
            parts.append(types.Part.from_function_response(name=c.name, response={"result": out}))
        msgs.append(types.Content(role="user", parts=parts))
    return results


def _retry_delay(e) -> float | None:
    """Seconds to wait for a 429 (uses the API's RetryInfo when present)."""
    if getattr(e, "code", None) != 429:
        return None
    try:
        for d in (e.details or {}).get("error", {}).get("details", []):
            if d.get("@type", "").endswith("RetryInfo"):
                return float(str(d.get("retryDelay", "10s")).rstrip("s")) + 1
    except Exception:
        pass
    return 15.0


def quota_info(e) -> str:
    try:
        return "; ".join(f"{v.get('quotaMetric', '')}:{v.get('quotaId', '')}" for d in e.details["error"]["details"]
                         for v in d.get("violations", []))[:300]
    except Exception:
        return ""


def _embed_call(model, contents, attempts=6):
    for attempt in range(attempts):
        try:
            return client().models.embed_content(model=model, contents=contents,
                                                 config=types.EmbedContentConfig(output_dimensionality=config.EMBED_DIM))
        except Exception as e:
            d = _retry_delay(e)
            if d is None or attempt == attempts - 1:
                raise
            time.sleep(min(d, 45 if attempts > 2 else 3))


def embed(texts: list[str], kind: str = "query") -> list[list[float]]:
    """gemini-embedding-2 has no task_type; the task goes into the text. One vector per text is enforced:
    if a batched call returns fewer vectors (multimodal aggregation), fall back to one call per text."""
    from concurrent.futures import ThreadPoolExecutor
    model = config.MODELS["embed"]
    fmt = (lambda s: f"task: search result | query: {s}") if kind == "query" else (lambda s: f"title: none | text: {s}")
    out = []
    for i in range(0, len(texts), 20):
        batch = [fmt(t)[:24000] for t in texts[i:i + 20]]
        t0 = time.time()
        # one Content per text, so the API returns one embedding per text (a list of strings can be merged into one)
        r = _embed_call(model, [types.Content(parts=[types.Part.from_text(text=b)]) for b in batch],
                        attempts=6 if kind == "document" else 2)  # user-facing queries fail fast
        vecs = [e.values for e in r.embeddings]
        if len(vecs) != len(batch):
            with ThreadPoolExecutor(8) as ex:
                vecs = list(ex.map(lambda b: _embed_call(model, b).embeddings[0].values, batch))
        approx = sum(len(b) for b in batch) // 4  # embeddings return no usage metadata; ~4 chars/token estimate
        record("embed_" + kind, model, type("U", (), {"prompt_token_count": approx})(), (time.time() - t0) * 1000)
        out.extend(vecs)
    assert len(out) == len(texts)
    return out
