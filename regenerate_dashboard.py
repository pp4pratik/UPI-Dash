import json, os, re, sys, urllib.request
from datetime import date

PROJECT_DIR = "/Users/pratikpujara/Downloads/Dev & Scripts/Chrome Downloads"
DASHBOARD_PATH = os.path.join(PROJECT_DIR, "upi-dashboard.html")

with open(os.path.join(PROJECT_DIR, ".env")) as f:
    for line in f:
        if line.startswith("AIRTABLE_TOKEN="):
            TOKEN = line.strip().split("=", 1)[1]

with open(os.path.join(PROJECT_DIR, "airtable_schema.json")) as f:
    SCHEMA = json.load(f)

BASE_ID = SCHEMA["baseId"]
TABLES = SCHEMA["tables"]

MON_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
MON_FULL = {'Jan':'January','Feb':'February','Mar':'March','Apr':'April','May':'May','Jun':'June',
            'Jul':'July','Aug':'August','Sep':'September','Oct':'October','Nov':'November','Dec':'December'}

def fetch_all(table_name):
    table_id = TABLES[table_name]
    records = []
    offset = None
    while True:
        url = f"https://api.airtable.com/v0/{BASE_ID}/{table_id}?pageSize=100"
        if offset:
            url += f"&offset={offset}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
        records.extend(r["fields"] for r in data["records"])
        offset = data.get("offset")
        if not offset:
            break
    return records

def iso_to_label(iso_date):
    y, m, d = iso_date.split("-")
    return f"{MON_NAMES[int(m)-1]} {y[2:]}"

def iso_to_long_label(iso_date):
    y, m, d = iso_date.split("-")
    return f"{MON_FULL[MON_NAMES[int(m)-1]]} {y}"

def month_key(iso_date):
    y, m, _ = iso_date.split("-")
    return int(y) * 12 + int(m)

def month_range(lo_iso, hi_iso):
    """All 'Mon YY' labels from lo to hi inclusive, in order."""
    y0, m0, _ = map(int, lo_iso.split("-"))
    y1, m1, _ = map(int, hi_iso.split("-"))
    out = []
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        out.append(f"{MON_NAMES[m-1]} {str(y)[2:]}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out

def js_num(v):
    if v is None:
        return "null"
    if isinstance(v, float) and v == int(v):
        return repr(v)
    return repr(v)

# ---------------- Fetch ----------------
trend = fetch_all("Monthly Trend")
app_stats = fetch_all("App Stats")
p2p_p2m = fetch_all("P2P P2M")
categories = fetch_all("Merchant Categories")
statewise = fetch_all("Statewise")
circulars_raw = fetch_all("Circulars")
autopay_reg = fetch_all("AutoPay Registrations")
autopay_exec = fetch_all("AutoPay Executions")

if not trend:
    print("No Monthly Trend data in Airtable — aborting."); sys.exit(1)

# ---------------- Monthly Trend ----------------
trend.sort(key=lambda r: r["Month"])
lo, hi = trend[0]["Month"], trend[-1]["Month"]
full_labels = month_range(lo, hi)
by_month = {iso_to_label(r["Month"]): r for r in trend}
mVol = [by_month[lbl]["Total Volume (Mn)"] if lbl in by_month else None for lbl in full_labels]
mVal = [by_month[lbl]["Total Value (Cr)"] if lbl in by_month else None for lbl in full_labels]
banks_live = trend[-1].get("Banks Live", 0)
last_month_iso = trend[-1]["Month"]
last_month_short = iso_to_label(last_month_iso)          # "Jun 26"
last_month_long = iso_to_long_label(last_month_iso)      # "June 2026"
first_month_short = iso_to_label(lo)
first_month_long = iso_to_long_label(lo)

months_js = "[" + ",".join(f"'{l}'" for l in full_labels) + "]"
mVol_js = "[" + ",".join(js_num(v) for v in mVol) + "]"
mVal_js = "[" + ",".join(js_num(v) for v in mVal) + "]"

# ---------------- App Stats (last 3 distinct months) ----------------
app_months = sorted(set(r["Month"] for r in app_stats), key=month_key)[-3:]
quarters_short = [iso_to_label(m).replace(" ", " ") for m in app_months]  # e.g. "Dec 25"
quarters_apos = [l[:3] + "'" + l[-2:] for l in quarters_short]            # e.g. "Dec'25"

apps = sorted(set(r["App Name"] for r in app_stats),
              key=lambda a: -sum(r["Volume (Mn)"] for r in app_stats if r["App Name"] == a and r["Month"] == app_months[-1]))
app_data = {}
for a in apps:
    vol, val = [], []
    for m in app_months:
        match = next((r for r in app_stats if r["App Name"] == a and r["Month"] == m), None)
        vol.append(match["Volume (Mn)"] if match else 0)
        val.append(match["Value (Cr)"] if match else 0)
    app_data[a] = {"vol": vol, "val": val}

quarters_js = "[" + ",".join(f'"{q}"' for q in quarters_apos) + "]"
appdata_js = "{\n" + ",\n".join(
    f'  "{a}":{{vol:[{",".join(js_num(v) for v in d["vol"])}], val:[{",".join(js_num(v) for v in d["val"])}]}}'
    for a, d in app_data.items()
) + "\n}"

# ---------------- Merchant Categories (top 5 by volume, latest month) ----------------
latest_cat_month = max(r["Month"] for r in categories)
cat_latest = [r for r in categories if r["Month"] == latest_cat_month and r["Description"] != "Others"]
cat_top5 = sorted(cat_latest, key=lambda r: -r["Volume (Mn)"])[:5]
categories_js = "[\n" + ",\n".join(
    f'    {{name:\'{r["Description"]}\', vol:{js_num(r["Volume (Mn)"])}, val:{js_num(r["Value (Cr)"])}}}'
    for r in cat_top5
) + "\n  ]"

# ---------------- Statewise (latest month, all rows) ----------------
latest_geo_month = max(r["Month"] for r in statewise)
geo_latest = sorted((r for r in statewise if r["Month"] == latest_geo_month), key=lambda r: -r["Volume (Mn)"])
geo_js = "[\n" + ",\n".join(
    f'    {{name:\'{r["District"].title()}\', vol:{js_num(r["Volume Share %"])}, val:{js_num(r["Value Share %"])}}}'
    for r in geo_latest
) + "\n  ]"

# ---------------- Circulars (all rows, newest first) ----------------
def circular_sort_key(r):
    fy = r.get("FY", "")
    fy_end = int(fy.split("-")[-1]) if "-" in fy else 0
    m = re.search(r"\d+", r.get("Ref", ""))
    num = int(m.group()) if m else 0
    return (-fy_end, -num)

circulars_raw.sort(key=circular_sort_key)
circulars_count = len(circulars_raw)
circulars_js = "[\n" + ",\n".join(
    f'  {{ref:\'{r["Ref"]}\', fy:\'{r["FY"]}\', title:{json.dumps(r["Title"])}}}'
    for r in circulars_raw
) + "\n]"

# ---------------- AutoPay (latest month each) ----------------
ap_reg_month = max(r["Month"] for r in autopay_reg)
reg_latest = sorted((r for r in autopay_reg if r["Month"] == ap_reg_month), key=lambda r: -r["Registrations (Mn)"])
reg_labels_js = "[" + ",".join(f"'{r['PSP']}'" for r in reg_latest) + "]"
reg_data_js = "[" + ",".join(js_num(r["Registrations (Mn)"]) for r in reg_latest) + "]"
ap_reg_month_long = iso_to_long_label(ap_reg_month)

ap_exec_month = max(r["Month"] for r in autopay_exec)
exec_latest = sorted((r for r in autopay_exec if r["Month"] == ap_exec_month), key=lambda r: -r["Executions (Mn)"])
exec_labels_js = "[" + ",".join(f"'{r['Bank']}'" for r in exec_latest) + "]"
exec_data_js = "[" + ",".join(js_num(r["Executions (Mn)"]) for r in exec_latest) + "]"

# ---------------- Read & patch file ----------------
with open(DASHBOARD_PATH) as f:
    html = f.read()
original_html = html

def replace_var(html, varname, new_value_js, opener, closer):
    pattern = re.compile(r'var\s+' + re.escape(varname) + r'\s*=\s*' + re.escape(opener) + r'.*?' + re.escape(closer) + r';', re.DOTALL)
    new_stmt = f"var {varname} = {new_value_js};"
    new_html, n = pattern.subn(lambda m: new_stmt, html, count=1)
    if n != 1:
        print(f"WARNING: could not find/replace var {varname} (matches={n})")
    return new_html

html = replace_var(html, "months", months_js, "[", "]")
html = replace_var(html, "mVol", mVol_js, "[", "]")
html = replace_var(html, "mVal", mVal_js, "[", "]")
html = re.sub(r'var\s+banksLive\s*=\s*\d+;', f'var banksLive = {banks_live};', html, count=1)
html = replace_var(html, "quarters", quarters_js, "[", "]")
html = replace_var(html, "appData", appdata_js, "{", "}")
html = replace_var(html, "categories", categories_js, "[", "]")
html = replace_var(html, "geo", geo_js, "[", "]")
html = replace_var(html, "circulars", circulars_js, "[", "]")
html = re.sub(r"var\s+regLabels\s*=\s*\[.*?\];", f"var regLabels={reg_labels_js};", html, count=1, flags=re.DOTALL)
html = re.sub(r"var\s+regData\s*=\s*\[.*?\];", f"var regData={reg_data_js};", html, count=1, flags=re.DOTALL)
html = re.sub(r"var\s+execLabels\s*=\s*\[.*?\];", f"var execLabels={exec_labels_js};", html, count=1, flags=re.DOTALL)
html = re.sub(r"var\s+execData\s*=\s*\[.*?\];", f"var execData={exec_data_js};", html, count=1, flags=re.DOTALL)

# ---------------- Label / text substitutions ----------------
today_str = date.today().strftime("%-d %b %Y")

def count_occurrences(text, sub):
    return text.count(sub)

replacements = [
    ("34 circulars", f"{circulars_count} circulars"),
    ("June 2026", last_month_long),
    ("May 2026", ap_reg_month_long),
    ("Jun 2023 – Jun 2026", f"{first_month_short} – {last_month_short}"),
    ("June 2023 to June 2026", f"{first_month_long} to {last_month_long}"),
    ("Dec'25 / Mar'26 / Jun'26", " / ".join(quarters_apos)),
    ("Dec 2025, Mar 2026 and Jun 2026", ", ".join(iso_to_long_label(m) for m in app_months[:-1]) + f" and {iso_to_long_label(app_months[-1])}"),
    ("Jun 2026)", f"{last_month_short})"),
    ("26 Jul 2026", today_str),
]
for old, new in replacements:
    n = count_occurrences(html, old)
    if n == 0:
        print(f"NOTE: literal '{old}' not found (0 occurrences) — skipped")
    html = html.replace(old, new)

# Quarter labels used inside single-quoted JS strings need the apostrophe escaped;
# double-quoted JS strings and plain HTML text don't. Handle each context explicitly.
escaped_quarters = [q.replace("'", "\\'") for q in quarters_apos]
for old, new in [
    ("Dec\\'25 Vol(Mn)", f"{escaped_quarters[0]} Vol(Mn)"),
    ("Mar\\'26 Vol(Mn)", f"{escaped_quarters[1]} Vol(Mn)"),
    ("Jun\\'26 Vol(Mn)", f"{escaped_quarters[2]} Vol(Mn)"),
    ("Dec\\'25 Val(Cr)", f"{escaped_quarters[0]} Val(Cr)"),
    ("Mar\\'26 Val(Cr)", f"{escaped_quarters[1]} Val(Cr)"),
    ("Jun\\'26 Val(Cr)", f"{escaped_quarters[2]} Val(Cr)"),
]:
    if old not in html:
        print(f"NOTE: literal '{old}' not found (0 occurrences) — skipped")
    html = html.replace(old, new)
for old, new in [
    ('"Dec\'25 Vol(Mn)"', f'"{quarters_apos[0]} Vol(Mn)"'),
    ('"Mar\'26 Vol(Mn)"', f'"{quarters_apos[1]} Vol(Mn)"'),
    ('"Jun\'26 Vol(Mn)"', f'"{quarters_apos[2]} Vol(Mn)"'),
    ('"Dec\'25 Val(Cr)"', f'"{quarters_apos[0]} Val(Cr)"'),
    ('"Mar\'26 Val(Cr)"', f'"{quarters_apos[1]} Val(Cr)"'),
    ('"Jun\'26 Val(Cr)"', f'"{quarters_apos[2]} Val(Cr)"'),
]:
    if old not in html:
        print(f"NOTE: literal '{old}' not found (0 occurrences) — skipped")
    html = html.replace(old, new)

if html == original_html:
    print("WARNING: no changes were made to the file at all")

with open(DASHBOARD_PATH, "w") as f:
    f.write(html)

print("Regeneration complete.")
print(f"Latest UPI month: {last_month_long} | AutoPay month: {ap_reg_month_long} | Circulars: {circulars_count}")
