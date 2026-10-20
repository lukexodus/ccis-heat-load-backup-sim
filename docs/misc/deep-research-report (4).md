## Outage Reliability in Ilocos Norte and the Philippines

The **System Average Interruption Frequency Index (SAIFI)** measures the average number of sustained interruptions a customer experiences per year.  **SAIDI** (System Average Interruption Duration Index) measures the total outage minutes per customer per year.  **CAIDI** is defined as SAIDI/SAIFI (roughly the average restoration time per interruption).  For example, Manila Electric Co. (Meralco) – the country’s largest distributor – reported SAIFI ≈0.91 and SAIDI ≈97.5 minutes in 2025.  Rural cooperatives typically have much higher values: Albay Electric Coop. (ALECO) had SAIFI ≈53 in 2025 (i.e. ~53 outages/customer-year).  No public data was found for Ilocos Norte EC (INEC) itself; it likely sees higher indices than Meralco (given its terrain and fewer resources) [Inference].  (IEEE median SAIFI for US utilities is about 1.10, SAIDI ~2 hours, for comparison.)  In practice, DOE/NEA/ERC performance reports collect SAIFI/SAIDI for each cooperative, but these are not openly published except via FOI requests.  

### Outage Types (Planned vs. Unplanned)
Outages are either **planned** (maintenance or upgrades) or **unplanned** (faults, equipment failure, or weather).  Philippine reports generally treat major weather events (typhoons, monsoons) separately.  No published breakdown was found, but in distribution utilities worldwide unplanned causes (trees, poles, animals, storms, equipment faults) dominate outages.  We assume planned outages are a small fraction (<10%) of events [Inference], with the rest unplanned.  Among unplanned, storm-related events (typhoons, monsoon winds) cause the largest but rare outages, while everyday faults (transient line faults, equipment failures) cause smaller, more frequent interruptions.  (For example, during Typhoon Egay in 2023, dozens of transmission lines tripped; Meralco’s urban network saw 11 minutes of outage for 220,000 customers, whereas rural coops likely saw hours/days of outages.)  

### Typhoon Impacts on Ilocos Norte and Northern Luzon
Typhoons frequently cause prolonged blackouts in northern Luzon.  For instance, **Super Typhoon Nando (Sept 2025)** hit Ilocos and Cagayan regions.  The DOE reported that Nando caused three cooperatives – Abra EC, Batanes EC, and Ilocos Norte EC – to suffer *total* outages.  By ~48 hours after landfall, only ~66% (271 of 411) of the affected municipal areas had been re-energized, leaving over 638,000 households (~60–70% of served customers) still without power.  This implies multi-day restoration times for many rural customers.  By contrast, during **Typhoon Egay (July 2023)**, although many NGCP transmission lines in Luzon were felled, the urban Meralco grid restored 220,000 customers in about 11 minutes once plants came back online.  (Household outage durations in Ilocos during Egay were not reported, but similar line faults likely caused regional outages lasting hours to days.)  In general, **major typhoons cause large-scale outages lasting days** in cooperatives, while non-typhoon faults typically cause shorter interruptions (minutes to hours).  

### Outage Arrival and Duration Distributions  
Reliability studies often model outage *arrivals* as a Poisson process (constant-rate random events), equivalently assuming **exponential interarrival times**.  Restoration times (outage *durations*) are often fit to skewed distributions: common choices are **lognormal**, **Weibull**, **gamma**, or **exponential**.  For example, Dobson (2023) models restoration with either lognormal or exponential rate processes.  One empirical example (from a North American transmission event) used a lognormal duration distribution with parameters μ≈1.64, σ≈1.56 (implying median restore ≈5.15 h).  (That is, outage duration $D$ with $\ln(D)\sim N(1.64, 1.56^2)$).  In general, a lognormal or Weibull with mean in a few-hour range is typical for distribution systems.  For *interarrival* times, an exponential law (mean = 1/λ) is often assumed, where λ is the annual outage rate.  We adopt these standard forms: e.g. outages arriving as Poisson(λ) and durations as Lognormal(μ,σ) or Weibull($k,\lambda$).  

### Recommended Outage Parameters (Generators)  

Based on the above and the Philippine context, we recommend the following **generator settings**.  (Where no data exist, values are educated estimates [Inference]; cite as needed.)  

- **Low-outage scenario (very reliable year):** Outage rate λ ≈ 1–2 per year.  Use exponential interarrival (Poisson process) or an alternative (e.g. uniform-per-year) so that on average 1–2 outages occur.  For durations, use a relatively short mean, e.g. Exp(mean ≈ 2–4 h) or Weibull(k=1.5, scale=4 h).  
- **Typical year:** λ ≈ 3–5 outages per year.  Durations maybe Lognormal with median ~3–5 h (e.g. μ=1.1, σ=0.8 giving mean ~4 h) or Weibull(α=1.5, β≈6 h).  
- **Typhoon-heavy year:** λ ≈ 6–10 outages per year (several major storm events plus routine faults).  Durations get longer: e.g. assume one or two long outages (~24–48 h) plus others of ~5–10 h.  A mixed approach: for modeling, one could use a Weibull with higher scale (β≈10–15 h, shape k~2) or a lognormal with μ≈ln(10 h), σ≈1.0 (mean ≈15–20 h).  

These values can be justified by analogy to reported events: e.g. Nando’s multi-day blackouts (implying high λ and large durations), versus Meralco’s ~0.9 outages/year of ~1.6 h each.  

#### Parameter Table

| Parameter                    | Normal Year (estimate)       | Typhoon-Heavy Year       | Source / Notes                                    |
| ---------------------------- | ---------------------------- | -------------------------| ------------------------------------------------- |
| Outages per year, λ          | ~3 (Poisson rate)            | ~8 (Poisson rate)        | Assumed from typical vs. typhoon frequency [Inference] |
| Interarrival distribution    | Exponential (mean=0.33 yr)   | Exponential (mean=0.125 yr)| Poisson arrivals; adjust λ.        |
| Duration distribution        | Lognormal (μ≈1.2,σ≈0.8)      | Lognormal (μ≈2.3,σ≈1.0)  | E.g. median ≈4 h vs. ≈10 h; use lognormal or Weibull as above. |
| Duration mean (approx)       | 4 hours                      | 12–15 hours              | Based on Meralco ~1.6 h (with events suppressed) vs. multi-day storms.  |
| Planned vs. unplanned split  | ~10% planned / 90% faults   | ~5% planned / 95% faults [Inference] | Philippine data not available; assume most outages are unplanned. |

*(All values above are for guidance. “Source” notes indicate whether based on published data or our estimates. E.g., Meralco’s SAIFI/SAIDI are cited, ALECO’s SAIFI. Other values are not explicitly published for Ilocos coops, so are inferred from analogous cases.)*

### Example: Generating One Year of Outages

As a concrete illustration, suppose a *normal* year with Poisson rate λ=3 (outages/year) and durations ~Exp(mean=4 h).  One can simulate as follows (in plain math): 

- **Sample number of outages:**  Draw an integer $N\sim\text{Poisson}(3)$.  
- **Interarrival times:**  Alternatively (if simulating arrival times), draw independent uniforms $U_i\in(0,1)$.  Then set interarrival time $t_i = -\ln(1-U_i)/\lambda$ (years).  This gives exponentially-distributed gaps with mean $1/\lambda=1/3$ yr (≈4 months).  Cumulatively sum the $t_i$ to get each outage’s start time.  
- **Durations:**  For each outage $i$, draw another uniform $V_i\in(0,1)$ and compute duration $d_i = -4\ln(V_i)$ hours (since Exp(mean=4) means density $f(d)=\frac1{4}e^{-d/4}$).  

For example, if $U_1=0.5$, then $t_1 = -\ln(0.5)/3 ≈ 0.231$ years (~84 days) to first outage.  If $V_1=0.2$, then $d_1 = -4\ln(0.2) ≈ 6.4$ hours.  Repeat to generate all events in the year.  

Thus the outage process is defined by the rate λ (or mean interarrival) and a specified duration distribution.  Different parameters (e.g. higher λ or heavier-tailed durations) can be used for the “high-outage” (typhoon) scenario.  In all cases we assume independent sampling and no forced ordering of outages across the year (a common Monte Carlo approach).  

**Sources:**  Definitions and formulas for SAIFI/SAIDI are standard.  The Meralco and ALECO indices are from published reports.  Typhoon outage data are from DOE/NEA updates.  Outage modeling assumptions (Poisson arrivals, lognormal/Weibull durations) are common in power-system reliability research.  Any parameter not found in Philippine sources is explicitly noted as estimated.

