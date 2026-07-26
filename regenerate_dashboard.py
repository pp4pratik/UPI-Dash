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

def iso_to_apos_label(iso_date):
    y, m, d = iso_date.split("-")
    return f"{MON_NAMES[int(m)-1]}'{y[2:]}"

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

# ---------------- App Stats, P2P/P2M, Merchant Categories: month-selectable, 2026 only (for now) ----------------
app_months = sorted(set(r["Month"] for r in app_stats if r["Month"].startswith("2026-")), key=month_key)
months2026_short = [iso_to_apos_label(m) for m in app_months]      # "Jan'26"
months2026_full = [iso_to_long_label(m) for m in app_months]       # "January 2026"

trend_by_iso = {r["Month"]: r for r in trend}
monthTotalVol = [trend_by_iso[m]["Total Volume (Mn)"] for m in app_months]
monthTotalVal = [trend_by_iso[m]["Total Value (Cr)"] for m in app_months]

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

months2026_js = "[" + ",".join(f'"{m}"' for m in months2026_short) + "]"
months2026full_js = "[" + ",".join(f'"{m}"' for m in months2026_full) + "]"
monthtotalvol_js = "[" + ",".join(js_num(v) for v in monthTotalVol) + "]"
monthtotalval_js = "[" + ",".join(js_num(v) for v in monthTotalVal) + "]"
appdata_js = "{\n" + ",\n".join(
    f'  "{a}":{{vol:[{",".join(js_num(v) for v in d["vol"])}], val:[{",".join(js_num(v) for v in d["val"])}]}}'
    for a, d in app_data.items()
) + "\n}"

p2p_months = sorted(set(r["Month"] for r in p2p_p2m if r["Month"].startswith("2026-")), key=month_key)
p2p_by_month = {r["Month"]: r for r in p2p_p2m}
if p2p_months != app_months:
    print(f"NOTE: P2P P2M months {p2p_months} differ from App Stats months {app_months} — selector indices may not line up")
p2pdata_js = "[\n" + ",\n".join(
    f'  {{p2pVol:{js_num(p2p_by_month[m]["P2P Volume (Mn)"])}, p2pVal:{js_num(p2p_by_month[m]["P2P Value (Cr)"])}, p2mVol:{js_num(p2p_by_month[m]["P2M Volume (Mn)"])}, p2mVal:{js_num(p2p_by_month[m]["P2M Value (Cr)"])}}}'
    for m in p2p_months
) + "\n]"

cat_months = sorted(set(r["Month"] for r in categories if r["Month"].startswith("2026-")), key=month_key)
if cat_months != app_months:
    print(f"NOTE: Merchant Categories months {cat_months} differ from App Stats months {app_months} — selector indices may not line up")
cat_month_blocks = []
for m in cat_months:
    month_cats = [r for r in categories if r["Month"] == m and r["Description"] != "Others"]
    top5 = sorted(month_cats, key=lambda r: -r["Volume (Mn)"])[:5]
    entries = ", ".join(
        f'{{name:{json.dumps(r["Description"])}, vol:{js_num(r["Volume (Mn)"])}, val:{js_num(r["Value (Cr)"])}}}'
        for r in top5
    )
    cat_month_blocks.append(f"  [ {entries} ]")
categoriesbymonth_js = "[\n" + ",\n".join(cat_month_blocks) + "\n]"

# ---------------- Statewise (all 2026 months, district- or state-level per NPCI's actual publication) ----------------
geo_months = sorted(set(r["Month"] for r in statewise if r["Month"].startswith("2026-")), key=month_key)
if geo_months != app_months:
    print(f"NOTE: Statewise months {geo_months} differ from App Stats months {app_months} — selector indices may not line up")

geo_granularity = []
geo_month_blocks = []
for m in geo_months:
    month_rows = sorted((r for r in statewise if r["Month"] == m), key=lambda r: -r["Volume (Mn)"])
    # District == State (case-insensitive) signals these rows are state-level, not real districts
    is_state_level = all(r["District"].strip().upper() == r["State"].strip().upper() for r in month_rows)
    geo_granularity.append("State" if is_state_level else "District")
    entries = ", ".join(
        f'{{name:{json.dumps(r["District"].title())}, vol:{js_num(r["Volume Share %"])}, val:{js_num(r["Value Share %"])}}}'
        for r in month_rows
    )
    geo_month_blocks.append(f"  [ {entries} ]")
geo_granularity_js = "[" + ",".join(f"'{g}'" for g in geo_granularity) + "]"
geo_js = "[\n" + ",\n".join(geo_month_blocks) + "\n]"

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
    f'  {{ref:\'{r["Ref"]}\', fy:\'{r["FY"]}\', title:{json.dumps(r["Title"])}, pdf:{json.dumps(r.get("PDF URL"))}}}'
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
html = replace_var(html, "months2026", months2026_js, "[", "]")
html = replace_var(html, "months2026Full", months2026full_js, "[", "]")
html = replace_var(html, "monthTotalVol", monthtotalvol_js, "[", "]")
html = replace_var(html, "monthTotalVal", monthtotalval_js, "[", "]")
html = replace_var(html, "appData", appdata_js, "{", "}")
html = replace_var(html, "p2pData", p2pdata_js, "[", "]")
html = replace_var(html, "categoriesByMonth", categoriesbymonth_js, "[", "]")
html = replace_var(html, "geoGranularity", geo_granularity_js, "[", "]")
html = replace_var(html, "geographyByMonth", geo_js, "[", "]")
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
    ("Jan'26 – Jun'26", f"{months2026_short[0]} – {months2026_short[-1]}"),
    ("26 Jul 2026", today_str),
]
for old, new in replacements:
    n = count_occurrences(html, old)
    if n == 0:
        print(f"NOTE: literal '{old}' not found (0 occurrences) — skipped")
    html = html.replace(old, new)

# Note: "Top apps this month" / "Leaderboard" / "P2P split" / "Categories" section notes,
# and the month-select <option> list, are populated live by JS (updateMonthLabels(),
# monthSelectEl.innerHTML) from months2026Full — no HTML patching needed for those.

if html == original_html:
    print("WARNING: no changes were made to the file at all")

with open(DASHBOARD_PATH, "w") as f:
    f.write(html)

print("Regeneration complete.")
print(f"Latest UPI month: {last_month_long} | AutoPay month: {ap_reg_month_long} | Circulars: {circulars_count}")
