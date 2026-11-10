# Monclova Energy Desk — Analyst Web Prototype

Standalone decision-centric web UI for electricity market procurement, dispatch, and D+7 settlement across the CENACE Monclova Load Zone. Built independently from [`experiments/`](../experiments/) purely as an interactive analyst workbench and screenshot source for the executive deck.

## Structure
- [`vendor/blueprint/`](./vendor/blueprint/): Local offline assets from Palantir **`@blueprintjs/core@6.22.0`** and **`@blueprintjs/icons@6.15.0`** (`bp6-dark` theme, navbar, tabs, callouts, tags, buttons, tables, and icon fonts).
- [`index.html`](./index.html), [`styles.css`](./styles.css), [`app.js`](./app.js): Palantir Foundry-styled dark telemetry UI with always-visible market status bar, **Tab 1 (`MDA · D-1`)**, **Tab 2 (`MTR · Live` with SCADA vs. Public D-7 mode)**, and **Tab 3 (`Settlement & Review · D+7`)**.
- [`prepare_dashboard_data.py`](./prepare_dashboard_data.py): Extracts real CENACE Monclova trajectories (`combined_monclova_lmp.parquet`), trains the causal `HistGBDT (L1)` model for short-term `1–4h` outlooks and time-of-day accuracy metrics, and builds [`data/dashboard_data.js`](./data/dashboard_data.js).
- [`render_screenshots.py`](./render_screenshots.py): Captures `2880x1720` Retina screenshots (`?tab=tab1`, `?tab=tab2`, `?tab=tab3`) into [`screenshots/`](./screenshots/).

## Quick Usage
```bash
# Refresh data bundle from processed CENACE Parquet + HistGBDT L1 model
.venv/bin/python analyst_website/prepare_dashboard_data.py

# Serve locally to interact in a browser
python3 -m http.server 8080 --directory analyst_website

# Re-render high-DPI presentation screenshots
.venv/bin/python analyst_website/render_screenshots.py
```
