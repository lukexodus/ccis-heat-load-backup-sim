# Definitions of critical, essential, and deferrable loads  
Critical (sometimes called “emergency”) loads are those whose loss would immediately endanger life or core operations.  Codes (e.g. NFPA/NEC as adopted in the Philippine Electrical Code) define an *emergency system* as one that **“automatically supply[ies] illumination, power, or both … to safeguard human life”** on utility failure.  A legally required *standby system* covers other safety-related loads (not life-safety) to minimize hazards.  In everyday terms, “critical” loads include fire/exits lighting, alarms, communications, medical or safety equipment, IT and data servers – anything that must stay on **without interruption**. 

By contrast, *non-critical* or *deferrable* loads are those that can tolerate a short outage.  For example, ordinary building lighting, HVAC (air conditioning), plug loads (printers, microwaves, etc.), and comfort features are typically considered non-critical.  Some authors use **“essential”** to mean loads needed for normal operation but which can survive momentary loss (e.g. emergency lighting that can turn on a few seconds after a generator starts).  In short: a load is critical if its brief interruption would be dangerous or disastrous; otherwise it is deferred or shed first.  

# Typical critical-load categories (college building)  
In a university classroom/lab/office building, typical critical-load categories might include:  
- **Exit and emergency lighting, fire alarms, safety signage (Tier 1 life-safety):** These are small loads (often just a few hundred watts total, ~1–2% of building demand) but must remain on continuously.  
- **Communications and IT equipment:** This includes network routers/switches, phone systems, wireless networks, server closets or the campus data center.  These might be on the order of a few kW, say **5–10%** of building load.  Data systems are often kept up to maintain campus communications.  
- **Selected office/lab computers or point-of-sale terminals:** A fraction of normal computing load (e.g. some essential workstations or cashiers) may be on an uninterruptible power supply.  This might be another **5–15%** of load.  
- **Ventilation fans and pumps (life-safety):** Ventilation for emergency exits and fire zones, or pumps for water supply/sprinklers, may be kept running.  Depending on building size, these can be a few kW (on the order of **5–10%**).  
- **Security systems:** Cameras, card-access controls, and intrusion alarms typically draw little power (≪1–2%).  They are often backed up to ensure building security during outages.  

By contrast, major HVAC (air conditioning) chillers or large office lighting circuits are usually *not* treated as critical in a solar-backup scenario.  (Fans for essential ventilation might stay on, but full cooling and non-emergency lighting would typically be shed.)  These comfort loads often dominate normal energy use (tens of percent each) but can be turned off during an outage with little immediate risk.  

*(These percentages are rough estimates for a medium-sized academic building.  Actual values vary by facility.  The ranges above are meant as plausible engineering assumptions [Speculation].)*  

# Critical-load fractions in published studies  
We did not find a single authoritative source giving fixed percentages for “critical load” in schools.  Different studies and standards make their own assumptions.  Some resilience analyses assume roughly 20–50% of a building’s peak demand qualifies as critical (justifying battery backup for that portion).  For example, one practical guideline notes that an entire facility’s *demand factor* for emergency loads is taken as 1.0 (i.e. all designated critical loads are assumed to run at full simultaneous load), implying these loads are a substantial subset of total demand.  In many case studies of commercial or hospital backup power, life-safety systems alone are often only ~5–15% of demand, with “standby” loads bringing the total critical share higher.  

Lacking firm data, designers often start by listing essential systems (above) and eyeballing that they might sum to perhaps one-quarter to one-half of total load.  We therefore flag all such fractions below as [Speculation] – they illustrate typical practice but are not universally fixed.  

# Tiered load-shedding strategies  
A common strategy is to define **priority tiers** (levels 1–3) to shed loads in stages.  For example:  
- **Tier 1 (Life Safety):** Exit/emergency lighting, fire alarm, nurse-call, critical pumps – essentially anything that directly protects lives.  These are powered instantly by the inverter/UPS and battery, or by diesel gen-set for <10 s transfer.  
- **Tier 2 (Important/Operational):** Communications (network, phones), key servers, select lighting (e.g. security lights), well pumps or elevator recall.  These can tolerate a short delay (seconds) and may be powered once Tier 1 is secured. They are often fed after a brief (≤60 s) transfer.  
- **Tier 3 (Comfort/Optional):** All remaining loads like general lighting, HVAC (air conditioning, non-essential fans), kitchen equipment, etc.  These can be cut entirely during the outage. They are shed first when power is constrained.  

Each tiering step reduces load and thus extends backup runtime.  For instance, shedding Tier 3 (comfort) might cut load by half, doubling available hours.  (Exact gains depend on the load mix.)  The Philippine Electrical Code (like NFPA 110) implies such sequencing by requiring any remaining loads be shed if the generator is undersized, with a clear priority order.  In practice, one might call Tier 1 + Tier 2 the *“emergency”* or *“critical”* load served by the solar+storage system, and Tier 3 the *“non-critical”* load that is turned off.  

*(The above tier definitions and their impact are illustrative [Speculation].  Exact categories vary by site, but the key idea is that shedding each tier lowers the power draw and so stretches battery life.)*  

# Load category parameters and estimates  
The table below summarizes approximate load categories and their typical share of a college building’s electrical demand.  These numbers are meant to indicate orders of magnitude; all figures are engineering estimates ([Speculation]) based on typical building practice and the categories above.  Verified code definitions are cited where relevant (no source can quote these percentages directly).  

| **Load Category**                       | **Typical fraction of building load** | **Notes/Source**                              |
|-----------------------------------------|--------------------------------------:|-----------------------------------------------|
| Emergency lighting & exit signs         | ~1–2%                                 | Very low-power fixtures (LED exit lights); non-critical in energy terms. |
| Fire alarm and smoke detectors          | ≪1%                                  | Minimal power draw (alarm panels, detectors); must remain live. |
| Security systems (cameras, door locks)  | ~1%                                   | Tiny loads; often on UPS for safety.           |
| IT equipment (servers, routers, comms)  | ~5–10%                                | Depends on building; e.g. a small server room. |
| Office computers and peripherals        | ~5–15%                                | Fraction of plug loads kept on (e.g. critical workstations). |
| Ventilation fans (critical zones)       | ~5–10%                                | Exhaust in labs, shafts, or stairwells; fans needed for safety airflows. |
| Water pumps (fire suppression, etc.)    | ~1–3%                                 | E.g. fire pump and well pump; often diesels drive these in large buildings. |
| Air conditioning (all zones)            | ~30–50%                               | Usually the single largest load; typically **shed completely** during outage. |
| Other plug loads (kitchen, lab, etc.)   | remainder                             | E.g. refrigerators, lab equipment – mostly shed unless essential. |

All values above are approximate.  Verified references define *which categories* count as emergency or standby (e.g. lights, pumps, alarms), but not the exact percentages.  

# Worked example: 12-hour outage, 300 kWh/day building  
Consider a medium-sized building that uses 300 kWh per day (an average **12.5 kW** continuous load).  A 12-hour outage means the solar+storage system must supply \(300\times(12/24)=150\) kWh to meet full (100%) load.  

- **No load shedding (Tier 3 ON):**  All loads on; average 12.5 kW draw. 150 kWh required ⇒ battery lasts 12 h (exactly the outage duration).  
- **Tier 1+2 ON only (~50% load):** Suppose shedding Tier 3 halves demand (~6.25 kW). 12 h at 6.25 kW uses 75 kWh.  A 150 kWh battery would now last 150/6.25 = 24 h. In other words, cutting comfort loads doubles the backup duration.  
- **Tier 1 only (~20% load):** If only life-safety + essential (say 2.5 kW, 20% of full) are on, 12 h uses 30 kWh. 150 kWh battery would last 150/2.5 = 60 h.  The system would easily outlast a 12 h outage.  

This example shows how shedding non-critical tiers sharply extends runtime.  In practice one would size the battery for the desired level of reliability.  

# Key assumptions and limitations  
- These category shares and example calculations are **estimates** for illustration; actual critical-load fractions must be determined by an on-site survey or detailed electrical plan.  We label all non-sourced values above as [Speculation].  
- Building codes require **certain life-safety loads** (lighting, alarms, communications) to be backed up automatically. Other loads (HVAC, general lighting) are usually optional to back up.  
- We assumed the battery capacity was just enough for the full load for 12 h (150 kWh). In reality one might oversize for extra safety.  
- Tier definitions vary by facility and local fire/OSHA rules. Our Tier 1/2/3 breakdown is illustrative.  

**References:** Definitions and load classifications are drawn from building and electrical codes and industry guides. Estimates of load shares come from typical commercial building practice and should be confirmed by energy audits.