# Monclova LMP Experiments & Presentation Figures

**Master Notebook:** [`monclova_lmp_experiments.ipynb`](./monclova_lmp_experiments.ipynb)  
**Notebook Builder:** [`build_experiments_notebook.py`](./build_experiments_notebook.py)  
**Presentation Sync Script:** [`update_presentation.py`](./update_presentation.py)  
**Target Presentation:** [`monclova_lmp_presentation.pptx`](../presentation/monclova_lmp_presentation.pptx)

---

## 1. Chronological Benchmark Split
- **Dataset:** [`combined_monclova_lmp.parquet`](../data/processed/combined_monclova_lmp.parquet) (`118,152` raw node-hours across all 9 Monclova substations, `2024-01-01` to `2025-06-30`).
- **Train Partition:** `2024-01-09` to `2024-12-31` ($N = 77{,}328$, after causal `lag_168` warm-up; Mean `$849.07`, Min `$20.96`, Max `$12,942.84/MWh`).
- **Out-of-Sample Test Partition:** `2025-01-01` to `2025-06-30` ($N = 39{,}096$; Mean `$759.13`, Min `$88.90`, Max `$8,460.16/MWh`).

---

## 2. Verified 3-Model Real-Time (`MTR`) Leaderboard (Slide 7)

| Model Family | MAE (\$/MWh) | RMSE (\$/MWh) | WAPE (%) | $R^2$ | Prec $\le \$50$ (%) | Prec $\le \$100$ (%) |
|---|---:|---:|---:|---:|---:|---:|
| Ref: Naive Persistence (`MTR_t-1`) | `$103.05` | `$372.49` | `13.58%` | `0.477` | `70.4%` | `82.8%` |
| **`SARIMA(1,0,1)×(1,0,1)24`** | **`$134.22`** | **`$342.07`** | **`17.68%`** | **`0.559`** | `25.6%` | `68.3%` |
| **`Ridge Regression (L2)`** | **`$142.65`** | **`$338.70`** | **`18.79%`** | **`0.568`** | `30.1%` | `57.4%` |
| **`HistGBDT (L1 / MAE Loss)` [Unified]** | **`$101.10`** | **`$319.43`** | **`13.32%`** | **`0.615`** | **`62.3%`** | **`79.9%`** |
| Ref: `HistGBDT (L1)` [9 Separate Models] | `$101.04` | `$316.99` | `13.31%` | `0.621` | `61.7%` | `79.5%` |
| Ref: `HistGBDT (L2 / MSE Loss)` | `$121.12` | `$337.81` | `15.96%` | `0.570` | `56.9%` | `75.3%` |
| Ref: Linear `L1+L2` (SGD) | `$109.36` | `$344.23` | `14.41%` | `0.553` | `61.5%` | `79.7%` |
| Ref: Huber Robust Linear | `$100.00` | `$358.64` | `13.17%` | `0.515` | `71.0%` | `83.8%` |

---

## 3. Slide-to-Figure Index

| Presentation Slide | Asset Path (`figures/`) | Verified Key Metrics Shown |
|---|---|---|
| Slide 2 (`Fundamentals`) | `slide_02_mtr_basis_premium.png` | Hour 19 Basis Risk: Mean `+$211.7/MWh`, P90 `+$1,348.9/MWh` |
| Slide 3 (`Grid Topology`) | `slide_03_spatial_grid_topology.png` | Georeferenced 9-substation Monclova / Frontera network (400 / 230 / 115 kV) on Esri WorldStreetMap |
| Slide 5 (`Market Physics`) | `slide_05_mtr_physics_and_coherence.png` | MTR Energy `88.7%` (`$864.84`), Losses `5.2%` (`$50.76`), Cong `6.1%` (`$59.10`); min $r = 0.999997$; Unified vs 9-Model parity (`$101.10` vs `$101.04`) |
| Slide 6 (`Temporal Cycles`) | `slide_06_mtr_temporal_dynamics.png` | Diurnal HE 5 (`$572.2`) -> HE 20 (`$1,627.0`); Weekday `$903.0` vs Weekend `$588.7` (`+$314.3 MXN/MWh`, `+53.4%`) |
| Slide 8 (`Feature Weights`) | `slide_08_mtr_feature_importance.png` | Ridge `mtr_lag_1 β = +$771.9/MWh` (`82.6%` squared weight share); HistGBDT L1 `mtr_lag_1 = 0.820`, `roll_mean_6h = 0.034`, `hour_cos = 0.032`, `hour_sin = 0.017` |
| Slide 9 (`Failure Modes`) | `slide_10a_mtr_solar_overshoot.png`, `slide_10b_mtr_bias_curve.png`, `slide_10c_mtr_error_cdf.png` | Jun 15–16 showcase (`$19.0` vs `$115.7` MAE, peak `+$449.3`); HE 11–18 solar bias `+$78.4` vs `+$2.9`; HE 3–8 dawn `-$71.8` vs `+$0.2`; HE 22–24 post-peak `+$106.0` (HE 23 `+$170.3`); CDF `79.9% vs 57.4% <= $100`; Jan freeze L1 `$99.24` vs Ridge `$128.71` |
| Slide 9 Alt Combined | `slide_09_mtr_bias_and_cdf.png` | Side-by-side Bias Curve & Precision CDF reference export |
| Slide 10 (`Anomaly Detection`) | `figures/slide_11_anomaly_detection.png` | **MDA-only:** `401` MDA VOLL alerts (`3.05%`, `365`/`91.0%` May–Jun '24, `7` in '25 up to `$3,068` zone / `$3,051` `06MON-115`), 2024 peak `$26,222.27` zone / `$26,094.06` `06MON-115`, `32.7x` MDA Ohmic loss surge (`$181.8` vs `$5.55` mean; `-$603.85` min node), Dec 25 Christmas negative inversion (`5` hrs down to `-$53.36` `06MON-115` / `-$53.87` zone) |
| Slide 11 (`3-Stage Workflow`) | *Native deck cards* | Scheduling (`10:15` D-1 `MDA` brief; `:45` `MTR` inference), alerting (`> $2,500`, `> 5x` I²R, `MTR − MDA`), `Mon 00:00` weekly retrain + `KS p < 0.01`, Jun 9–15 D+7 savings `MXN 828.7k (-14.8%)` |
| Slide 12 (`Analyst Workbench UI`) | [`../analyst_website/screenshots/`](../analyst_website/screenshots/) (`01_tab1_day_ahead_planner.png`, `02_tab2_realtime_monitor.png`, `03_tab3_settlement_review.png`) | Palantir Blueprint `@blueprintjs/core v6.22` (`bp6-dark`) console showcasing `MDA` D-1 planning (`Jun 11 HE 21: $3,012`), live `MTR` dispatch (`Jun 10 HE 20: $5,285`), and `D+7` settlement (`MXN 828,677` net saved) |
