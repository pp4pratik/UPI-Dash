# UPI Pulse

A single-file dashboard tracking India's UPI (Unified Payments Interface) ecosystem — monthly transaction trends, app leaderboard, merchant categories, geography, seasonality, ticket size, UPI AutoPay stats, and NPCI circulars — sourced directly from [NPCI](https://www.npci.org.in)'s published statistics, so there's no need to click through to their site for the numbers.

**[Open the dashboard](./upi-dashboard.html)** — it's a static HTML file, just open it in a browser.

## What's in this repo

| File | Purpose |
|---|---|
| `upi-dashboard.html` | The dashboard itself. Plain HTML/CSS/JS with [Chart.js](https://www.chartjs.org/) via CDN — no build step, no server. |
| `airtable_schema.json` | Base/table IDs for the Airtable base that stores the underlying data. |
| `regenerate_dashboard.py` | Pulls the latest data from Airtable and rewrites the data arrays (and related labels) inside `upi-dashboard.html`. |

## How the data flows

NPCI's live statistics pages are the ultimate source of truth. Since NPCI doesn't offer an API and blocks plain automated requests, refreshing data means:

1. Manually check NPCI's stats/circulars pages for the latest published month
   (`product/ecosystem-statistics/upi`, `circulars/upi`, `product/upi/product-statistics`)
2. Add the new month's rows to the Airtable base (schema in `airtable_schema.json`)
3. Run `regenerate_dashboard.py` to rewrite `upi-dashboard.html` from the updated Airtable data

Airtable acts as the structured, append-only store of history across months; the HTML file is a regenerated snapshot, not hand-edited.

Running the regeneration script requires an Airtable Personal Access Token (scoped to this base) in a local `.env` file as `AIRTABLE_TOKEN` — not included in this repo.

## Disclaimer

All figures are pulled from NPCI's official statistics and circulars pages. NPCI makes no warranty on the completeness or continued validity of this data, and this project is not affiliated with or endorsed by NPCI. Some derived metrics (e.g. "premiumness index", month-over-month seasonality) are computed by this dashboard, not published directly by NPCI.
