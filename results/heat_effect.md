# Heat-Effect Numbers (DOC-FIX-001 Part C)

> Grid-only runs (solar 0, battery 0, bottom-up demand, seed 0).
> Cooling kWh is computed by calling `compute_cooling_demand` with the same inputs.
> Daily means use all calendar days; the regression uses school days only.
> The 2016 weather case keeps the default (`AcademicCalendar(year=2019)`) calendar,
> matching what `simulate()` does.

## Table 1 — Bottom-up demand (scale = 1.0)

| Weather case | Annual kWh | Cooling kWh | Non-cooling kWh | Cooling share | Peak kW | Peak timestamp | Mean daily kWh, days ≥30 °C | Mean daily kWh, days <26 °C | Days ≥34 °C |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- | ---: | ---: | ---: |
| 2019 | 189,356 | 29,685 | 159,670 | 15.7% | 95.7 | 2019-04-08 11:00:00+08:00 | 1,003.2 | 533.2 | 0 |
| 2019 +2 °C | 203,731 | 44,061 | 159,670 | 21.6% | 101.9 | 2019-04-08 11:00:00+08:00 | 524.7 | 636.8 | 0 |
| 2016 | 198,797 | 32,804 | 165,992 | 16.5% | 99.6 | 2016-05-04 11:00:00+08:00 | 795.9 | 524.9 | 0 |

### Daily regression — 2019, school days only

| Quantity | Value |
| :--- | ---: |
| Slope | 32.2570 kWh/°C |
| Intercept | -75.87 kWh/day |
| R² | 0.0818 |
| n (school days) | 206 |

## Table 2 — Bill-calibrated demand (scale ≈ 2.1047)

| Weather case | Annual kWh | Cooling kWh | Non-cooling kWh | Cooling share | Peak kW | Peak timestamp | Mean daily kWh, days ≥30 °C | Mean daily kWh, days <26 °C | Days ≥34 °C |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- | ---: | ---: | ---: |
| 2019 | 398,537 | 62,479 | 336,058 | 15.7% | 201.4 | 2019-04-08 11:00:00+08:00 | 2,111.5 | 1,122.1 | 0 |
| 2019 +2 °C | 428,792 | 92,734 | 336,058 | 21.6% | 214.4 | 2019-04-08 11:00:00+08:00 | 1,104.4 | 1,340.4 | 0 |
| 2016 | 418,407 | 69,044 | 349,364 | 16.5% | 209.6 | 2016-05-04 11:00:00+08:00 | 1,675.2 | 1,104.7 | 0 |

### Daily regression — 2019, school days only (bill-calibrated)

| Quantity | Value |
| :--- | ---: |
| Slope | 67.8913 kWh/°C |
| Intercept | -159.69 kWh/day |
| R² | 0.0818 |
| n (school days) | 206 |

## Notes

- 2019 baseline: 189,356 kWh/yr; cooling is 15.7% of annual demand.
- +2 °C perturbation: 203,731 kWh/yr (+14,375 kWh, +7.59%).
- 2016 weather: 198,797 kWh/yr (+9,441 kWh, +4.99%).
- Regression slope is a simulation-conditional association, not a causal estimate.
