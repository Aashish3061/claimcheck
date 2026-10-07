"""Item-level chunks for Annexure I (Lists I-IV) of IRDAI/HLT/REG/CIR/193/07/2020 (pages ~26-31).
The PDF's table layout interleaves lists across page breaks (e.g. List I items 63-68 print under the List II heading),
so items are assigned by sequential numbering, not by the nearest heading: a number continuing the current list's
sequence stays in that list; '1' starts the next list."""
import re

TITLES = {1: "List I - Optional items (not payable unless the policy offers optional cover)",
          2: "List II - Items to be subsumed into room charges",
          3: "List III - Items to be subsumed into procedure charges",
          4: "List IV - Items to be subsumed into costs of treatment"}
ITEM = re.compile(r"^\s*(\d{1,2})\s+(\S.*?)\s*$")


def annexure_items(pages: list[str]) -> list[dict]:
    start = next((i for i, p in enumerate(pages) if re.search(r"ANNEXURE\s+I\b", p) and "List I" in p), None)
    if start is None:
        return []
    items, lst, nxt = [], 0, 1
    for pno in range(start, min(start + 7, len(pages))):
        for ln in pages[pno].splitlines():
            if re.match(r"^\s*ANNEXURE\s+II\b", ln):
                return _chunks(items)
            m = ITEM.match(ln)
            if m and int(m.group(1)) == nxt and lst:
                items.append([lst, nxt, m.group(2), pno + 1]); nxt += 1
            elif m and int(m.group(1)) == 1 and lst < 4:
                lst += 1; nxt = 2
                items.append([lst, 1, m.group(2), pno + 1])
            elif items and not m and (items[-1][2].count("(") > items[-1][2].count(")") or items[-1][2].count("[") > items[-1][2].count("]")):
                items[-1][2] += " " + ln.strip()
    return _chunks(items)


def _clean(t):
    return re.sub(r"\s+", " ", t).strip()


def _chunks(items):
    return [dict(chunk_id=f"irdai_standardisation_2020-L{l}-{k:03d}", doc_type="non_payable_item", list_no=l,
                 section=f"Annexure I, List {l}, item {k}", page=p,
                 content=f"IRDAI Annexure I, {TITLES[l]}: item {k}. {_clean(t)}") for l, k, t, p in items]
