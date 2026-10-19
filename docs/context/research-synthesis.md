# Deep Research Synthesis & Parameter Master Reference

This document synthesizes findings, empirical benchmarks, mathematical formulations, and citations extracted from the 8 Deep Research reports (prepared for the CCIS Heat, Load and Backup Power Simulation project). Every parameter in the simulation must trace back to this document or be tagged as an explicit assumption.

---

## 1. Geographic & Meteorological Baseline (Batac, Ilocos Norte)

- **Location:** City of Batac, Ilocos Norte, Philippines (`18.06° N, 120.56° E`).
- **Optimal Solar Tilt:** $15^\circ \text{ to } 18^\circ$ True South (Batac latitude ~18.06°N).
- **Global Horizontal Irradiance (GHI):** $1,700 \text{ to } 1,800\text{ kWh/m}^2\cdot\text{yr}$ (Global Solar Atlas, Solargis).
- **Daily Solar Insolation:** $4.0 \text{ to } 5.5\text{ kWh/m}^2\cdot\text{day}$ (average ~4.5–5.0 sun-hours/day).
- **Historical Climate Baseline:** National warming of $+0.6^\circ\text{C}$ (PAGASA 1991–2020 baseline).
- **Dangerous Heat Index Threshold:** $> 40.0^\circ\text{C}$ apparent temperature on summer afternoons in lowland northern Luzon.
- **Extreme Heat Records:** Strong El Niño years (2015–2016, 2019) with prolonged dry spells and suppressed cloud cover.
- **CMIP6 Climate Projections (Northern Luzon):**
  - Mid-Century (2050): $+1.0^\circ\text{C} \text{ to } +2.0^\circ\text{C}$ under SSP2-4.5 and SSP5-8.5.
  - End-Century (2100): $+3.0^\circ\text{C} \text{ to } +4.0^\circ\text{C}$ under SSP5-8.5.
  - Precipitation seasonality: Increase in wet season (June–July); decrease in pre-monsoon dry season (March–May).

### Data Sources & Resolutions:
- **NASA POWER:** MERRA-2 meteorology ($0.5^\circ \times 0.625^\circ$), CERES solar ($1.0^\circ \times 1.0^\circ$), IMERG precipitation ($0.1^\circ \times 0.1^\circ$). Daily 1981–present; Hourly 2001–present. Sentinel for missing data: `-999.0`. Timestamps default to LST (must convert to Philippine Standard Time UTC+8).
- **ERA5 / ERA5-Land (Open-Meteo):** $0.25^\circ$ (~28 km) / $0.1^\circ$ (~9 km). Gap-free hourly records from 1940. Tropical temperature difference from MERRA-2 typically $< 1.0^\circ\text{C}$.

---

## 2. Building Energy, Cooling Response & Equipment Modeling

### Building Archetype (CCIS Baseline):
- **Gross Floor Area:** ~2,500 m² (2-storey academic college building, 16 designated spaces: 2 hyflex smart rooms, 4 lecture rooms, 1 COD room, 1 Dean + Secretary office, 2 faculty rooms, and 6 computer lab rooms; no dedicated server room, network switches distributed in IDF/office cabinets).
- **Energy Use Intensity (EUI) Benchmarks:**
  - Tropical SE Asian air-conditioned office/academic: $160 \text{ to } 275\text{ kWh/m}^2\cdot\text{yr}$.
  - Philippine DOE Commercial Survey: $213 \text{ to } 336\text{ kWh/m}^2\cdot\text{yr}$ (median: $275\text{ kWh/m}^2\cdot\text{yr}$).
  - ASEAN 3-Star Energy Efficiency Target: $\approx 160\text{ kWh/m}^2\cdot\text{yr}$.
- **Electrical End-Use Breakdown (Tropical University Audit):**
  - Air Conditioning (HVAC): $60\% \text{ to } 65\%$ (Philippine university audit: 63.0%; Indonesian audit: 64.7%).
  - Lighting: $10\% \text{ to } 25\%$ (Philippine university audit: 23.0%; Indonesian audit: 8.8%).
  - Plug Loads & IT: $10\% \text{ to } 15\%$ (Philippine university audit: 14.0%; Indonesian audit: 15.0%).

### Cooling Heat-Response Model:
- **Balance-Point Temperature:** $T_{\text{base}} = 24.0^\circ\text{C}$ ($75.2^\circ\text{F}$).
- **Cooling Degree Day (CDD):** $\text{CDD}_t = \max(T_{\text{out}, t} - 24.0,\, 0)$.
- **Temperature Sensitivity:** $+3.0\% \text{ to } +5.0\%$ increase in total building electrical load per $1^\circ\text{C}$ ambient temperature rise above $24.0^\circ\text{C}$ (Default: **4.0%/°C**).
- **Latent Cooling Penalty:** $+10\% \text{ to } +30\%$ addition to sensible cooling load due to high tropical relative humidity (Default: **+20%**).
- **Equipment Ratings:**
  - Inverter Split AC (1.0 HP / 2.8 kWth): rated $0.8\text{ kW}$ (0.5–1.1 kW), modulates at 35% capacity.
  - Non-inverter Split AC (1.0 HP): rated $1.0\text{ kW}$ (0.7–1.3 kW), 50% duty cycle.
  - Inverter Split AC (2.0 HP / 5.6 kWth): rated $1.5\text{ kW}$ (1.2–1.8 kW).
  - Non-inverter Split AC (2.0 HP): rated $2.2\text{ kW}$ (1.6–2.8 kW).
  - Desktop PC + Monitor: active $150\text{ W}$ (100–200 W), idle $50\text{ W}$.
  - Rack Server (1–2U): $300\text{ W}$ continuous (100–500 W).
  - Network Switch: $20\text{ W}$ continuous.
  - LED Lighting Power Density: $10\text{ W/m}^2$ (fluorescent: $15\text{ W/m}^2$).
  - Nighttime Baseload (00:00–06:00): $5\% \text{ to } 15\%$ of daytime peak (Default: **10%**).

---

## 3. Solar PV System Technical Specifications

- **Governing AC Output Equation:**
  $$P_{\text{ac}}(t) = P_{\text{kWp}} \times \left(\frac{G_{\text{tilted}}(t)}{1.0\text{ kW/m}^2}\right) \times \left[1 + \gamma (T_{\text{cell}}(t) - 25^\circ\text{C})\right] \times \eta_{\text{inv}} \times \eta_{\text{BOS}}$$
- **Cell Operating Temperature:**
  $$T_{\text{cell}}(t) = T_{\text{amb}}(t) + \left(\frac{\text{NOCT} - 20}{800}\right) G_{\text{tilted}}(t) + \Delta T_{\text{roof}}$$
  where $\text{NOCT} = 45^\circ\text{C}$, $\Delta T_{\text{roof}} = +10.0^\circ\text{C}$ for close rooftop mounting.
- **Temperature Coefficient of Power ($\gamma$):** $-0.40\%/^\circ\text{C}$ (monocrystalline / PERC silicon range: $-0.35\% \text{ to } -0.43\%/^\circ\text{C}$).
- **Overall Performance Ratio (PR):** $0.70 \text{ to } 0.80$ (Default: **0.77** / 77.1% based on Tarlac rooftop case study).
  - Temperature loss: ~8%
  - Soiling loss: ~3% (annual without washing)
  - Wiring & mismatch: ~2.5%
  - Inverter loss: ~2% (peak efficiency: 98.0%, SMA Sunny Boy benchmark)
- **Monitored Specific Yield (103 Philippine Systems Study, 2025):**
  - Average (Luzon, 0° tilt): **$1,298\text{ kWh/kWp}\cdot\text{yr}$** (~$3.6\text{ kWh/kWp}\cdot\text{day}$).
  - Interquartile range: $1,200 \text{ to } 1,400\text{ kWh/kWp}\cdot\text{yr}$.
  - Top-tier rural systems (unshaded, tilted): $1,600 \text{ to } 1,650\text{ kWh/kWp}\cdot\text{yr}$.
- **Rooftop Area Requirement:** $6.0\text{ m}^2\text{ per kWp}$ ($1.6\text{--}2.0\text{ m}^2$ per 400W module).
- **Rooftop Wind Rating Standard:** $200 \text{ to } 250\text{ km/h}$ structural survival (National Structural Code of the Philippines).

---

## 4. Battery Energy Storage System (BESS) Parameters

- **Battery Chemistry:** Lithium Iron Phosphate (LFP / $\text{LiFePO}_4$).
- **Round-Trip Efficiency (RTE):** $92.0\%$ (symmetric charge/discharge efficiency $\eta_{\text{chg}} = \eta_{\text{dis}} = \sqrt{0.92} \approx 95.9\%$).
- **Depth of Discharge (DoD):** $90.0\%$ usable capacity.
- **Minimum State of Charge (Min SoC):** $10.0\%$ non-discretionary reserve floor to prevent cell under-voltage.
- **Continuous Power Limits (C-Rate):**
  - Maximum continuous charge: $0.5\text{C}$ (e.g. 50 kW for 100 kWh battery).
  - Maximum continuous discharge: $1.0\text{C}$ (e.g. 100 kW for 100 kWh battery).
- **Cycle Life:** 4,000 cycles at 80% DoD and 25°C to 80% capacity retention (~10–15 year calendar life).
- **Thermal Degradation Rate:** Cycle life degrades by roughly $2\times$ per $10^\circ\text{C}$ operating temperature above $25^\circ\text{C}$ if unconditioned.
- **Self-Discharge Rate:** $2.0\%/\text{month}$ idle loss at tropical ambient temperatures.
- **Tare / Standby Parasitic Consumption:** ~20–50 W continuous for BMS and inverter idle circuits.

---

## 5. Critical Load Tiers & Priority Load Shedding

Standards: Philippine Electrical Code (PEC), NFPA 110, commercial microgrid resilience literature.

| Tier | Designation | Typical % of Peak Load | Demand (35 kW peak) | Permissible Transfer Delay | Included Equipment |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **Tier 1** | **Life Safety & Emergency** | **~2%** (1–2%) | ~0.7 – 1.0 kW | Instant (UPS) / <10 s | Egress/exit LED signs, fire alarm panels, smoke detectors. |
| **Tier 2** | **Important & Operational** | **~18%** (15–20%) | ~6.0 – 7.5 kW | $\le 60\text{ s}$ | Main network switch, core routers, campus server, 10–15 critical lab PCs, security cameras. |
| **Tier 3** | **Comfort & Deferrable** | **~80%** (75–85%) | ~28.0 – 30.0 kW | Shed immediately (0 s) | All split AC units, general classroom lighting, kitchen appliances, water coolers. |

- **Battery Runtime Impact (Example 100 kWh usable battery, 12.5 kW avg load):**
  - 100% Load (no shedding, 12.5 kW): Runtime = 8.0 hours.
  - Tier 1 + 2 Only (~2.5 kW): Runtime = 40.0 hours (5× runtime extension).
  - Tier 1 Only (~0.5 kW): Runtime = 200 hours.

---

## 6. Outage Reliability Statistics & Stochastic Parameters

- **Utility Landscape (Urban vs. Rural Cooperative):**
  - Meralco (Metro Manila, 2025): $\text{SAIFI} = 0.91\text{ interruptions/customer-yr}$, $\text{SAIDI} = 97.5\text{ min/customer-yr}$ (CAIDI ≈ 1.79 h).
  - ALECO (Albay rural cooperative, 2025): $\text{SAIFI} \approx 53\text{ interruptions/customer-yr}$.
  - Ilocos Norte Electric Cooperative (INEC): Semi-rural cooperative exposed to western Pacific typhoons, overhead radial feeders, and seasonal monsoons. Reliability aligns with rural cooperative benchmarks.
- **Typhoon Empirical Case Study (Super Typhoon Nando, Sept 2025):**
  - Abra EC, Batanes EC, and **INEC suffered 100% grid blackouts**.
  - At 48 hours post-landfall, only 66% of municipalities were re-energized; over 638,000 households (60–70%) remained without power. Rural feeder restorations required 3 to 7 days.
- **Outage Generator Stochastic Parameters:**
  - **Arrivals:** Poisson process with rate $\lambda$ (Exponential interarrivals $t_i = -\ln(1-U)/\lambda$).
  - **Durations:** Lognormal distribution $\ln(D) \sim \mathcal{N}(\mu, \sigma^2)$ (Median = $\exp(\mu)$, Mean = $\exp(\mu + \sigma^2/2)$).
  - **Normal / Baseline Year:**
    - $\lambda = 3.0\text{ outages/yr}$ (mean interarrival ~122 days).
    - $\text{Lognormal}(\mu = 1.2, \sigma = 0.8)$: Median = $3.32\text{ hours}$, Mean = $4.56\text{ hours}$.
    - Outage cause split: 90% unplanned faults / 10% scheduled maintenance.
  - **Typhoon / Extreme Year:**
    - $\lambda = 8.0\text{ outages/yr}$ (mean interarrival ~46 days).
    - $\text{Lognormal}(\mu = 2.3, \sigma = 1.0)$: Median = $9.97\text{ hours}$, Mean = $16.4\text{ hours}$. Includes 1–2 major storm outages lasting 24–48 hours.
    - Solar depression coupling: 3–5 consecutive days of depressed GHI (20%–30% of normal clear-sky insolation).
    - Outage cause split: 95% storm damage / 5% maintenance.

---

## 7. Monte Carlo Simulation Design & Statistical Rigor

- **Replication Sizing Equation:**
  $$n \approx \left(\frac{z_{1-\alpha/2} \cdot \sigma}{\delta}\right)^2$$
  where $z_{0.975} = 1.96$ for 95% confidence level, $\sigma$ is estimated from a pilot sample ($n_0 = 30$), and $\delta$ is the target margin of error (half-width tolerance).
- **Sequential Stopping Criterion:**
  $$\frac{z_{1-\alpha/2} \cdot s_n}{\sqrt{n}} \le \delta$$
  Stop sampling when the confidence interval width drops below $\delta$ (with minimum $n \ge 50$ to avoid premature stoppage).
- **Reported Percentiles:** $P_5$ (optimistic / 5th percentile), $P_{50}$ (median), $P_{95}$ (worst-case risk / 95th percentile).
- **Random Number Generation:** Dedicated PRNG with fixed seed `0` for deterministic reproducibility across runs.

---

## 8. Multi-Criteria Decision Analysis (AHP) Parameters

- **Saaty's Pairwise Comparison Scale:** 1 (Equal), 3 (Moderate), 5 (Strong), 7 (Very Strong), 9 (Extreme), with intermediate values (2, 4, 6, 8) and reciprocal values ($1/k$).
- **Random Consistency Index ($RI_n$):**
  - $n=3$: 0.58; $n=4$: 0.90; $n=5$: **1.12**; $n=6$: 1.24; $n=7$: 1.32.
- **Consistency Verification:**
  $$CI = \frac{\lambda_{\max} - n}{n - 1}, \quad CR = \frac{CI}{RI_n} \le 0.10 \quad (10\%)$$
- **Default Criteria Hierarchy & Weights (Institutional Sizing):**
  1. Energy Reliability & Resilience (Outage hours covered, unserved kWh): **0.35**
  2. System Cost (CapEx for PV and BESS): **0.25**
  3. Economic Return / LCOE: **0.15**
  4. Environmental Benefit (Grid kWh offset, $t\text{CO}_2e$ avoided): **0.15**
  5. Technology Risk & Battery Degradation: **0.10**
- **Economic Assumptions (Labelled):**
  - Commercial Rooftop PV Installed Cost: PHP 45,000–55,000 / kWp ($800–$1,000/kWp).
  - Commercial LFP BESS Installed Cost: PHP 12,000–16,000 / kWh ($220–$290/kWh).
  - Commercial Retail Tariff (Luzon): PHP 11.50 / kWh.

---

## 9. Model Verification & Validation (V&V) Standards

Since utility bills are synthetic/mock rather than real MMSU meter records:
1. **Physical Conservation Invariant:**
   $$\sum_{t=1}^{8760} \left( E_{\text{solar}, t} + E_{\text{grid\_in}, t} + E_{\text{bat\_dis}, t} \right) = \sum_{t=1}^{8760} \left( E_{\text{demand}, t} + E_{\text{bat\_chg}, t} + E_{\text{losses}, t} + E_{\text{curtail}, t} \right) \pm 10^{-5}\text{ kWh}$$
2. **ASHRAE Guideline 14 Calibration Limits (vs. Synthetic Bills):**
   - Normalized Mean Bias Error: $\text{NMBE} \le \pm 5.0\%$
   - Coefficient of Variation of RMSE: $\text{CV(RMSE)} \le 25.0\%$
3. **Plausibility Envelopes:**
   - Solar AC Specific Yield: $1,200 \le Y \le 1,600\text{ kWh/kWp}\cdot\text{yr}$ ($Y > 1,700$ flags missing losses; $Y < 1,000$ flags excessive clipping).
   - Facility Annual EUI: $150 \le \text{EUI} \le 300\text{ kWh/m}^2\cdot\text{yr}$ for an air-conditioned college facility.
   - Self-sufficiency without battery: $10\% \text{ to } 30\%$.
