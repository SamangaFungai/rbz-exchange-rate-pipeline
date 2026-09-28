import requests

MONTHS = {8: "August", 9: "September"}

def url_for(y, m, d):
    name = MONTHS[m]
    return (f"https://www.rbz.co.zw/documents/Exchange_Rates/{y}/{name}/"
            f"RATES_{d:02d}_{name.upper()}_{y}.pdf")

skipped = [(8,3),(8,4),(8,5),(8,6),(8,7),(8,10),(8,11),
           (9,1),(9,2),(9,3),(9,4),(9,7),(9,8),(9,9),(9,15)]
short = [(8,24),(9,14)]

print("=== SKIPPED DATES ===")
for m, d in skipped:
    u = url_for(2026, m, d)
    try:
        r = requests.get(u, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        print(f"2026-{m:02d}-{d:02d} | HTTP {r.status_code} | "
              f"{r.headers.get('Content-Type')} | {len(r.content)} bytes")
    except Exception as e:
        print(f"2026-{m:02d}-{d:02d} | ERROR {e}")

print("\n=== SHORT DATE PDF TEXT ===")
for m, d in short:
    u = url_for(2026, m, d)
    r = requests.get(u, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    fn = f"probe_{m:02d}_{d:02d}.pdf"
    open(fn, "wb").write(r.content)
    print(f"\n--- {fn} (HTTP {r.status_code}, {len(r.content)} bytes) ---")
    try:
        import pdfplumber
        with pdfplumber.open(fn) as pdf:
            print("Pages:", len(pdf.pages))
            print(pdf.pages[0].extract_text())
    except ImportError:
        print("pdfplumber not installed; open", fn, "in your browser instead")
    break
