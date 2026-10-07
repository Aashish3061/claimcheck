"""Guards: quotes must be verbatim substrings of stored chunks; generated text may only use numbers present in its input."""
import json, re

_TRANS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
                        " ": " ", "₹": "rs "})


def norm(s: str) -> str:
    s = (s or "").translate(_TRANS).lower()
    s = re.sub(r"\brs\.?\s*", "rs ", s)
    return re.sub(r"\s+", " ", s).strip()


def quote_ok(quote: str | None, content: str | None, min_len: int = 12) -> bool:
    if not quote or not content:
        return False
    q = norm(quote).strip(" .\"'")
    return len(q) >= min_len and q in norm(content)


_NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(\d+))?")


def numbers_in(text: str) -> set[str]:
    out = set()
    for m in _NUM.finditer(text or ""):
        whole = m.group(1).replace(",", "")
        out.add(whole if not m.group(2) or set(m.group(2)) == {"0"} else f"{whole}.{m.group(2)}")
    return out


def allowed_numbers(*objs) -> set[str]:
    return numbers_in(" ".join(json.dumps(o, ensure_ascii=False) for o in objs))


def unsupported_numbers(text: str, allowed: set[str]) -> set[str]:
    return {n for n in numbers_in(text) if n not in allowed}
