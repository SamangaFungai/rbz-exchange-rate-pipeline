"""
parse_pdf.py
Parses a single RBZ daily "RATES_DD_MONTH_YYYY.pdf" into structured rows.

Each data row has: CURRENCY [*] IDX_BID IDX_ASK IDX_MID ZWG_BID ZWG_ASK ZWG_MID

PDF text extraction sometimes splits a number with a stray space, e.g.
    ZAR 16.0043 16.0069 1 6.00560 0.5827 0.6127 0.5977
    MWK 1717.0200 1751.0000 1 ,734.01000 62.5168 67.0236 64.7702
    USD 1 1 1 .0000 26.1251 27.4649 26.7950
So we take the first two tokens as idx_bid/idx_ask, the last three as the
ZWG rates, and rejoin whatever is in between as idx_mid. Each mid value is
checked against (bid + ask) / 2 so a bad rejoin is caught, not stored.
"""

import io
import re
from datetime import datetime

import pdfplumber

# Data row: currency code (optionally like ZMW/ZMK), optional *, then numbers.
ROW_RE = re.compile(
    r"^(?P<currency>[A-Z]{3}(?:/[A-Z]{3})?)\s*\*?\s+(?P<rest>[\d.,\s]+)$"
)

# Anything that looks like it should be a data row (used to detect drops).
CANDIDATE_RE = re.compile(r"^[A-Z]{3}(?:/[A-Z]{3})?\s*\*?\s+[\d.,]")

MID_TOLERANCE = 0.005  # 0.5% allowed difference vs (bid + ask) / 2

DATE_PATTERNS = [
    # Day first: "Friday, 25 September 2026"
    (
        re.compile(r"[A-Za-z]+,\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})"),
        "%d %B %Y",
        lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}",
    ),
    # Month first: "Wednesday, August 19, 2026"
    (
        re.compile(r"[A-Za-z]+,\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})"),
        "%B %d %Y",
        lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}",
    ),
]


def _num(s):
    return float(s.replace(",", "").replace(" ", ""))


def _mid_ok(bid, ask, mid):
    expected = (bid + ask) / 2
    return abs(mid - expected) <= MID_TOLERANCE * max(abs(expected), 1e-9)


def parse_date(text):
    """Find the date line and return an ISO date string (or None)."""
    for pattern, strptime_fmt, build_str in DATE_PATTERNS:
        m = pattern.search(text)
        if m:
            dt = datetime.strptime(build_str(m), strptime_fmt)
            return dt.strftime("%Y-%m-%d")
    return None


def _parse_row(currency, rest):
    """Return a row dict, or None if the line can't be trusted."""
    toks = rest.split()
    if len(toks) < 6:
        return None
    try:
        idx_bid = _num(toks[0])
        idx_ask = _num(toks[1])
        zwg_bid, zwg_ask, zwg_mid = (_num(t) for t in toks[-3:])
        idx_mid = _num("".join(toks[2:-3]))  # rejoin a split mid value
    except ValueError:
        return None

    if not _mid_ok(idx_bid, idx_ask, idx_mid):
        return None
    if not _mid_ok(zwg_bid, zwg_ask, zwg_mid):
        return None

    return {
        "currency": currency,
        "idx_bid": idx_bid,
        "idx_ask": idx_ask,
        "idx_mid": idx_mid,
        "zwg_bid": zwg_bid,
        "zwg_ask": zwg_ask,
        "zwg_mid": zwg_mid,
    }


def parse_rates(text):
    """Parse the extracted PDF text into a list of row dicts."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        m = ROW_RE.match(line)
        if not m:
            continue
        row = _parse_row(m.group("currency"), m.group("rest"))
        if row:
            rows.append(row)
    return rows


def parse_pdf_bytes(pdf_bytes):
    """
    Given raw PDF bytes, return (date_str, rows).
    Raises ValueError if the date or rows can't be found, or if any line that
    looks like a currency row could not be parsed (so nothing is dropped
    silently).
    """
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    date_str = parse_date(text)
    rows = parse_rates(text)

    if not date_str:
        raise ValueError("Could not find a date line in the PDF text.")
    if not rows:
        raise ValueError("Could not parse any currency rows from the PDF text.")

    candidates = [
        l.strip() for l in text.splitlines() if CANDIDATE_RE.match(l.strip())
    ]
    if len(rows) < len(candidates):
        parsed = {r["currency"] for r in rows}
        missed = [c for c in candidates if c.split()[0] not in parsed]
        raise ValueError(
            f"Parsed {len(rows)} of {len(candidates)} currency lines. "
            f"Unparsed: {missed}"
        )

    return date_str, rows


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python parse_pdf.py <path-to-pdf>")
        sys.exit(1)

    with open(sys.argv[1], "rb") as f:
        date_str, rows = parse_pdf_bytes(f.read())

    print(f"Date: {date_str}")
    print(f"Parsed {len(rows)} currency rows")
    for r in rows[:5]:
        print(r)