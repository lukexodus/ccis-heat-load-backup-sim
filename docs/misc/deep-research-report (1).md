## Solar PV Performance Parameters

**Module Efficiency and Temperature Coefficient:**  Modern crystalline‐silicon PV modules (polycrystalline or monocrystalline) typically convert about 15–22% of sunlight into electricity at standard test conditions (25°C).  For example, inexpensive polycrystalline panels often run ~14–18% efficient, while high-end monocrystalline panels can reach ~20–22%.  In hot, humid conditions the *cell temperature* rises above 25°C and reduces power output.  The loss is captured by the *temperature coefficient of power* (γ, in %/°C): most Si modules have γ ≈ –0.3%/°C to –0.5%/°C (i.e. about –0.4%/°C typical).  This means for each °C above 25°C, power drops by ~0.4%.

**Cell Temperature (NOCT):**  A key practical value is the module’s **Nominal Operating Cell Temperature (NOCT)**, defined as the module temperature under 800 W/m² irradiance, 20°C ambient, wind 1 m/s, open rack.  Many modules have NOCT ≈40–50°C (typical ~45°C).  On a sunny hot day (e.g. ambient 30°C, irradiance 1000 W/m²), actual cell temp can exceed NOCT; a simple model is:  
$$T_{\rm cell} \approx T_{\rm amb} + (T_{\rm NOCT}-20^\circ C)\times \frac{G}{800\rm\ W/m^2}\,. $$  
So at 1000 W/m² and T_amb=30°C, T_cell ≈30 + (45–20)×(1000/800) ≈ 30 + 25×1.25 ≈ 61°C.  **Roof mounting** on a hot tropical roof often adds another ~10°C or more.  

**Performance Ratio (PR):**  The *performance ratio* (PR) is the ratio of actual energy output to the ideal output if the system ran at STC.  It accounts for all losses (soiling, wiring, inverter, etc.).  High-quality systems in good climates reach PR up to ~80%.  In tropical rooftop systems, PR is often in the 70–80% range.  Major loss components include:  
- **Temperature loss:**  High module temperatures reduce output.  For a 20°C temperature rise above 25°C and γ≈–0.4%/°C, expect ~8% power loss.  
- **Soiling:**  Dust, bird droppings, etc., typically cause ~2–5% annual loss unless cleaned.  
- **Wiring and mismatch:**  Series resistance and panel mismatches cause ~2–3% losses.  
- **Inverter inefficiency:**  Modern inverters reach ~96–99% peak efficiency.  At low loads efficiency falls slightly; overall system loss ~3–5%.  
- **Shading:**  Even small shade can sharply cut output if panels are not optimally oriented (try to avoid roof shadows).  
Summing these, a realistic PR for a tropical rooftop plant is often 75% (default).  A beginner can think: if 1000 kWh of sunlight hits a panel, a PR of 75% means 750 kWh is delivered to the grid (after all losses).  

**Inverter Efficiency and Degradation:**  Inverters convert DC from panels to AC.  Modern string or hybrid inverters reach **~95–99%** peak efficiency.  For instance, an SMA Sunny Boy 9–11 kW inverter lists max efficiency 98.7% (CEC efficiency 98.5%).  Smaller off-grid inverters may be slightly less.  Over time inverters degrade very little (often <0.5% per year) as electronics.  PV *modules* degrade ~0.5–1.5%/yr depending on quality and climate (e.g. 0.5%/yr in a 3-year Thai system, up to ~1–1.4%/yr in 13-year old tropical systems).  Default PV module degradation ~0.5%/yr, and inverter degradation ~0.5%/yr, can be assumed unless data is available.  

**Rooftop Area, Tilt and Orientation:**  A typical panel is ~1.6–2.0 m² per kWp (assuming 15–20% efficiency: 1 kWp needs ~5–6 m² at 20% eff, or up to ~7 m² at 15%).  In practice assume ~6 m²/kWp default.  In the tropics near 18°N (Ilocos Norte), the sun is high: ideal tilt is fairly low.  Data for ~16°N (Agoo, Ilocos) suggests a fixed tilt ~15° facing south.  At 18°N the optimal tilt is similar (~15–18°).  The rule of thumb “tilt ≈ latitude” is slightly reduced near the equator.  Facing true south (toward equator) maximizes annual yield; small east-west tilts can be used on split rows.  

**PV Output Formula:**  To estimate AC output from irradiance and temperature, a simple formula is:  
> **AC_power = Gₚᵥ (kW/m²) × PanelArea (m²) × ModuleEff @ STC × [1 + γ (T_cell–25)] × InverterEff.  
 
Here Gₚᵥ is plane-of-array irradiance (kW/m²), T_cell is cell temp (°C), γ is per-degree power loss (e.g. –0.004/°C), and InverterEff ~0.96.  For a 100 kWp system receiving 5 kWh/m² daily (e.g. G=500 W/m² avg over day), panel area ≈100 kW/0.18 ≈556 m² (18% eff), STC output is 100 kW, cell temp maybe 60°C (35°C above 25°C) so power ≈100 kW·[1+(–0.004·35)]≈86 kW, inverter brings 86×0.96≈82.6 kW AC.  Over one 5 kWh/m² day (100 kW×5 h sun), AC energy ≈82.6×5≈413 kWh (≈4.13 kWh/kWp/day), matching ~75% PR.  

## Battery Parameters

**Chemistries:**  **Lithium Iron Phosphate (LFP)** is common for commercial/utility BESS.  For comparison, we note typical **Lead-Acid (flooded or AGM)** specs as well.  Other Li-ion (NMC, etc.) are less common in PV-coupled building storage.  

**Round-Trip Efficiency:**  This is the ratio of energy out/in.  LFP systems (with appropriate inverters/chargers) usually achieve ~90–95% round-trip efficiency.  Lead-acid is lower (around 70–80%); losses in charging (gassing) and lower depth of charge reduce effective efficiency.  

**Depth of Discharge (DoD) and Minimum State-of-Charge:**  – LFP cells can often be discharged deeply: *usable* DoD ~80–90%.  Many LFP battery systems allow 90% DoD, but for longevity 80% is a safe default.  (For example, an LFP cell might be rated for 5000 cycles if discharged to 80%.)  – Lead-acid should be kept shallower: ~50% DoD is typical recommended (some designs use 30–40% DoD to extend life).  Thus a lead-acid battery bank might keep 50% as the lowest state.  We mark LFP MinSoC ~10–20% left (DoD 80–90%), and lead-acid ~50% DoD (SoC never <50%).  

**Charge/Discharge C-Rates:**  – *LFP:*  Commercial LFP modules usually allow charging/discharging at ~0.5–1.0C continuously, and peaks to 2C or more.  (1C means 1-hour rate: e.g. a 100 kWh battery can deliver 100 kW continuously.)  – *Lead-Acid:*  Typically limited to low C-rates (~0.2C–0.3C) to avoid heating and sulfation.  Lead-acid batteries often “C/5” (0.2C) is used for long life.  –  In practice, hybrid inverters for buildings might cap battery power at ~0.5–1C of the capacity.  For example, [107] notes typical BESS sizes: ~100 kWh to 2 MWh capacity with ~50 kW to 1 MW inverter (0.05–0.5C).  Fast charging beyond 1C is usually avoided without special cooling.  

**Cycle Life and Degradation:**  – *LFP:* Very long-lived.  Datasheets often quote 3000–6000 cycles to 80% capacity at 25°C.  In practice, expect ~4000 cycles at 80% DoD (about 10–15 years at 1 cycle/day).  However, high ambient temperature greatly shortens life: a rule of thumb is that cycle life halves for each 10°C above ~25°C.  For example, a battery rated 4000 cycles at 25°C might only give ~2000 cycles if operated at 45°C.  In the Philippine tropics, keeping batteries in shade or cooled is important.  – *Lead-Acid:* Cycle life is much shorter.  Flooded/gel deep-cycle batteries might manage ~400–500 cycles at 80% DoD, or ~1000 cycles at 50% DoD.  Roughly, one may assume 500 cycles at 50% DoD.  – *Calendar degradation:* Both chemistries lose some capacity each year even if unused: LFP <3%/yr, lead-acid ~5%/yr.  We use typical calendar loss ~2%/yr LFP, ~5%/yr lead-acid (subject to temperature).  

**Self-Discharge and Standby Losses:**  Batteries slowly lose charge when idle.  – *LFP:* Very low self-discharge, ~1–3% per month.  – *Lead-acid:* Higher (~5% per month) and worse if hot.  Additionally, inverters/chargers draw a small standby current (tens of watts), but this is often neglected in hourly models (or assumed ~0.1–0.3%/day).  

**Sizes (Commercial Products):**  Typical commercial-sized BESS in the Philippines range from ~100 kWh up to multiple MWh.  For instance, a recent guide notes that a *“Commercial BESS Philippines”* project is often 100 kWh–2 MWh of LFP with ~50 kW–1 MW inverter.  Smaller systems (20–60 kWh) can be cabinet units (for clinics, small offices), while 200 kWh–1 MWh systems may be containerized.  Hybrid inverter/charger ratings often match battery power (e.g. a 100 kW inverter with 100 kWh battery, ~1C).  

**Dispatch Rules:**  A simple, defensible control strategy is:  (1) **Charge** the battery from any surplus PV generation (or from grid during low-price periods, if modeled).  (2) **Discharge** the battery to cover building load whenever PV is insufficient *and/or* to shave demand peaks (e.g. during high-rate hours).  (3) **Reserve:** always keep a minimum SoC (e.g. 20% for LFP, 50% for lead) to handle unexpected outages or peaks.  (4) If anticipating a power outage, maintain enough reserve (e.g. 10% of capacity) so that the battery can ride out a storm.  We can implement: if grid supply fails or brownout is imminent, switch to “backup mode” and discharge battery until reserve limit.  

## Irradiance and Yield Benchmarks (Ilocos Norte)

For Batac (18.06°N, 120.56°E) in northern Luzon, resource tools agree on a high tropical insolation.  The annual global horizontal irradiance is roughly 1700–1800 kWh/m².  **Specific yield** (AC kWh per kWp per year) can be estimated from this: tropical, low-tilt roofs give ~1200–1400 kWh/kWp·yr.  For example, a study of 103 real Philippine PV systems (all Luzon) found an average **1298 kWh/kWp** output in 2025.  That is ~3.6 kWh/kWp·day (after losses).  We can compare PV performance tools:  
- **Global Solar Atlas:** Reports ~1800 kWh/m²/yr for Batac (GHI) and yields ~1300–1350 kWh/kWp·yr for fixed roof-mount systems (per its PVOUT tools).  
- **PVGIS/NASA POWER:** NASA’s POWER tool gives 4.0–4.5 sun-hours/day (1460–1640 kWh/m²·yr) for horizontal. PVGIS (as of 2024 data) suggests ~1500–1600 kWh/m²·yr on a 15° tilt south. (Precise numbers depend on dataset version.)  
- **NREL PVWatts:** For Luzon, a PVWatts query (if run) yields ~1400–1500 kWh/kWp·yr.  
Overall, these models typically agree within ~10%.  The real data (~1300 kWh/kWp·yr actual) tends to be slightly lower than raw model output (~1400 kWh/kWp·yr) because of soiling, shading, and system losses.  Global Solar Atlas and PVGIS are based on satellite/climate data and generally accurate to within ~5–10% for the Philippines, but may slightly overestimate actual yields since they assume clean panels and optimal conditions.

Monthly, the best solar is late spring (March–May) and the worst is monsoon season (July–September).  A rough monthly distribution might be: 120–130 kWh/kWp in March/April down to 60–80 kWh/kWp in August.  (Model data can refine this if needed.)  For example, one analysis for Luzon shows ~5.5 kWh/kWp·day in spring vs ~3.0 kWh/kWp·day in August.  **Example:** on a day with 5 kWh/m² of irradiance (e.g. a clear day), a 100 kWp array (≈6×700 W panels) produces about 500 kWh of DC. With PR~0.75 and inverter~0.96, AC output ≈500×0.75×0.96≈360 kWh (so ~3.6 kWh/kWp).  

## Typhoon and Weather Effects

The Philippines has frequent tropical storms.  **Cloudy/Rainy reduction:** On heavy overcast days, generation can drop to 10–30% of clear-sky.  A typical monsoon/thunderstorm day (e.g. 50% diffuse light) might yield only ~2–3 kWh/m² (vs ~5–6 kWh/m² on sunny days).  Expect *rainy season* (Jul–Sep) to cut monthly yield by ~40–50%.  

**Multi-day outages:** Typhoons often bring several successive low-sun days.  Luzon might see 3–5 days of heavy clouds per strong typhoon.  Ilocos Norte might be affected by a few (say 2–4) typhoons per year, each causing 1–3 days of very low output.  For simulation, one could randomly model e.g. 5–10 days/year with 20–50% of normal irradiance (and 0% during actual storm hours if extreme).  

**Wind/Damage:**  Typhoon winds are a concern for PV mounting.  Philippine building codes and guidelines require rooftop PV to withstand very high winds (often ~200–250 km/h, akin to a strong typhoon).  Properly engineered frames (steel supports anchored to structure) are essential.  Past typhoons in the Philippines have occasionally damaged poorly secured panels, but well-designed systems (using hurricane-rated mounts) survive with minimal harm.  Hail is very rare in the tropics, so not a major factor.  

## Costs and Economics (*Assumptions*)

These are ballpark, with local currency (PHP) and USD.  
- **Rooftop PV installed cost:**  Recent commercial/industrial solar prices in the Philippines are on the order of PHP 40,000–60,000 per kW (US $700–1000/kW) installed.  (Lower bound from bulk projects, higher for small installs.)  For example, 2024 EPC bids for large rooftops have been ~PHP 45,000–50,000/kW (≈$800–900/kW)‡.  Panel + inverter costs are ~50–60% of that; rest is balance-of-system (mounting, wiring, labor).  These costs are falling, so check latest bids.  
- **Battery storage cost:**  LFP battery+inverter systems are roughly PHP 10,000–15,000 per kWh for commercial scale (≈$180–300/kWh) including BOS.  Thus a 100 kWh system might cost ~1.2 M–1.5 M PHP.  (Prices vary widely with scale and supplier; systems >500 kWh get lower $/kWh.)  
- **Electricity rate:**  Commercial electricity rates in Luzon are about PHP 10–15/kWh (≈$0.17–0.25/kWh) as of 2025, depending on utility and demand charges.  Residential rates (higher tiers) reach PHP 10–12/kWh for the first 1000 kWh, more for excess.  Net-metering (see below) effectively uses the retail rate.  
- **Net-metering and RE Act:**  Under RA 9513 (2008) and ERC regulations, qualifying customers may install rooftop PV and offset their bill.  As of 2023–25, residential/commercial net-metering in the Philippines typically limits system size to ~100 kW (gross) for a single meter, exporting excess at the full retail rate (no feed-in to grid for profit).  Larger systems require special contracts (e.g. QF status).  (Note: rules have been evolving; older net-metering capped at 30 kW, raised to 100 kW by ERC Order in 2021).  

*(Economic values change rapidly; check current DOE/ERC publications for up-to-date figures.)*  

## Summary of Recommended Parameters

The table below summarizes key parameters. *Values in bold are our recommended defaults.*  Sources (where found) are cited. Unverified estimates are noted.  

| Parameter                            | Low         | Typical      | High        | Default    | Source / Notes                                                  |
|--------------------------------------|------------:|-------------:|------------:|-----------:|-----------------------------------------------------------------|
| **Module efficiency (STC)**          | 15%         | **18%**      | 22%         | 18%        | Poly-Si ~14–18%; Mono up to ~20–22%.             |
| **Temp. coeff. of power (γ)**        | –0.5%/°C    | **–0.4%/°C** | –0.3%/°C    | –0.4%/°C   | c-Si γ ≈ –0.35 to –0.43%/K.                     |
| **Nominal O.C. cell temp. (NOCT)**   | 40°C        | **45°C**     | 50°C        | 45°C       | Typical ≈40–48°C; roof mount adds ≈+10°C. |
| **Performance Ratio (PR)**           | 70%         | **75%**      | 85%         | 75%        | Tropical rooftop ~70–80%; SMA notes “up to 80%”.     |
| **Inverter efficiency (peak)**       | 95%         | **98%**      | 99%         | 98%        | Modern inverters ~96–99%; e.g. SMA spec 98.7% max.  |
| **Degradation (modules)**            | 0.5%/yr     | **1.0%/yr**  | 1.5%/yr     | 0.5%/yr    | 0.5–1.4%/yr observed in tropics.                |
| **Degradation (inverter)**          | 0.1%/yr     | **0.2%/yr**  | 0.5%/yr     | 0.2%/yr    | (Estimate) inverter electronics lose <0.5%/yr.                   |
| **Area per kWp (tilt ~15°)**         | 5.5 m²/kW   | **6.0 m²/kW**| 7.0 m²/kW   | 6.0 m²/kW  | At 15–18% eff, 6 m²/kW is typical (1.6 m² per 300 W panel).    |
| **Tilt / orientation**               | 10°–20° S   | **15° S**    | 30° S       | 15° S      | Ilocos 18°N → tilt ~15° toward equator. Default 15° south.      |
| **Battery round-trip eff. (LFP)**    | 90%         | **92%**      | 95%         | 92%        | LFP (LiFePO₄) typically 90–95%.                                  |
| **Battery round-trip eff. (Lead)**   | 70%         | **75%**      | 80%         | 75%        | Lead-acid ~70–80% (lower when aged).                             |
| **DoD (usable)** (LFP)              | 80%         | **90%**      | 95%         | 90%        | Many LFP designs allow 90% DoD; default keep 80% to 90%.         |
| **DoD (usable)** (Lead)            | 30%         | **50%**      | 70%         | 50%        | Lead-acid best life at 30–50% DoD (1800–500 cycles). |
| **Min. SoC (LFP)**                  | 10%         | **10%**      | 20%         | 10%        | Reserve 10–20% for longevity/safety.                             |
| **Min. SoC (Lead)**                 | 30%         | **50%**      | 70%         | 50%        | Typically keep ≥50% SoC (≤50% DoD recommended).                 |
| **Charge C-rate (LFP)**            | 0.5C        | **1.0C**     | 2.0C        | 0.5–1.0C   | LFP cells often allow 1C; default 0.5–1C max.                   |
| **Charge C-rate (Lead)**           | 0.1C        | **0.2C**     | 0.3C        | 0.2C       | Lead-acid ~C/5 to C/3 to extend life.                            |
| **Cycle life (LFP @80% DoD)**      | 2000 cycles | **4000 cycles** | 6000 cycles | 4000 cycles | Typical 3000–6000 cycles to 80% at 25°C.            |
| **Cycle life (Lead @50% DoD)**     | 600 cycles  | **1000 cycles** | 1500 cycles | 1000 cycles | Victron: ~750 cycles @50% (gel).                  |
| **Self-discharge (LFP)**          | 1%/mo       | **2%/mo**    | 3%/mo       | 2%/mo      | Low self-discharge (~1–3%/month for LFP).                       |
| **Self-discharge (Lead)**         | 3%/mo       | **5%/mo**    | 8%/mo       | 5%/mo      | Lead-acid ~3–8%/month, worse when hot.                           |
| **Battery system sizes**           | 10 kWh      | 100 kWh      | 2000 kWh    | –          | Commercial BESS: ~100 kWh–2 MWh; inverters ~50–1000 kW. |
| **Dispatch rule**                 | –           | –            | –           | –          | E.g. charge from PV surplus, discharge at peak/off-hours or outage. |

Values labeled with **bold** default are recommended for simulation if only one number is used.  
Sources: [39,41,50,62,68,73,108,110,107] for key parameters; others are standard estimates.  Values in this table are a mix of cited data and conservative estimates appropriate for tropical Philippine conditions.

