# Technical Challenge: Monclova LMP Analytics, Forecasting & Operations

Reproducible analytics pipeline, forecasting/anomaly experiments, and analyst dashboard prototype for the **nine Monclova Load Zone nodes** in Mexico's Wholesale Electricity Market (**MEM / CENACE**, `SIN · NORESTE`, **Jan 1, 2024 – Jun 30, 2025**).

---

## 1. Clean Project Structure

```text
.
├── pyproject.toml                  # Python 3.12 dependencies (managed via uv)
├── .python-version
├── README.md
├── code/                           # 1. CENACE Fetcher & Validation Pipeline
│   ├── config.py                   # Node IDs, voltage metadata, CENACE SW-PML endpoints
│   ├── cenace_client.py            # Resilient HTTP client with retries & rate-limit backoff
│   ├── extractor.py                # 7-day chunked MDA/MTR extractor & raw JSON caching
│   ├── parser.py                   # JSON normalization, component checks & Parquet export
│   ├── validator.py                # Data completeness, duplicate & additivity audit
│   └── run_pipeline.py             # CLI entrypoint
├── experiments/                    # 2. Modeling, Evaluation & Presentation Figures
│   ├── monclova_lmp_experiments.ipynb
│   ├── build_experiments_notebook.py
│   ├── update_presentation.py
│   ├── README.md
│   └── figures/                    # All presentation charts (Slides 2–10 PNGs)
├── analyst_website/                # 3. Independent Analyst Web Prototype & Screenshots
│   ├── index.html                  # Tab 1 (MDA Planner), Tab 2 (MTR Monitor), Tab 3 (D+7 Review)
│   ├── styles.css
│   ├── app.js
│   ├── prepare_dashboard_data.py   # Exports CENACE data + HistGBDT (L1) outlook into JS bundle
│   ├── render_screenshots.py       # Headless Chrome high-DPI screenshot capture
│   ├── data/dashboard_data.js
│   └── screenshots/                # Retina PNG screenshots ready for deck insertion
├── data/
│   ├── raw/                        # Cached CENACE MDA & MTR JSON chunks
│   └── processed/                  # Curated Parquet datasets (118,152 node-hours each)
├── presentation/                   # Final executive presentation deck (monclova_lmp_presentation.pptx)
└── source/                         # Technical challenge brief, SW-PML manual & NodosP catalog
```

---

## 2. Quick Start (`uv`)

```bash
# Sync dependencies
uv sync

# 1. Run CENACE Data Fetcher & Validation Pipeline
uv run python code/run_pipeline.py

# 2. Re-execute Master Experiments Notebook & All Slide Figures
uv run jupyter nbconvert --to notebook --execute --inplace \
  experiments/monclova_lmp_experiments.ipynb

# 3. Launch or Re-render Independent Analyst Website Mockup & Screenshots
python3 -m http.server 8080 --directory analyst_website
uv run python analyst_website/render_screenshots.py
```

---

## 3. Verified Headline Results (`MTR` Real-Time Benchmark, `2025` Test $N = 39{,}096$)

- **Spatial Unity:** All 9 Monclova substations track at $r \ge 0.999997$ (Energy drives **88.7%** of gross `MTR` price magnitude), justifying one unified multi-node model (`$101.10` vs `$101.04/MWh` 9-separate-model parity).
- **Model Leaderboard (`MTR`):** **`HistGBDT (L1 / MAE Loss)`** cuts error to **`$101.10/MWh` MAE** (`13.32%` WAPE, `79.9%` within `≤ $100/MWh`), outperforming `SARIMA` (`$134.22`) and `Ridge L2` (`$142.65`, `57.4% <= $100/MWh`).
- **Two-Stage Operations:** Because public CENACE `MTR` releases with a **7-day lag**, the analyst workbench separates **Tab 1 (`MDA` Day-Ahead Bidding Planner)**, **Tab 2 (`MTR` Real-Time Dispatch with SCADA vs. D-7 mode)**, and **Tab 3 (`D+7` Settlement & Retraining Governance)**.
