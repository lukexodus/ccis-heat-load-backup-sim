# Illustrations — CCIS Engineering Report

This file holds the diagram sources for the hand-assembled Google Docs version of
`CCIS-engineering-report.md`. Google Docs does not render Mermaid, so each diagram is kept
here as source and is pasted into Google Docs through a Mermaid renderer or converted to an
image first. Section references (§3, §5) point back to the report.

Sources: `docs/context/conceptual-model.md` and `docs/context/phase2-interface-contract.md`
for the system and hourly logic; the implementation (`src/ccis_sim/`) for anything the two
documents describe loosely; `docs/decisions/decision-log.md` for the decision pipeline.

---

## D1 — Overall simulation flow

**Suggested caption:** Figure D1. End-to-end simulation flow, from exogenous inputs to the
Monte Carlo sizing study and the decision analysis.
**Target section:** §3 Conceptual model.

```mermaid
flowchart TD
    A["Inputs: site, 18-room audit, weather year 2019/2016, sizing kWp/kWh, seed"] --> B["Weather and calendar: NASA POWER hourly, Feb 29 dropped, academic occupancy"]
    B --> C["Demand: non-cooling (lighting, IT, plug) + cooling (CDD, latent)"]
    B --> D["Outage schedule: Poisson arrivals, lognormal durations, typhoon GHI depression"]
    C --> E["Hourly engine: shed, dispatch PV and battery, settle bus, record"]
    D --> E
    E --> F["Annual records: grid import, curtailment, unserved Tier 1+2"]
    F --> G["Monte Carlo: 50 seeds per sizing, common random numbers"]
    G --> H["Decision analysis: AHP scoring, Pareto frontier, pre-registered rule"]
    H --> I["Recommendation and figures"]
```

---

## D2 — Hourly event order and shedding rules

**Suggested caption:** Figure D2. Order of operations inside one simulated hour, including the
load-shedding rules and the settle order.
**Target section:** §3.2 and §3.3.

```mermaid
flowchart TD
    S(["Hour t"]) --> D1["1. Compute tiered demand T1, T2, T3"]
    D1 --> D2["2. Read grid status from outage schedule"]
    D2 --> D3{"3. Grid available?"}
    D3 -->|"No (outage)"| SH["Shed Tier 3 at once"]
    SH --> SOC{"SoC at hour start below 20% of capacity?"}
    SOC -->|"Yes"| T1ONLY["Serve Tier 1 only"]
    SOC -->|"No"| T12["Serve Tier 1 + Tier 2"]
    D3 -->|"Yes"| ALL["Serve all tiers"]
    T1ONLY --> PV["4. PV output for the hour, typhoon multiplier applied"]
    T12 --> PV
    ALL --> PV
    PV --> BUS["5. Settle the bus in order: PV, then battery, then grid"]
    BUS --> CHG["Battery charges from surplus PV only; no grid charging"]
    CHG --> LOSS["6. Apply self-discharge and standby idle losses"]
    LOSS --> REC["7. Record import, curtailment, unserved energy per tier"]
    REC --> E(["Hour t+1"])
```

---

## D3 — Software architecture

**Suggested caption:** Figure D3. Package layout of `ccis_sim` and the direction of data flow.
**Target section:** §5.2.

```mermaid
flowchart TD
    CLI["cli.py"] --> INT["integration: engine, scenarios, exporters, baseline"]
    INT --> CORE["core: models, interfaces, conservation harness"]
    INT --> WX["weather: client, parser, sanitizer, disaggregator"]
    INT --> DEM["demand: equipment audit, schedule, non-cooling, cooling, mock bills"]
    INT --> SOL["solar: irradiance, array"]
    INT --> BAT["battery: dynamics, reserve"]
    INT --> OUT["outage: sampler, shedding"]
    VAL["validation: audit, plausibility, sensitivity, hypothesis"] --> INT
    DEC["decision: ahp, sizing, plots"] --> INT
```

---

## D4 — Decision pipeline

**Suggested caption:** Figure D4. From candidate grid to recommendation: Monte Carlo study,
AHP scoring, Pareto frontier, and the pre-registered selection rule.
**Target section:** §7.2.

```mermaid
flowchart TD
    G["Candidate grid: 4 PV sizes x 6 battery sizes + 0/0"] --> MC["Monte Carlo: 50 seeds, 2019 typhoon, both demand cases, common random numbers"]
    MC --> AGG["Aggregate per candidate: reliability, unserved energy, self-sufficiency, cost index"]
    AGG --> AHP["AHP scoring: weights from pairwise matrix, CR = 0.007"]
    AGG --> PAR["Pareto frontier over reliability, cost, self-sufficiency"]
    PAR --> RULE{"Pre-registered rule D-38: non-dominated, cheapest with Tier 1+2 >= 90% bottom-up and >= 80% bill-calibrated"}
    AHP --> COMP["Composite ranking, reported alongside the rule"]
    RULE --> REC["Recommendation: 200 kWp / 150 kWh"]
    COMP --> REC
    MC --> R16["2016 robustness re-run: top five sizings, 1,000 runs"]
    R16 --> REC
```

---

## Decorative image prompts

These are **decorative only** (cover or context illustrations). No technical diagram is to be
produced from an image prompt: labels and flows in D1–D4 must stay exact and are delivered as
Mermaid source above.

### I1 — Cover illustration

> A single-storey-fronted two-storey university college building in a hot, humid Philippine
> provincial setting, seen from the front at midday; a flat roof covered with dark-blue solar
> panels; a small battery cabinet on the ground beside the entrance; palm trees and a
> tropical sky with cumulus clouds; warm natural light; wide landscape composition with empty
> sky space at the top. Style: clean editorial illustration, muted realistic palette. No text,
> no numbers, no logos, no institutional branding, no identifiable real building.

### I2 — Context illustration

> Cutaway-style illustration of a campus building at night during a storm: rain on the
> windows, the surrounding street lights dark, but warm light glowing from a few interior
> rooms and corridor exit signs; solar panels on the roof; a compact battery cabinet inside a
> utility closet. Style: clean editorial illustration, muted realistic palette. No text, no
> numbers, no logos, no institutional branding.
