"""Supabase over REST (PostgREST). Server-only; the secret key bypasses RLS."""
import os
import httpx

TIMEOUT = 20


def configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SECRET_KEY"))


def _headers(prefer: str | None = None) -> dict:
    key = os.environ["SUPABASE_SECRET_KEY"]
    h = {"apikey": key, "Content-Type": "application/json"}
    if key.startswith("eyJ"):  # legacy JWT keys also need the Bearer header
        h["Authorization"] = "Bearer " + key
    if prefer:
        h["Prefer"] = prefer
    return h


def _url(path: str) -> str:
    return os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/" + path.lstrip("/")


def rest(method: str, path: str, json=None, params=None, prefer=None, timeout=TIMEOUT):
    r = httpx.request(method, _url(path), headers=_headers(prefer), json=json, params=params, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"supabase {method} {path} -> {r.status_code}: {r.text[:300]}")
    return r.json() if r.content else None


def rpc(fn: str, payload: dict, timeout=TIMEOUT):
    return rest("POST", f"rpc/{fn}", json=payload, timeout=timeout)


def insert(table: str, rows, upsert_on: str | None = None, timeout=TIMEOUT):
    prefer = "return=minimal"
    params = None
    if upsert_on:
        prefer = "resolution=merge-duplicates,return=minimal"
        params = {"on_conflict": upsert_on}
    return rest("POST", table, json=rows, params=params, prefer=prefer, timeout=timeout)
