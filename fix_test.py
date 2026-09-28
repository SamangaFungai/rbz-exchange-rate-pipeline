import re
import pdfplumber

CODE = re.compile(r"^([A-Z]{3}(?:/[A-Z]{3})?)\s*\*?\s+(.*)$")

def to_float(s):
    return float(s.replace(",", "").replace(" ", ""))

def parse_line(line):
    m = CODE.match(line.strip())
    if not m:
        return None
    code, rest = m.groups()
    toks = rest.split()
    if len(toks) < 6:
        return None
    try:
        idx_bid = to_float(toks[0])
        idx_ask = to_float(toks[1])
        zwg_bid, zwg_ask, zwg_mid = (to_float(t) for t in toks[-3:])
        idx_mid = to_float("".join(toks[2:-3]))  # rejoin split mid index
    except ValueError:
        return None
    expected = (idx_bid + idx_ask) / 2
    ok = abs(idx_mid - expected) <= 0.005 * max(expected, 1)
    return {"currency": code, "idx_bid": idx_bid, "idx_ask": idx_ask,
            "idx_mid": idx_mid, "zwg_bid": zwg_bid, "zwg_ask": zwg_ask,
            "zwg_mid": zwg_mid, "mid_check_ok": ok}

with pdfplumber.open("probe_08_24.pdf") as pdf:
    text = pdf.pages[0].extract_text()

parsed = [r for r in (parse_line(l) for l in text.splitlines()) if r]
print("Parsed rows:", len(parsed))
for r in parsed:
    print(r["currency"], r["idx_mid"], r["zwg_mid"],
          "" if r["mid_check_ok"] else "  <-- mid index check failed")