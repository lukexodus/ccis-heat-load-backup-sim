> [!NOTE]
> **Archival Provenance Notice:** This document is an early course brainstorming draft predating project initialization. Its preliminary descriptions (e.g., real electricity bills, daily time step, simplified battery model) are superseded by the formal decision log (`docs/decisions/decision-log.md`, [D-01]–[D-18]) and the canonical conceptual model (`docs/context/conceptual-model.md`). Kept for historical provenance and traceability.

# **IDEA \#1: CCIS Heat, Load and Backup Power Simulation**

# **1\. Overview**

To simulate the electricity use of the College of Computing and Information Sciences (CCIS), and test whether rooftop solar panels and a battery could keep it running through hot days and power outages.

**Main question.** How much does Batac's heat raise CCIS's electricity use, and how much of that load could solar plus a battery cover during a heat wave or an outage?

**Why this problem.** Hot weather raises air-conditioning load, outages interrupt classes and lab work, and solar is a realistic option for a campus in Ilocos Norte. The topic is local, small enough to finish in two weeks, and has a clear what-if question for a Modelling and Simulation course.

**What we will deliver**

•       A working simulation (Python or Excel) of CCIS demand, solar output and battery use.  
•       Charts comparing solar and battery sizes under normal and hot years.  
•       A short recommendation, for example which size covers most of a heat-wave day.  
•       A validation check showing the model matches real electricity bills.

**Scope limit.** CCIS only (one college), not the whole campus or all of Luzon. If CCIS shares a meter with other buildings, we model the shared zone and say so.

## **2\. How the model works**

The model runs one day at a time (later, one hour at a time) and answers: how much electricity does CCIS need, how much can solar make, and what does the battery do about the gap?

**Part A: Demand (how much CCIS needs).** Start with a bottom-up estimate: count equipment (air conditioners, computers, lights, servers), multiply by power rating and hours of use, and add them up. Then make it respond to heat: cooling use rises when the outside temperature goes above a threshold, and falls during semester breaks and holidays. Fit the unknown numbers to the real electricity bills.

**Part B: Solar (how much the sun can supply).** NASA POWER is a free service that gives daily weather history for any coordinates, including how much sunlight reaches the ground. We use Batac's coordinates. Panel output is estimated as:

*E\_{solar} \= P\_{kWp} \\times H\_{sun} \\times PR*  
Here P is panel size in kWp, H is that day's sunlight in kWh per square metre, and PR is a performance ratio of about 0.75 to 0.80 that accounts for heat, dust and wiring losses.

**Part C: Battery (what happens to the gap).** Each day the model compares solar with demand:

1\.      If solar is more than demand, the extra charges the battery until it is full.  
2\.      If demand is more than solar, the battery discharges until it is empty.  
3\.      Whatever is still missing comes from the grid. During an outage, it counts as unserved load.

**Part D: Monte Carlo (repeat with many possible years).** We replay many years of real weather, and randomly add outage events, then look at the spread of results instead of one answer. This shows the bad cases too, such as several cloudy days in a row.

**Worked example.** A day has 5 kWh/m2 of sunshine, and we assume 100 kWp of panels with PR of 0.8. Solar gives 100 x 5 x 0.8 \= 400 kWh. If CCIS needs 300 kWh that day, 100 kWh goes to the battery. If CCIS needs 500 kWh, the battery or the grid covers 100 kWh.

**Tools.** Python (pandas, numpy, matplotlib) is the simplest choice, and Excel can work for a smaller version. Any tool the team prefers is fine.

## **3\. Data we need**

The weather is free and public. The electricity data must be requested from MMSU, so that request is the first task.

| Data | Source | How to get it | Priority |
| :---- | :---- | :---- | :---- |
| Electricity bills (kWh, peak kW, pesos, billing dates), last 3 to 5 years | Physical Plant or Budget and Accounting office | Written request letter | Critical |
| Daily or hourly meter readings, if they exist | Physical Plant or the electric cooperative | Ask in the same letter | Very useful |
| Is there a separate CCIS meter? | Physical Plant | Ask in the same letter | Critical |
| Equipment list: air conditioners (rating), computers, lights, servers, and daily hours of use | CCIS itself | Walk through the building and count | Critical |
| Floor area and rooftop area available for solar | CCIS and Physical Plant | Ask, or estimate from a floor plan | Important |
| Power interruption records (dates, durations) | Physical Plant | Same letter | Important |
| Academic calendar and holidays | Registrar | Public or from the college | Important |
| Daily temperature, humidity, solar radiation for Batac, 1981 to now | NASA POWER (free web service) | Download by coordinates | Critical |

**If data is limited.** Monthly bills alone are workable: validate at monthly level and build the daily pattern from the equipment audit. State this limit in the report.

**Assumptions we may need.** Solar and battery performance numbers (efficiency, losses) and prices will come from published ranges, and we will cite them and label them as assumptions. Main results will be in kWh, not pesos, so they stay valid even if prices are uncertain.

## **4\. Scenarios, outputs and validation**

We run a small grid of what-if cases and judge each by how much of CCIS's load it covers.

| Factor | Levels to test |
| :---- | :---- |
| Weather | Normal year, hot year (about \+2 degrees C), the hottest year on record |
| Solar size | 0, 50, 100, 200 kWp (limited by rooftop area) |
| Battery size | None, small, large (sizes to be set from the load) |
| Outage | 4 hours, 12 hours, 24 hours, starting at a random time |

**Outputs we will report**

•       A plot of daily electricity use against temperature, with the fitted line.  
•       Share of yearly CCIS electricity that solar and battery supply, for each size.  
•       Hours of a typical outage that the system can fully or partly cover, including critical loads only (servers, lights, some computers).  
•       A distribution (spread) of results across weather years, so we can show best, typical and worst cases.  
•       One recommendation, for example the smallest solar and battery combination that covers a 12-hour outage on a hot day.

**How we validate**

1\.      Split the bills into two parts: fit the demand model on the earlier part, then predict the later part and compare.  
2\.      Compare the bottom-up equipment estimate with the actual bill; they should agree within a reasonable margin, and we explain any gap.  
3\.      Report errors clearly (percent error in monthly kWh, or RMSE for daily data).  
4\.      Check solar output against typical Ilocos values, for example yearly yield per kWp from published sources.

**Sanity checks built into the code.** Energy must balance each day (supply plus battery change equals demand), the battery never goes below empty or above full, and results change in the expected direction when a factor changes.

## **5\. Strengths, weaknesses and risks**

The project is realistic and local, and its biggest weakness is that it depends on getting electricity data from the university.

| Strengths | Weaknesses |
| :---- | :---- |
| One college keeps the scope small and finishable in two weeks | Result applies to CCIS only, not the whole campus or other buildings |
| Weather data is free, long and public (NASA POWER) | Depends on the Physical Plant giving us bills and meter data |
| Our own building: we can count equipment and check schedules ourselves | Monthly bills give few data points, so fitting and validation are weaker |
| Clear what-if question and a practical answer (solar and battery size) | One NASA POWER grid cell covers a wide area, so local sunshine may differ slightly |
| Fits the course: build, calibrate, validate, then test scenarios | Solar and battery performance and prices are assumptions from published ranges |
| Easy to extend later (other colleges, more buildings) | Does not model the grid itself, tariffs or net-metering rules |

