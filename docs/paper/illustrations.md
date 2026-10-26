# Illustrations — CCIS Engineering Report

This file holds the diagram sources for the hand-assembled Google Docs version of
`CCIS-engineering-report.md`. Google Docs does not render Mermaid, so each diagram is kept
here as source and is pasted into Google Docs through a Mermaid renderer or converted to an
image first. Section references (§3, §5) point back to the report.

Sources: `docs/context/conceptual-model.md` and `docs/context/phase2-interface-contract.md`
for the system and hourly logic; the implementation (`src/ccis_sim/`) for anything the two
documents describe loosely; `docs/decisions/decision-log.md` for the decision pipeline.

**Revision note (2026-10-26).** D1–D4 were parsed and rendered with `mmdc` at review, which
also checked the syntax that could not be checked when the file was first written. D1 and D3
are unchanged. D2 and D4 were corrected: D4 now shows the [D-38] fallback branch, because no
sizing reaches 80% under bill-calibrated demand; D2 gains the battery floors of [D-32] and the
reverse-priority shortfall allocation of [D-34]. D2's SoC test is at the start of the hour, as
the engine's own docstring states (`src/ccis_sim/outage/shedding.py`, `shed_for_hour`).

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
    S(["Hour t"]) --> H1["1. Compute tiered demand: Tier 1, Tier 2, Tier 3"]
    H1 --> H2["2. Read grid status from outage schedule"]
    H2 --> G{"3. Grid available?"}
    G -->|"Yes"| ALL["Serve all tiers. Battery floor = 30% of capacity (10% cell floor + 20% emergency reserve held back)"]
    G -->|"No: outage"| SH["Shed Tier 3 at once. Emergency reserve released: battery floor = 10% of capacity"]
    SH --> Q{"Battery SoC at the start of the hour below 20% of capacity?"}
    Q -->|"Yes"| T1["Serve Tier 1 only (Tier 2 shed)"]
    Q -->|"No"| T12["Serve Tier 1 + Tier 2"]
    ALL --> PV["4. PV output for the hour, typhoon irradiance multiplier applied"]
    T1 --> PV
    T12 --> PV
    PV --> BUS["5. Settle the bus: PV first, then battery, then grid. Battery charges from surplus PV only"]
    BUS --> SF{"Battery cannot deliver the served demand during an outage?"}
    SF -->|"Yes"| RP["Shortfall is unserved, taken in reverse priority: Tier 3, then Tier 2, then Tier 1"]
    SF -->|"No"| LOSS
    RP --> LOSS["6. Apply self-discharge and standby idle losses"]
    LOSS --> REC["7. Record grid import, curtailment, unserved energy per tier"]
    REC --> N(["Hour t+1"])
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
    G["Candidate grid: PV 50, 100, 150, 200 kWp x battery 0, 25, 50, 100, 150, 200 kWh, plus 0/0 reference"] --> MC["Monte Carlo: 50 seeds, 2019 typhoon, both demand cases, common random numbers"]
    MC --> AGG["Aggregate per sizing: reliability, unserved energy, self-sufficiency, curtailment, cost index"]
    AGG --> AHP["AHP composite score: 4 criteria, consistency ratio 0.007"]
    AGG --> PAR["Pareto frontier over reliability, cost, self-sufficiency (per demand case)"]
    PAR --> RULE{"Pre-registered rule D-38: cheapest non-dominated sizing with Tier 1+2 hours served at least 90% (bottom-up) AND at least 80% (bill-calibrated)?"}
    RULE -->|"Some sizing qualifies"| REC1["Recommend it"]
    RULE -->|"None qualifies (actual outcome)"| FB["Report the best achievable sizing under each demand case, with the trade-off"]
    FB --> R1["Bottom-up: cheapest sizing at 90% or more = 200 kWp / 150 kWh (recommended)"]
    FB --> R2["Bill-calibrated: best achievable = 200 kWp / 200 kWh at 73.8%"]
    AHP --> CMP["AHP ranking reported alongside, not used to select"]
    MC --> R16["2016 weather robustness re-run of the top-5 AHP sizings"]
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
