## University Building Energy Use Modeling in Tropical Climate

**Equipment Power Ratings:** Typical appliances and systems in a 2–3 thousand m² college building include HVAC, plug loads, and lighting.  Split‐type air conditioners have rated input roughly proportional to capacity.  Industry sources report ~0.8–1.2 kW per ton (≈3.5 kW) of cooling.  For example, a 2.7 kW (≈0.75 HP) split AC is rated ~810 W and a 6.5 kW (≈2.3 HP) unit ~2000 W.  Inverter ACs typically draw less than non‐inverter models of the same capacity (e.g. ~720–950 W for ~3 kW units).  In practice compressors cycle on/off: a non‐inverter may average ~50% of rated power; an inverter modulates near ~30–50% of full rating [Inference]. Desktop PCs (towers) draw ~100–200 W when active (idle ~50 W), laptops ~20–60 W, LCD/LED monitors ~15–30 W each [Inference].  LED lighting in classrooms/offices is on the order of 8–15 W/m² (older fluorescent ~10–20 W/m²) [Inference].  A typical data projector uses ~200–300 W in use [Inference].  A small server or networking switch may draw 100–500 W (server higher end) [Inference].  Printers use ~100 W when printing (idle ~10 W) [Inference].  Water coolers/dispensers use ~50–100 W for heating/cooling cycles [Inference].  Elevators or pumps (if any) have high peak power (several kW) but operate infrequently; Indonesian office data show lifts ~7% of building energy.  

**Energy Use Intensity (EUI) and End‐Use Shares:**  Published studies give air‐conditioned offices around 160–275 kWh/m²·yr in tropical SE Asia.  A Philippine DOE survey found office buildings’ EUI ≈213–336 kWh/m²·yr (median ~275).  In Indonesia a sample of air‐conditioned offices averaged ~160 kWh/m²·yr.  (By comparison, temperate European office EUI might be ~100; tropical schools/offices are much higher due to air‐conditioning demand.)  Cooling (HVAC) typically dominates energy use: on the order of 60–65% of total.  For example, an audit of a Philippine university office found AC use ~63%, lighting ~23%, and other plug loads ~14% of electricity.  The Indonesian study similarly found HVAC ~64.7%, office equipment ~15%, lighting ~8.8%.  Based on these, one can allocate roughly two‐thirds of building energy to cooling, ~10–25% to lighting, and ~10–15% to plug loads (computers, lab equipment, etc.) in an air‐conditioned educational facility.  

**Cooling Load vs. Temperature:**  Cooling energy rises roughly linearly with outdoor temperature above a “balance‐point” (indoor setpoint).  A common approach is to use Cooling Degree Days: e.g. with base ~24 °C (≈75 °F) indoor comfort.  One can define daily CDD = max$(T_{\rm out} -24°C,0)$.  Empirically, each 1 °C increase above the balance point adds on the order of a few percent to the cooling load.  (For example, tropical office data imply ~3–5% higher total load per °C heating of outdoor temp.)  Humidity further increases load (latent cooling): humid air can add another ~10–30% to cooling demand [Inference].  In practice one may fit a piecewise linear model: no cooling below 24 °C, linear above, or use CDD accumulation.  

**Occupancy & Equipment Schedules:**  University buildings have variable schedules.  On weekdays, occupancy and loads rise from morning (class start ~8–9 AM) through early afternoon and decline by early evening (classes often end by 5–6 PM).  Equipment (PCs, projectors) and lights follow class schedules.  There are few (if any) classes on weekends or academic breaks, so loads drop drastically (only base systems and select labs remain powered).  Nighttime base load (midnight–6 AM) might be ~5–15% of daytime peak, from security lights, servers, etc.  (These patterns are inferred from typical school operation; actual schedules depend on the institution.) [Inference].  

**Hourly Load Profile Shape:**  An illustrative profile for a weekday might be: negligible usage at 0–6 AM; ramp-up 7–9 AM; peak flat plateau through midday (9 AM–3 PM), then decline by 6–8 PM to low nighttime base.  Weekends would be a flat low profile.  (For example, an Indonesian office had ~25% of max load at 7 AM ramping to 100% by 11 AM, staying high till 4 PM, then tapering [Inference].)  In practice, one can scale such normalized profiles to the building’s peak kW or integrate the CDD-based cooling load curve plus fixed plug/lighting demand.  

**Parameter Values (low/typical/high/default):** The table below summarizes the key parameters with source references and notes.  Values marked “[Est]” are our best estimates when no source was found.  Defaults may be used in the simulation, with ranges for sensitivity:

| Parameter                       | Low      | Typical | High     | Default | Units        | Source/Notes                                            |
|---------------------------------|----------|---------|----------|---------|--------------|---------------------------------------------------------|
| **A/C rated input**             |          |         |          |         |              |                                                         |
| – Inverter split AC (per 1 HP)  | 0.5      | 0.8     | 1.1      | 0.8     | kW           | DOE labels: ~780–950 W for 2.6–3.0 kW (1 HP) units; [Est] duty cycles lowers avg. |
| – Non-inverter split (1 HP)     | 0.7      | 1.0     | 1.3      | 1.0     | kW           | [Inference] slightly higher; Indonesian example ~831 W for 1.5HP unit.                |
| – Inverter split AC (2 HP)      | 1.2      | 1.5     | 1.8      | 1.5     | kW           | Scaled from 1 HP values and AUX data (1.2–1.8 kW per 1.5 ton).                    |
| – Non-inverter split (2 HP)     | 1.6      | 2.2     | 2.8      | 2.2     | kW           |  [Inference] roughly COP ~3–3.5.                              |
| **Duty cycle (compressor)**     |          |         |          |         | %            |                                                         |
| – Non-inverter AC (on-cycle)    | 40%      | 50%     | 60%      | 50%     | % of time    | [Inference] approximate on‐time fraction during occupancy.         |
| – Inverter AC (modulated)      | 20%      | 35%     | 50%      | 35%     | % of time    | [Inference] inverter runs at reduced power, possibly average ~30–50%. |
| **Desktop PC**                  | 50       | 150     | 300      | 150     | W            | [Est] Typical tower PC with monitor: 100–200 W in use (Idle ~50 W).        |
| **Laptop (active)**             | 15       | 45      | 90       | 50      | W            | [Est]  Typical laptop (50 W) or tablet (<20 W).                  |
| **Monitor (LED)**               | 10       | 25      | 50       | 20      | W            | [Est] ~15–30 W for 22–27″ LED monitor.                           |
| **Fluorescent lighting**        | 12       | 15      | 20       | 15      | W/m²         | [Est] Older offices: 15 W/m² (total installed).  Higher if older fixtures.      |
| **LED lighting**               |  8       | 10      | 12       | 10      | W/m²         | [Est] Modern LED ~8–10 W/m² for office/classroom lighting.    |
| **Projector**                  | 100      | 200     | 300      | 200     | W            | [Est] Small classroom projector.                                 |
| **Small server**               | 100      | 300     | 500      | 300     | W            | [Est] Single 1–2U server or NAS.                                 |
| **Network switch/router**      | 5        | 20      | 50       | 20      | W            | [Est] Switch ~20 W; router 5–10 W.                              |
| **Printer (active)**           | 20       | 100     | 250      | 100     | W            | [Est] Laser printer in use ~100 W; standby ~5–10 W.            |
| **Water dispenser**            | 20       | 50      | 100      | 50      | W            | [Est] Heating element for hot water ~50 W on average.          |
| **Elevator motor**             | 1,000    | 5,000   | 10,000   | 5,000   | W            | [Est] If building has an elevator (rare), each up-call ~5–10 kW but very infrequent. |
| **Lighting schedule**          | Off      | 8am–5pm | 24/7     | 8am–5pm | hours/week   | [Est] Typically on during office hours; near zero in summer break.       |
| **AC schedule (occupied)**     | Off      | 8am–5pm | 24/7     | 8am–5pm | hrs/day      | [Est] Cooled during occupied hours; off or setback nights/weekends.      |
| **Base load (night)**         | 0.05×peak | 0.10×peak | 0.20×peak | 0.10×peak | fraction    | [Inference] Typical non-AC base (lights/offices off) load ~5–10% of daytime peak.  |

*Notes:* Cooling duty cycles and schedules are estimates; actual use may vary.  Shares and EUI are supported by cited studies.  

**Worked Example – Classroom and Lab:**  
Consider a 50 m² classroom with one 3.5 kW (1.0 HP) AC, lighting (10 W/m²), and 1 PC+monitor.  Assuming 8 hours of use (8 AM–4 PM):  
- **AC energy:** Rated ~0.8 kW (from DOE labels). If running ~60% of time on average, 0.8 kW×0.6×8 h ≈ 3.8 kWh/day.  
- **Lights:** 50 m²×10 W/m²=500 W; 8h ⇒ 4.0 kWh.  
- **PC+monitor:** 150 W; 8h ⇒ 1.2 kWh.  
- **Total ≈9.0 kWh/day** for the classroom.  

For a 100 m² computer lab with two 5.3 kW (1.5 HP) ACs, 20 PCs, lighting (10 W/m²), and a projector (200 W), 8 AM–6 PM (10 h):  
- **ACs:** Each ~1.4 kW (typical inverter 1.5 HP); assume 50% duty ⇒ 1.4×0.5×2units×10h ≈ 14 kWh.  
- **Lights:** 100 m²×10 W/m²=1,000 W; 10h ⇒ 10 kWh.  
- **20 PCs:** 20×150 W=3,000 W; 10h ⇒ 30 kWh.  
- **Projector:** 0.2 kW×10h = 2 kWh.  
- **Total ≈56 kWh/day** for the lab.  

These examples use the default values above; actual consumption depends on occupancy, equipment power, and duty cycles.  All input data and assumptions are drawn from cited sources or expert estimation (marked above), to guide a bottom-up demand model.

**Sources:** Primary data from Philippines DOE energy labels (AC ratings) and energy audits, Asian building studies, and manufacturer/industry figures.  Where no direct source exists (schedules, duty cycles, some appliance draws), estimates are noted [Inference]. 