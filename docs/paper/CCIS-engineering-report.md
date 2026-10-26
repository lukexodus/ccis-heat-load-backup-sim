# Heat, Load and Backup Power for the CCIS Building: A Hybrid Simulation of Rooftop Solar and Battery Storage under Heat and Outage Stress

**Course:** [TO BE FILLED BY TEAM]
**Instructor:** [TO BE FILLED BY TEAM]
**Team members and roles:** [TO BE FILLED BY TEAM]
**Submission date:** 2026-11-03

**Project:** CCIS Heat, Load and Backup Power Simulation (Batac City, Ilocos Norte, Philippines)
**Document:** Final engineering report, prepared for submission on 2026-11-03. Numbers are those of the repository at branch `task/DOC-003` (stacked on `task/DEC-003.3` and `task/DOC-FIX-001`), which is not yet merged to `master`.
**Repo path:** `docs/paper/CCIS-engineering-report.md` (deliberately not `docs/reports/`, which `validate-report.py` checks against the task-report template)
**Status of evidence:** Computational verification and plausibility screening, **not** empirical validation (see §6.1)

> **Reader's note on figures.** Figures 1–5 are the tracked images in `results/figures/` and were opened and compared against their captions for this revision (§7.5). Figure 6 is a text capture of the console output of a single simulation run. Diagram sources for the hand-assembled Google Docs version are in `docs/paper/illustrations.md` (§3.4).

---

## Executive summary

**Question.** How much does Batac's heat raise electricity use in the CCIS building, and how much of the critical load can rooftop solar plus a battery cover during a typhoon-season grid outage?

**What was built.** An hourly (8,760 h) simulation in Python with demand, solar, battery, outage and load-shedding sub-models, a Monte Carlo runner, a conservation-checking harness, and a multi-criteria (AHP) plus Pareto sizing analysis. 290 tests pass on the branch this report is built from (281 on bare `master`).

**Findings (all conditional on the assumptions in §3 and §4).**

| # | Finding | Evidence |
| :-: | :-- | :-- |
| 1 | A +2 °C warming of the 2019 weather raises annual demand by **14,375 kWh (+7.6%)**, from 189,356 to 203,731 kWh. Cooling rises from 29,685 to 44,061 kWh (+48%); cooling is 15.7% of annual demand at baseline and 21.6% at +2 °C. | §7.1 |
| 2 | The recommended sizing is **200 kWp PV / 150 kWh battery** (cost index 290, r = 0.6). Under the bottom-up demand it serves Tier 1+2 loads in **90.3%** of outage hours (95% CI ±2.6%) and cuts mean unserved Tier 1+2 energy from 726.7 to 34.3 kWh per year. | §7.2 |
| 3 | The recommendation is **demand-dependent**. If actual demand is the bill-calibrated level (about 2.1× the bottom-up model), the same sizing serves only **68.4%** of outage hours, and **no tested sizing reaches the 80% target** (best: 200 kWp / 200 kWh at 73.8%). | §7.2 |
| 4 | The bottom-up demand (EUI 75.7 kWh/m²·yr) is about **half** of the synthetic-bill level (EUI 159.4). This gap is unresolved and is carried through every result as two cases. | §6.2 |
| 5 | Simulated PV yield is **1,509 kWh/kWp·yr**, about 16% above the 1,298 benchmark used at project setup. It matches POA × PR within 0.7%; the gap is attributed to the resource data, not to tuning. | §6.4 |
| 6 | Energy is conserved to numerical precision in all audited runs (max hourly residual 2.8 × 10⁻¹⁴ kWh) and all 2,460 Monte Carlo runs passed the harness. | §6.1 |

**What this report does not claim.** It does not validate the model against measured data (none exist), does not give peso costs (the cost index is dimensionless), and does not isolate the effect of the 2016 hot year (a calendar mismatch confounds it, §7.1).

---

## 1. Overview

### 1.1 Problem
The College of Computing and Information Sciences (CCIS) building in Batac relies on grid power in a hot, typhoon-exposed climate. Cooling drives demand, and utility interruptions, longer during typhoon season, threaten loads that must stay on (life-safety, communications, servers). Rooftop solar with battery storage can cover part of that, but sizing depends on how heat shapes load and on how long outages last.

### 1.2 Goal
Quantify (a) the heat-driven increase in electricity use and (b) the share of critical load that solar plus storage can cover during outages, then recommend a sizing under a transparent decision rule.

### 1.3 System boundary
**Inside:** the CCIS building's electrical load (18-room archetype), a rooftop PV array (up to 200 kWp, set by usable roof area, [D-18]), a lithium-iron-phosphate battery (up to 200 kWh), the utility connection, outage events, and a three-tier load-shedding policy.
**Outside:** the wider campus grid, tariffs and pesos, net metering or export revenue, grid-to-battery charging, equipment degradation over years, and any measured building data (none were available, [D-03]).

---

## 2. Formulation

### 2.1 System description
Weather (NASA POWER hourly, 2019 baseline, 2016 hot-year sensitivity, 8,760 h each, [D-20]) drives cooling demand and PV output. Occupancy follows an academic calendar. A stochastic outage process interrupts the grid. During an outage, a priority policy sheds loads, and the battery, charged only from PV surplus, supplies what remains.

### 2.2 Modelling objectives
1. Reproduce hourly building demand split into cooling and non-cooling, by priority tier.
2. Simulate PV generation with temperature derating, and a battery with efficiency, rate and reserve limits.
3. Simulate stochastic outages (normal and typhoon regimes) and measure unserved critical energy.
4. Compare sizing options under uncertainty in outage timing and in building demand.

### 2.3 Performance measures
| Measure | Definition |
| :-- | :-- |
| Annual demand, EUI, peak | kWh/yr, kWh/m²·yr (floor area ≈ 2,500 m², implied by the bill EUI), kW |
| Cooling share | Cooling kWh / total kWh |
| Reliability | Fraction of outage hours in which Tier 1 and Tier 2 loads are fully served |
| Unserved Tier 1+2 energy | kWh per year, mean and spread over seeds |
| Self-sufficiency | Fraction of annual consumption met by solar (directly or via battery) |
| Curtailment | Solar energy generated but neither used nor stored (kWh) |
| Cost index | `kWp × 1.0 + kWh × r`, with r = 0.6 (relative units, not pesos) |

### 2.4 Decision variables
PV capacity ∈ {50, 100, 150, 200} kWp and battery capacity ∈ {0, 25, 50, 100, 150, 200} kWh (a 24-point grid) plus a 0/0 reference. Battery-only designs are excluded (§5.3).

---

## 3. Conceptual model

### 3.1 Entities and state
- **Building load**, tiers: Tier 1 (critical, nominally 2%), Tier 2 (essential, 18%), Tier 3 (sheddable, 80%) of nominal load ([D-10]). The equipment audit gives a connected-load split of 0.82% / 10.39% / 88.79% (1.2 / 15.4 / 131.2 kW of 147.8 kW, [D-19]); the model reports this difference instead of forcing the nominal split.
- **PV array:** DC yield from transposed irradiance and a cell-temperature model, then inverter and balance-of-system losses.
- **Battery:** state of charge (SoC) in kWh; floor and reserve rules.
- **Grid:** available or in outage each hour.

### 3.2 Hourly event order (per [D-35])
1. Compute tiered demand (occupancy and weather). 2. Determine grid status (outage schedule). 3. Apply the shedding policy. 4. Compute PV output (with the typhoon irradiance multiplier). 5. Settle the bus: serve load from PV, then battery, then grid; charge the battery from surplus PV only. 6. Apply idle losses (self-discharge, standby). 7. Record grid import, curtailment and unserved energy per tier.

### 3.3 Key assumptions
| Area | Assumption | Source |
| :-- | :-- | :-- |
| Cooling | Piecewise cooling-degree response: base 24 °C, 4% per °C, +20% latent | [D-07] |
| PV | 15° south tilt, PR 0.77, γ = −0.40%/°C, NOCT 45 °C + 10 °C rooftop rise | [D-08] |
| Battery | LFP, 92% round-trip efficiency, 90% depth of discharge, 10% floor, 0.5C charge / 1.0C discharge, 2%/month self-discharge | [D-09], [D-26] |
| Reserve | Emergency reserve 20% of capacity, held back from daily dispatch while the grid is up; released during outages | [D-17] |
| Outages | Poisson arrivals (3/yr normal, 8/yr typhoon); lognormal durations (μ 1.2, σ 0.8 normal; μ 2.3, σ 1.0 typhoon); typhoon irradiance at 20–30% of normal for 3–5 days | [D-11], [D-33] |
| Shedding | Tier 3 shed at once on grid failure; Tier 2 shed when SoC < 20% of capacity (a threshold separate from the reserve) | [D-34] |
| Time step | 1 hour; outage durations rounded up to whole hours | [D-05], [D-33] |

### 3.4 Diagrams

Two diagrams accompany this section. **D1** shows the overall simulation flow and **D2** shows
the hourly event order of §3.2 together with the shedding rules of §3.3. Their Mermaid sources,
with suggested captions and the target section for each, are in `docs/paper/illustrations.md`
(together with D3 for the software architecture and D4 for the decision pipeline). The diagrams
are kept in a separate file because the report is assembled by hand in Google Docs, which does
not render Mermaid; the sources are the exact, version-controllable form.

The full state and event specification, including the `HourlyRecord` contract and the
conservation invariant, is in `docs/context/conceptual-model.md` and
`docs/context/phase2-interface-contract.md`.

---

## 4. Data collection and input modelling

### 4.1 Sources
| Input | Source | Treatment |
| :-- | :-- | :-- |
| Weather | NASA POWER native hourly, Batac grid cell, 2019 and 2016; Feb 29 dropped to keep 8,760 h | [D-20]; 2019 mean 26.44 °C, GHI 1,900.6 kWh/m²·yr; 2016 hourly peak 36.64 °C |
| Equipment | Synthetic 18-room equipment audit, 147.81 kW connected | [D-16], [D-19]; **no institutional data were used** ([D-03]) |
| Bills | Synthetic monthly bills generated from the same audit, 398,537 kWh/yr, EUI 159.41 | CORE-003; **not independent of the model's inputs** |
| Outage statistics | Poisson and lognormal parameters from the project's research synthesis | [D-11]; primary sources not verified (§9) |

NASA POWER cell representativeness for Batac has not been checked against a local station.

### 4.2 Distribution fitting
The outage sampler draws continuous lognormal durations and discretizes them. A Kolmogorov–Smirnov test on the continuous draws against the target lognormal (α = 0.01) and a z-test on mean annual arrivals against the Poisson rate both pass in unit tests (`tests/test_outage_sampler.py`, 17 tests). This confirms the **sampler matches its specified distributions**; it does not show that the specified distributions match Batac's real outages.

### 4.3 Handling of missing and anomalous weather data

The ingestion path is `ccis_sim/weather/`. In order, it does the following.

1. **Parse and coerce** (`parser.py`, `WeatherParser.parse_hourly_json`). NASA POWER parameters `T2M`, `RH2M` and `ALLSKY_SFC_SW_DWN` are renamed to `t_amb`, `rh` and `ghi`; every value is passed through `pd.to_numeric(..., errors="coerce")`, so any non-numeric token becomes `NaN`. Timestamps in LST are localised to PST (+08:00); UTC payloads are converted.
2. **Replace the missing-value sentinel** (`sanitizer.py`, `WeatherSanitizer.filter_sentinels`). NASA POWER's `-999.0` is replaced by `NaN` in every numeric column, using `np.isclose(..., atol=1e-3)`. Nothing else is treated as missing.
3. **Interpolate short gaps** (`WeatherSanitizer.interpolate_missing`). Linear interpolation in time, limited to **24 consecutive hours**; the remaining edges are filled backwards and forwards (`bfill().ffill()`). If any `NaN` survives, the function raises `ValueError` rather than continuing. This is the only imputation in the model: no regression, no analogue-year substitution, no flagging of imputed hours.
4. **Align to Philippine Standard Time** (`WeatherSanitizer.align_to_pst`). A naive `timestamp_utc` index is localised to UTC then converted; an already-aware index is converted; a naive unnamed index is assumed to be local standard time and localised to +08:00.
5. **Validate physical bounds** (`WeatherSanitizer.validate_psychrometrics`). Raises `PsychrometricValidationError` if ambient temperature leaves −10 to 55 °C, relative humidity leaves 0–100%, or GHI leaves 0–1500 W/m². The check is reject-only: out-of-range values are not clipped or repaired.
6. **Standardise the year** (`WeatherSanitizer.standardize_annual_hourly`). Selects the target calendar year, **drops 29 February in leap years** so every year has 8,760 hours ([D-20]), and raises `ValueError` unless exactly 8,760 rows remain. It then rounds temperature and humidity to two decimals and clips humidity into 0–100% and GHI to ≥0.

What the reported runs actually exercise is narrower. `simulate()` calls `load_weather_fixture` (`loader.py`), which **validates but does not clean**: it requires the five canonical columns, exactly 8,760 rows, no `NaN`, and no surviving `-999.0`. There is no call site for `WeatherSanitizer` anywhere in `src/` outside the package's own re-exports, so steps 2–4 above do not run during a simulation; the committed CSVs in `data/fixtures/` are already clean (their first rows read e.g. `2019-01-01 00:00:00+08:00, 22.92 °C, 87.0%, 0.0 W/m²`), and the loader rejects anything that is not.

Two limits follow, and they are stated plainly. First, there is **no anomaly detection** beyond the physical bounds: a plausible but wrong value (for example 45 °C at midnight, or non-zero GHI at 02:00) passes every check. Second, the interpolator **does not report what it imputed** — the count of replaced sentinels and interpolated hours is not logged or stored — so the report cannot say how much of the input series is reconstructed.

### 4.4 What was not fitted

No probability distribution was fitted to observed data, because no observed local data exist for this building ([D-03]). The outage arrival rates, duration parameters and typhoon solar-depression factors are taken from the project's research synthesis ([D-11]) and are unverified against primary sources (§9). The Kolmogorov–Smirnov and z tests in §4.2 test the **sampler** against those chosen parameters; they are not goodness-of-fit tests against Batac data and should not be read as evidence that the parameters are right.

---

## 5. Implementation

### 5.1 Tool justification
Python 3.14 with NumPy, pandas and SciPy: transparent, scriptable, easy to test. A custom hourly loop was chosen over a general discrete-event package because every component is a pure function of (config, weather, seed), which makes seed-matched comparisons and conservation checks simple. ([D-04] records Python as the choice; instructor confirmation was never recorded.)

### 5.2 Architecture
| Package | Role |
| :-- | :-- |
| `core/` | Domain models, interface types, conservation and boundary harness |
| `weather/` | NASA POWER client, parser, sanitizer, daily-to-hourly disaggregator |
| `demand/` | Equipment audit, occupancy schedule, non-cooling and cooling demand, synthetic bills |
| `solar/` | Irradiance transposition, NOCT thermal derating, array scaling and inverter clipping |
| `battery/` | Dispatch dynamics, reserve floors, idle losses |
| `outage/` | Outage sampler with typhoon coupling, tiered shedding, unserved-energy tracker |
| `integration/` | Engine, exporters, Monte Carlo scenario runner |
| `validation/` | Audit, plausibility, sensitivity, hypothesis tests |
| `decision/` | AHP, Pareto frontier, sizing rule, figures |
| `cli.py` (top level, beside the packages) | Command-line entry point (`ccis-sim run`): argument parsing and summary printing |

About 9,300 lines of source (42 files) and 6,000 lines of tests (22 test modules plus `tests/__init__.py`); the full per-file index is in Appendix C.

### 5.3 Engine limitations that shape the results
1. **The battery never charges from the grid.** With no PV, a battery discharges once and stays at its floor (about 0.8 cycles per year). Battery-only designs are therefore excluded ([D-38]) and no conclusion about grid-charged storage should be drawn.
2. **No export.** Surplus PV that the battery cannot absorb is curtailed.
3. **During an outage all of Tier 3, including cooling, is shed.** "Reliability" therefore means Tier 1+2 only; this is about 16.6 kW of connected load, not the full building.
4. **Tier 2 shedding has no hysteresis** (SoC at the start of the hour decides).
5. **Costs are relative.** The cost index supports ranking, not budgeting.

---

## 6. Verification and validation

### 6.1 Framing
The mock bills and the bottom-up model share one equipment audit, so agreement between them would be circular and disagreement is not evidence about the real building. This section therefore reports **verification** (does the code do what it claims), **sensitivity**, and **plausibility screening**. No empirical validation was possible.

### 6.2 Verification results
| Check | Result |
| :-- | :-- |
| Test suite | 290 passed on the report branch `task/DOC-003` (281 on `master` at `6efa69f`) |
| Energy conservation audit, 12 configurations (grid-only, PV, PV+battery; 2019 normal, 2019 typhoon, 2016 normal) | All pass. Max hourly residual 2.84 × 10⁻¹⁴ kWh; cumulative residual ≤ 6.6 × 10⁻¹³ kWh; SoC within [10%, 100%] wherever a battery exists (identically 0 otherwise); no non-finite values; served + unserved = demand per tier per hour |
| Monte Carlo runs | 2,460 annual runs, 0 harness failures |
| Reproducibility | Identical seed gives an identical hourly-CSV hash; a different seed gives a different outage schedule |
| Negative controls | A +10⁻³ kWh residual, SoC below the floor, and a NaN are each caught by the harness |

### 6.3 Plausibility screening
| Quantity | Model (bottom-up) | Comparison | Reading |
| :-- | :-: | :-- | :-- |
| Annual demand | 189,356 kWh | Mock bills 398,537 kWh (−52.5%) | Large gap |
| EUI | 75.7 kWh/m²·yr | Bills 159.4; research-synthesis band for tropical air-conditioned buildings 160–275 | Model is below the band |
| Monthly fit to bills (ASHRAE Guideline 14 style) | NMBE −57.3%, CV(RMSE) 55.3% | Thresholds ±5% and 15% | Fails, as expected for an uncalibrated model |
| Peak | 95.7 kW (2019-04-08 11:00) | Bills 139.2 kW | Lower |
| Day types | School days 845.8 kWh/day, weekends 268.6, breaks and holidays 204.5 | | Occupancy structure is visible |

The research-synthesis band describes continuously occupied air-conditioned offices; an academic building with long breaks plausibly sits lower, which the day-type means support. But the gap is large enough that the report treats it as **an unresolved uncertainty, not an explained one**: results are shown for the bottom-up case (primary, no circular tuning) and for a bill-calibrated case in which all demand is scaled uniformly by 2.1047 ([D-36]). The uniform scaling does not test *which* part of the load (cooling, plug, lighting) is missing.

### 6.4 Solar yield
POA insolation 1,945.98 kWh/m²·yr × PR 0.77 = 1,498.4 kWh/kWp; the simulation gives 1,508.74 (+0.7%). The project's 1,298 kWh/kWp benchmark is 16.2% lower. Model physics reproduces its own inputs; the benchmark's source was not verified in the repository, so the higher yield is reported as plausible-but-high and is not tuned away. NASA POWER irradiance can run high against ground stations; this was not checked.

### 6.5 One-at-a-time sensitivity (100 kWp / 100 kWh, 2019 normal, seed 0)
| Parameter | Values | Change in grid import | Change in unserved Tier 1+2 |
| :-- | :-- | :-: | :-: |
| Cooling slope | 3 / 4 / 5 %/°C | −6,496 / 0 / +6,501 kWh (±8.2%) | none |
| PV BOS factor | −5% / base / +5% | +3,721 / 0 / −3,688 kWh (about ∓4.7%) | none |
| Emergency reserve | 10% / 20% / 50% | −1,711 / 0 / +5,274 kWh | +11.6 kWh at 10% |
| Tier 2 shed threshold | 10% / 20% / 30% | none | +11.6 kWh at 30% |
| Battery round-trip efficiency | 0.88 / 0.92 / 0.96 | +372 / 0 / −365 kWh (±0.5%) | none |

Annual demand is most sensitive to the cooling slope and PV output to the loss factor; battery efficiency barely matters at this scale. This is a single-seed, one-factor-at-a-time screen, not a variance decomposition.

### 6.6 Subject-matter-expert review: status

**No subject-matter-expert review has been performed**, and no measured data were available to validate against. The model is therefore verified against its own specification (§6.2) and screened for plausibility (§6.3), but it has not been reviewed for realism by anyone with building-energy or distribution-utility expertise, and the conclusions in §8 rest on that unreviewed basis.

A reviewer should check, at minimum:

1. **EUI band.** Whether 75.7 kWh/m²·yr is plausible for an intermittently occupied academic building of this size with the audited AC inventory, and whether the 160–275 kWh/m²·yr band used for comparison applies.
2. **Cooling response.** The 24 °C base temperature, the 4%/°C slope, and the +20% latent allowance for a hot, humid coastal site.
3. **Outage parameters.** The Poisson rates (3/yr normal, 8/yr typhoon) and the lognormal duration parameters as descriptions of INEC service in Batac.
4. **Load-shedding priorities.** Whether Tier 1 at 2%, Tier 2 at 18% and Tier 3 at 80% of nominal load, and the shedding rules in §3.3, reflect what the college would actually keep energised.
5. **Solar yield.** The simulated 1,509 kWh/kWp·yr against the 1,298 kWh/kWp·yr benchmark, and the PR of 0.77.

A blank review record is provided in Appendix E for this purpose.

---

## 7. Results

### 7.1 How much does heat raise electricity use? (grid-only building, deterministic demand)

| Weather case | Annual kWh | Cooling kWh | Non-cooling kWh | Cooling share | Peak kW |
| :-- | --: | --: | --: | --: | --: |
| 2019 (baseline) | 189,356 | 29,685 | 159,670 | 15.7% | 95.7 |
| 2019 + 2 °C | 203,731 | 44,061 | 159,670 | 21.6% | 101.9 |
| 2016 (hot year) | 198,797 | 32,804 | 165,992 | 16.5% | 99.6 |

- **+2 °C is the clean estimate:** +14,375 kWh (+7.6%) in total, +48% in cooling, +6.2 kW in peak. The same calendar is used, so the difference is weather only. Under the bill-calibrated demand the absolute increase scales to +30,255 kWh (398,537 → 428,792) at the same +7.6%.
- **2016 is confounded.** `simulate()` always applies the 2019 academic calendar, so 2016 gets 218 class days instead of 206; non-cooling demand rises by 6,322 kWh from the calendar alone. The +4.99% difference for 2016 should **not** be quoted as a weather effect.
- **Regression.** For 2019 school days, daily kWh rises 32.3 kWh per °C of daily mean temperature (intercept −75.9, R² = 0.08, n = 206). That is about 3.8% of the mean school-day demand per °C, close to the model's own 4%/°C cooling assumption. The low R² reflects occupancy and season dominating daily variation. **This is a recovered model input, not an independent estimate of the building's heat sensitivity.**
- Temperature-band means (days ≥ 30 °C versus < 26 °C) are not shown as a heat effect, because occupancy seasonality dominates them. In the +2 °C case the ≥ 30 °C band has *lower* mean demand (524.7 vs 636.8 kWh/day) since the extra hot days fall in the academic break; in the 2019 baseline the ≥ 30 °C band is higher (1,003.2 vs 533.2) because those days are term-time. No day reaches a daily mean ≥ 34 °C; extreme-heat counts need hourly maxima.

Heat results are conditional on the cooling parameters in [D-07]; the ±8% cooling-slope sensitivity (§6.5) bounds how much they could move.

### 7.2 Backup power: Monte Carlo sizing study

**Design.** Candidates: PV ∈ {50, 100, 150, 200} kWp × battery ∈ {0, 25, 50, 100, 150, 200} kWh, plus a 0/0 reference. 2019 weather, typhoon regime, 50 seeds per sizing, common random numbers across sizings, evaluated under both demand cases. A 2016 re-run covers the top five sizings.

**Pre-registered rule ([D-38], fixed before computing).** Choose the cheapest non-dominated sizing with mean Tier 1+2 outage-hours-served ≥ 90% (bottom-up demand) **and** ≥ 80% (bill-calibrated demand); if none qualifies, report the best achievable under each case and the trade-off.

**Outcome.** No sizing met both. The recommendation, 200 kWp / 150 kWh, is the cheapest sizing meeting the bottom-up threshold; under bill-calibrated demand the best achievable is 200 kWp / 200 kWh.

| Case | Sizing | Reliability (mean, 95% CI) | P5 / P95 | Unserved T1+2, kWh (mean ± 95% CI) | Self-sufficiency | Grid import |
| :-- | :-- | :-: | :-: | :-: | :-: | :-: |
| Bottom-up | 0 / 0 (reference) | 0% | | 726.7 | 0% | |
| Bottom-up | **200 / 150 (recommended)** | **90.3% ± 2.6** | 72.1 / 100.0% | 34.3 ± 11.7 | 84.9% | 28.5 MWh |
| Bottom-up | 200 / 200 | 92.9% | | 25.9 | 87.4% | |
| Bill-calibrated | 0 / 0 (reference) | 0% | | 1,529.6 | 0% | |
| Bill-calibrated | **200 / 150 (recommended)** | **68.4% ± 3.8** | 48.4 / 91.2% | 321.9 ± 58.1 | 54.5% | 181.3 MWh |
| Bill-calibrated | 200 / 200 | 73.8% | | 279.3 | 56.0% | |

Reading the table:
- The recommended sizing removes about 95% of mean unserved Tier 1+2 energy under the bottom-up demand and about 79% under the bill-calibrated demand.
- **The 90% pass is marginal.** The true bottom-up value is 90.34%. Until DOC-FIX-001/DEC-003.3, `scripts/run_decision_pipeline.py` multiplied this cell by 100.2 instead of 100 and `results/recommendation.md` printed 90.5%; the multiplier is now `×100` and the file prints 90.3%, agreeing with the Pareto table. The margin over the 90% threshold is therefore 0.34 points, the CI half-width is ±2.6 points, and 150 kWp / 200 kWh sits at 88.8%. The ranking among the top few sizings is not statistically firm.
- **PV is oversized for the bottom-up demand.** A 200 kWp array generates about 301.7 MWh against 189.4 MWh of demand; roughly 138 MWh (46%) is curtailed because the model has no export. Much of the self-sufficiency gain is real, but the marginal PV above ~150 kWp mostly buys curtailment unless demand is nearer the bill-calibrated level.
- **The AHP ranking and the rule disagree.** On AHP composite score (weights: reliability 0.587, cost 0.218, self-sufficiency 0.123, curtailment 0.072; λmax = 4.019, CR = 0.0071), the top three are 150/150 (0.751), 150/200 (0.748) and 150/100 (0.744); 200/150 is seventh (0.725). The AHP score trades reliability against cost and curtailment; the pre-registered rule enforces a reliability floor. The report follows the rule because it was fixed before the results; a decision-maker who weighs curtailment more heavily would choose 150 kWp.

**Pareto structure.** Under the bottom-up demand 20 of the 25 evaluated sizings are non-dominated, and under the bill-calibrated demand 23 are, across (reliability, cost, self-sufficiency): there is no single dominant design, only a trade-off curve. Reliability rises steeply with battery size up to 100–150 kWh at 150–200 kWp and flattens beyond (e.g. at 200 kWp: 87.0% at 100 kWh, 90.3% at 150, 92.9% at 200).

**Weather robustness (top-5 AHP sizings, 2016 weather).** Reliability is 1.9–4.5 points higher in 2016 for each of the five sizings (e.g. 200/200: 92.9% → 96.5%). 2016 also differs in calendar handling (§7.1), so this is a robustness check, not a clean weather comparison.

**Cost and weight sensitivity.** With r = 0.3 or 1.0 the Pareto structure is preserved; cheaper storage favors 150–200 kWh, costlier storage penalizes capacity above 100 kWh. Equal weights favor more PV with moderate storage; reliability-heavy weights favor batteries of at least 100 kWh. (These two statements are summarized from `results/recommendation.md` §4.2–4.3; the supporting tables were not reproduced there.)

### 7.3 Statistical comparisons (seed-paired, 2019 typhoon, bottom-up demand)

p-values describe **seed-to-seed simulation variability** with 30 paired seeds. They are not inference about the real world.

| Comparison (unserved Tier 1+2) | n | Mean difference (kWh) | 95% CI half-width | Cohen's dz | Holm-adjusted Wilcoxon p |
| :-- | :-: | :-: | :-: | :-: | :-: |
| 100/50 → 100/100 | 30 | −44.1 | 11.6 | −1.41 | 7.7 × 10⁻⁶ |
| 100/100 → 200/100 | 30 | −61.5 | 19.6 | −1.17 | 7.7 × 10⁻⁶ |
| 200/100 → 200/200 | 30 | −19.4 | 7.7 | −0.94 | 7.7 × 10⁻⁶ |
| 0/0 → 100/100 | 30 | −534.5 | 117.9 | −1.69 | 7.5 × 10⁻⁹ |
| Typhoon vs normal, 100/100 (unpaired; Mann–Whitney) | 30 + 30 | +104.6 | | | 3.4 × 10⁻⁹ |

Each added increment of PV or storage reduces unserved energy by a large margin relative to seed variability, so the *direction* of every step is reliable. The weather comparisons (2019 vs 2016: −9,434 kWh grid-only; +2 °C: +14,347 kWh) are near-deterministic differences between fixed inputs, with seeds varying only the outage draw; their p-values and effect sizes (|dz| in the tens to hundreds) are not meaningful and are not used.

### 7.4 Convergence
At the benchmark cell (100 kWp, 100 kWh, 2019 typhoon), the 95% CI half-width of mean unserved Tier 1+2 energy is 59.9% of the mean at N = 10, 36.7% at N = 20 and 31.6% at N = 30 (mean 111 kWh). Typhoon outage durations are heavy-tailed, so means converge slowly. Common random numbers keep *comparisons between sizings* stable; the absolute means should be read with their intervals. The sizing study used N = 50.

### 7.5 Sample outputs

The five figures below are tracked images in `results/figures/` and are referenced in place.

![Figure 1: Seven-day stacked dispatch for the recommended 200 kWp / 150 kWh sizing around an outage window](../../results/figures/fig1_dispatch_7day.png)

**Figure 1.** Seven-day stacked dispatch for the recommended 200 kWp / 150 kWh sizing. Stacked areas from the bottom are battery discharge, solar to demand, grid import and unserved shortfall; the legend lists them in a different order (solar, battery, grid, unserved). The dashed purple line is battery stored SoC on the right-hand axis and the dotted line is the 10% protection floor. The grey hatched band marks the outage window, inside which grid import disappears and unserved shortfall appears.

![Figure 2: Annual battery state-of-charge duration curve, normal versus typhoon regime](../../results/figures/fig2_soc_duration_curve.png)

**Figure 2.** Annual battery state-of-charge duration curve for the 150 kWh battery, x-axis being the percentage of annual hours exceeded. Normal and typhoon regimes are drawn as separate lines, with nominal capacity (150 kWh) and the minimum SoC floor (15 kWh) as reference lines. The two regime curves nearly coincide: over a full year the duration curve is dominated by the daily charge–discharge cycle, not by outage regime.

![Figure 3: Distribution of unserved Tier 1+2 energy across 50 seeds for three sizings](../../results/figures/fig3_unserved_distribution.png)

**Figure 3.** Box plots of annual unserved Tier 1+2 energy across 50 typhoon-regime seeds for three sizings, left to right on the x-axis: 100 kWp / 50 kWh (moderate system), the recommended 200 kWp / 150 kWh, and 200 kWp / 200 kWh (maximum grid cap). The boxes show the interquartile range, the orange line the median, the dashed green line the mean, and the circles are outliers.

![Figure 4: Pareto trade-off, cost index versus Tier 1+2 outage hours served, both demand cases](../../results/figures/fig4_pareto_scatter.png)

**Figure 4.** Pareto trade-off for both demand cases. Panel A is the bottom-up demand (scale 1.0) and Panel B the bill-calibrated demand (scale ≈ 2.10); the x-axis is the relative cost index, the y-axis the percentage of Tier 1+2 outage hours served, and the colour is annual self-sufficiency. Large markers joined by the dashed line are the non-dominated frontier, pale points are dominated sizings, and the red star marks the recommended 200 kWp / 150 kWh.

![Figure 5: Monthly demand, bottom-up model versus synthetic utility bills](../../results/figures/fig5_monthly_demand_comparison.png)

**Figure 5.** Monthly electricity consumption, bottom-up model against the synthetic utility bills. The title states the annual totals (189.4 MWh versus 398.5 MWh, ratio 2.10×) and the two EUIs (75.7 versus 159.4 kWh/m²·yr). The gap is widest in June and July, when the model's academic occupancy drops and the bill series does not.

**Figure 6.** `ccis-sim run` console output (text capture; replace with a terminal screenshot if the instructor requires one). The command was `ccis-sim run --solar-kwp 200 --battery-kwh 150 --weather 2019 --outages typhoon --seed 1 --out <temporary directory>`, run through the same entry point as `python3 -m ccis_sim.cli` because the console script was not installed in the task environment. This is a **single-seed illustrative run**, not the Monte Carlo result of §7.2; the seed fixes one outage draw, so the figures here differ from the 50-seed means.

```text
========================================================================
   CCIS HEAT, LOAD AND BACKUP POWER SIMULATION — ANNUAL RUN SUMMARY
========================================================================
 Configuration:
   Solar PV Capacity:         200.00 kWp
   Battery BESS Capacity:     150.00 kWh
   Weather Reference Year:      2019 (offset: +0.0°C)
   Outage Arrival Regime:    typhoon (seed: 1)
   Tier 2 Shed SoC Floor:       20.0%
   Emergency Reserve Ratio:     20.0%
------------------------------------------------------------------------
 Energy Balance Totals:
   Gross Demand:              189,355.61 kWh
   Served Demand:             186,851.71 kWh
   Unserved Deficit:            2,503.90 kWh
   Utility Grid Import:        28,945.92 kWh
   Solar Generation:          298,627.42 kWh
   Solar Direct to Demand:    127,566.67 kWh
   Solar to Battery:           32,970.34 kWh
   Solar Curtailed:           138,090.42 kWh
   Battery Charge:             32,970.34 kWh
   Battery Discharge:          30,339.12 kWh
------------------------------------------------------------------------
 Performance & Reliability:
   Peak Gross Demand:              95.71 kW at hour 2340
   Facility EUI (Served):          74.74 kWh/m²·yr
   Facility EUI (Gross):           75.74 kWh/m²·yr
   Solar Self-Sufficiency:         84.51 %
   Solar Specific Yield:         1493.14 kWh/kWp
   Total Outage Hours:               135 hours
   Tier 1 (Critical) Unserved:      0.00 kWh (Covered: 100.0%)
   Tier 2 (Essential) Unserved:    67.22 kWh (Covered:  82.2%)
   Tier 3 (Sheddable) Unserved: 2,436.68 kWh (Covered:   0.0%)
------------------------------------------------------------------------
 Conservation Invariants:
   Max Hourly Residual:       2.8422e-14 kWh (limit: 1.0000e-05)
   Cumulative Net Drift:     -2.8155e-12 kWh
========================================================================

Simulation artifacts saved to: /tmp/tmp.Q3VZu5NzpW
  Hourly records: ccis_sim_hourly.csv
  Daily summary:  ccis_sim_daily.csv
  Annual metrics: ccis_sim_summary.json
```

---

## 8. Conclusions and recommendations

1. **Heat matters, and the building is cooling-sensitive.** +2 °C adds about 7.6% to annual demand (+14.4 MWh bottom-up; +30.3 MWh bill-calibrated), concentrated in cooling hours and raising the peak by about 6 kW. The magnitude rests on the assumed cooling slope and base temperature.
2. **A 200 kWp / 150 kWh system is the rule-based recommendation**, serving Tier 1+2 loads in about nine of ten outage hours at bottom-up demand and about two-thirds at bill-calibrated demand. **It is a demand-dependent recommendation**, and the most valuable next step is to measure the building's real demand.
3. **If curtailment matters, 150 kWp is a defensible alternative:** it ranks first on the AHP composite and gives up about 4 points of reliability.
4. **Raising reliability above about 90% under higher demand needs more than 200 kWh of storage or demand-side action** (for example keeping Tier 2 loads lean in outages); the tested grid tops out at 73.8% under the bill-calibrated demand.
5. **Storage without PV is worthless in this design** because the battery cannot charge from the grid; if grid charging is allowed, the conclusion changes.

**Recommended follow-up (priority order):** (i) obtain 12 months of actual meter data and replace the synthetic bills; (ii) check NASA POWER irradiance against a ground station and revisit the 1,298 kWh/kWp benchmark; (iii) fix the calendar handling so weather years carry their own academic calendar; (iv) replace the cost index with quoted unit prices; (v) allow grid-to-battery charging and export as scenarios.

---

## 9. References

**Verified in the repository:** none. A search of `docs/context/` and `docs/reports/` found no URLs, DOIs or reference list; the "Deep Research" synthesis carries values without citations. The domain-specific inputs below therefore have **unverified provenance** and must be sourced before submission.

| Input in this report | Needs a primary source |
| :-- | :-- |
| Tropical air-conditioned building EUI band 160–275 kWh/m²·yr; Philippine DOE commercial survey values | Required |
| Luzon PV specific-yield benchmark 1,298 kWh/kWp·yr | Required |
| Outage frequency and duration parameters (Poisson 3 and 8 per year; lognormal parameters); typhoon irradiance depression | Required |
| Cooling slope 4%/°C, base 24 °C, latent +20% | Required |
| LFP efficiency, depth of discharge, C-rates, self-discharge | Required (manufacturer datasheet or review) |

**Standard methods and tools** (cited from memory by the APC; verify edition, pages and wording against the source before submission):

[1] T. L. Saaty, *The Analytic Hierarchy Process: Planning, Priority Setting, Resource Allocation*. New York, NY, USA: McGraw-Hill, 1980.
[2] ASHRAE, *ASHRAE Guideline 14-2014: Measurement of Energy, Demand, and Water Savings*. Atlanta, GA, USA: ASHRAE, 2014.
[3] J. A. Duffie and W. A. Beckman, *Solar Engineering of Thermal Processes*, 4th ed. Hoboken, NJ, USA: Wiley, 2013.
[4] A. M. Law, *Simulation Modeling and Analysis*, 5th ed. New York, NY, USA: McGraw-Hill, 2015.
[5] F. Wilcoxon, "Individual comparisons by ranking methods," *Biometrics Bulletin*, vol. 1, no. 6, pp. 80–83, 1945.
[6] S. Holm, "A simple sequentially rejective multiple test procedure," *Scand. J. Statist.*, vol. 6, no. 2, pp. 65–70, 1979.
[7] F. J. Massey, Jr., "The Kolmogorov–Smirnov test for goodness of fit," *J. Amer. Statist. Assoc.*, vol. 46, no. 253, pp. 68–78, 1951.
[8] NASA Langley Research Center, "NASA POWER: Prediction of Worldwide Energy Resources." [Online]. Available: https://power.larc.nasa.gov (access date to be added).

---

## 10. Program listing

The listing is generated by `scripts/build_program_listing.py` (deterministic: sorted paths, no timestamps). Two versions are provided, because the instructor has not said whether the full source or a core selection is required:

- **`docs/paper/program-listing.md`** — the **full listing**: all 42 files of `src/ccis_sim/` plus `scripts/run_decision_pipeline.py`, 43 files and 9,679 lines, about 389 KB. Tests are listed by path, length and purpose, not reproduced.
- **`docs/paper/program-listing-core.md`** — the **core selection**: 15 files and 4,572 lines, about 198 KB, covering the domain models, equipment audit, occupancy, demand, solar, battery, outage, shedding, engine and the AHP/Pareto sizing pipeline; the remaining 28 source files and all 22 test modules (plus `tests/__init__.py`) are listed by index only.

Appendix C gives the index of every file. Reproduce the results with:

```bash
pip install -e .                # provides the ccis-sim console script
pytest -q                       # 290 tests on the report branch; 281 on master at 6efa69f
ccis-sim run --solar-kwp 200 --battery-kwh 150 --weather 2019 --outages typhoon --seed 1 --out results/
python scripts/run_decision_pipeline.py   # regenerates results/*.csv and figures (see script for options)
```

The `ccis-sim run` line writes into `results/`; use a temporary directory if you do not want to overwrite local outputs (Figures 1–5 come from the decision pipeline, not from this single-seed command). Generated CSVs (`results/*.csv`) are gitignored; they are reproduced by `run_grid()` and the decision pipeline. Cite code and decision-log entries ([D-01]–[D-41]); do not cite the INT-001 task report (it misdescribes some function names).

---

## Appendix A. Decision log summary

| ID | Topic |
| :-- | :-- |
| D-05, D-06 | Hourly step; 18-room CCIS archetype |
| D-07, D-08, D-09 | Cooling response; PV parameters; LFP battery |
| D-10, D-17, D-18, D-19 | Load tiers; emergency reserve; usable roof (cap 200 kWp); audit totals (147.81 kW) |
| D-11, D-33 | Outage model; sampler and typhoon coupling |
| D-20 | NASA POWER hourly, 2019 baseline, 2016 hot year |
| D-26 | Idle-loss allowance in the harness; SoC-side tare loss |
| D-27 to D-35 | Demand, solar, battery, shedding, engine |
| D-36 | Dual demand scaling (bottom-up primary, bill-calibrated sensitivity) |
| D-37 | Verification framing, KPI tables |
| D-38 | AHP weights, cost proxy, Pareto rule, solar = 0 exclusion |
| D-39 | Reserved, unused |
| D-40 | Heat-effect reporting convention; 2016 calendar mismatch |
| D-41 | Course-deliverable packaging: generated program listings, diagram sources, figure references, Markdown-only submission |

## Appendix B. Candidate sizings and Pareto status

Bottom-up demand, 2019 typhoon, N = 50 (selected rows; the full table is in `results/pareto_frontier.csv` and `results/recommendation.md`):

| Sizing (kWp / kWh) | Cost index | Reliability | Self-sufficiency | Unserved T1+2 (kWh) |
| :-- | --: | --: | --: | --: |
| 100 / 100 | 160 | 75.2% | 58.2% | 122.5 |
| 100 / 150 | 190 | 79.0% | 60.2% | 104.1 |
| 150 / 100 | 210 | 83.2% | 75.4% | 68.4 |
| 150 / 150 | 240 | 86.4% | 78.1% | 55.2 |
| 200 / 100 | 260 | 87.0% | 81.2% | 46.9 |
| 150 / 200 | 270 | 88.8% | 79.3% | 45.9 |
| **200 / 150** | **290** | **90.3%** | **84.9%** | **34.3** |
| 200 / 200 | 320 | 92.9% | 87.4% | 25.9 |

## Appendix C. Program listing index

Two generated listings are supplied (§10): `docs/paper/program-listing.md` (full, 43 source files, 9,679 lines) and `docs/paper/program-listing-core.md` (core selection, 15 files, 4,572 lines, plus an index of the rest).

The complete per-file index, including every test file, is `results/program_listing_index.md` (65 entries: 42 source files and 23 test-side files, the latter being 22 test modules plus `tests/__init__.py`; largest files `core/verification.py` 919 lines, `outage/sampler.py` 510, `integration/engine.py` 490, `solar/irradiance.py` 429). One entry in that index is stale by three lines: `validation/hypothesis.py` is listed at 340 lines and the file on disk has 343; the generated listings use the on-disk count, so total source lines are 9,298 rather than the index's 9,295.

## Appendix D. Known limitations and open items

1. Mock bills and model share one audit; the 2.1× demand gap is unexplained.
2. 2016 comparisons use the 2019 academic calendar (218 vs 206 class days).
3. The heat sensitivity is an input assumption (D-07), not an estimate.
4. The recommended sizing passes the 90% threshold by 0.34 points inside a ±2.6-point interval.
5. No grid charging, no export, no battery degradation; Tier 3 (including cooling) is shed in outages.
6. Cost index is relative; no pesos.
7. References for domain inputs are unverified.
8. D-04 (Python) was never confirmed by the instructor; team size and track ownership were never recorded.
9. The `×100.2` formatting typo in `scripts/run_decision_pipeline.py`, which printed the bottom-up reliability as 90.5%, was **corrected** in DOC-FIX-001/DEC-003.3: the multiplier is now `×100`, the underlying value is 90.34%, no ranking changes, and `results/recommendation.md` now prints 90.3% for that cell. No other script or result file was found to carry the same typo.

## Appendix E. Subject-matter-expert review record

**Not yet performed.** This page is intentionally blank; nothing below has been filled in, and no review has taken place.

| Reviewer | Role / expertise | Date | Item reviewed | Comment | Disposition |
| :-- | :-- | :-- | :-- | :-- | :-- |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
