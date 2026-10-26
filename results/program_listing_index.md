# Program Listing Index (DOC-FIX-001 Part D)

| Path | Lines | Purpose |
| :--- | ---: | :--- |
| `src/ccis_sim/__init__.py` | 8 | CCIS Heat, Load and Backup Power Simulation package. |
| `src/ccis_sim/battery/__init__.py` | 6 | Battery energy storage system (BESS) dispatch dynamics, state-of-charge, and limits. |
| `src/ccis_sim/battery/dynamics.py` | 201 | Battery dispatch dynamics, State-of-Charge tracking, and physical limits. |
| `src/ccis_sim/battery/reserve.py` | 194 | Battery outage reserve policy, State-of-Charge protection floors, and idle losses. |
| `src/ccis_sim/cli.py` | 198 | Command-line interface (CLI) for the CCIS Heat, Load and Backup Power Simulation. |
| `src/ccis_sim/core/__init__.py` | 60 | Core domain models, interface protocols, and conservation invariants. |
| `src/ccis_sim/core/interfaces.py` | 229 | Shared interface types and data contracts for Phase 2 parallel sub-models. |
| `src/ccis_sim/core/models.py` | 304 | Canonical immutable domain models and interface contracts for CCIS simulation. |
| `src/ccis_sim/core/verification.py` | 919 | Verification and validation harness for CCIS energy simulation. |
| `src/ccis_sim/core/weather.py` | 27 | Weather interface re-exports for shared core infrastructure. |
| `src/ccis_sim/decision/__init__.py` | 55 | Multi-criteria decision analysis (AHP), Pareto trade-off optimization, and figure visualization. |
| `src/ccis_sim/decision/ahp.py` | 283 | Analytic Hierarchy Process (AHP) multi-criteria weighting engine (DEC-001). |
| `src/ccis_sim/decision/plots.py` | 368 | Publication-quality visualization and figure generation suite (DEC-003.1 / DEC-003.2). |
| `src/ccis_sim/decision/sizing.py` | 392 | Pareto trade-off optimization, candidate evaluation, and sizing recommendation engine (DEC-002). |
| `src/ccis_sim/demand/__init__.py` | 34 | Building electricity demand models: equipment inventory schedules and cooling load. |
| `src/ccis_sim/demand/cooling.py` | 134 | Temperature and humidity sensitive AC cooling demand model. |
| `src/ccis_sim/demand/equipment.py` | 250 | Equipment audit domain model and inventory parser for CCIS simulation. |
| `src/ccis_sim/demand/mock_bills.py` | 299 | Synthetic monthly electricity bill generator calibrated against CCIS equipment audit. |
| `src/ccis_sim/demand/non_cooling.py` | 105 | Diurnal non-cooling electrical demand model for CCIS facility. |
| `src/ccis_sim/demand/schedule.py` | 332 | Academic calendar and building occupancy schedule engine. |
| `src/ccis_sim/integration/__init__.py` | 54 | Integrated time-step simulation engine, CLI driver, and Monte Carlo scenario runners. |
| `src/ccis_sim/integration/baseline.py` | 297 | Baseline grid-only continuous simulation engine (CORE-005 Phase 1 Exit Gate). |
| `src/ccis_sim/integration/engine.py` | 490 | Integrated time-step simulation engine for CCIS microgrid. |
| `src/ccis_sim/integration/exporters.py` | 220 | Data exporters for CCIS microgrid simulation outputs. |
| `src/ccis_sim/integration/scenarios.py` | 342 | Scenario Grid and Monte Carlo Simulation Runner (INT-002). |
| `src/ccis_sim/outage/__init__.py` | 53 | Stochastic utility outage generation (Poisson/Lognormal) and priority load shedding. |
| `src/ccis_sim/outage/sampler.py` | 510 | Stochastic utility outage generation and typhoon solar depression sampler. |
| `src/ccis_sim/outage/shedding.py` | 402 | Priority-based tiered load shedding controller and unserved energy tracker (OUT-002). |
| `src/ccis_sim/solar/__init__.py` | 47 | Solar photovoltaic output models: irradiance geometry, NOCT thermal derating, array sizing, and BOS losses. |
| `src/ccis_sim/solar/array.py` | 165 | Solar PV array capacity scaling, inverter clipping, and balance-of-system losses. |
| `src/ccis_sim/solar/irradiance.py` | 429 | Solar irradiance geometry and NOCT cell temperature thermal derating model. |
| `src/ccis_sim/validation/__init__.py` | 35 | Validation, verification, and plausibility auditing package for CCIS microgrid simulation. |
| `src/ccis_sim/validation/audit.py` | 196 | Verification and physical invariant audit harness for CCIS microgrid simulation (INT-003). |
| `src/ccis_sim/validation/hypothesis.py` | 340 | Paired and unpaired hypothesis tests over the INT-002 scenario grid (DOC-FIX-001 Part B). |
| `src/ccis_sim/validation/plausibility.py` | 269 | Plausibility evaluation and benchmark reconciliation module (INT-003). |
| `src/ccis_sim/validation/sensitivity.py` | 222 | One-at-a-time (OAT) parameter sensitivity analysis harness (INT-003). |
| `src/ccis_sim/weather/__init__.py` | 26 | Weather ingestion, parsing, sanitization, and disaggregation pipeline. |
| `src/ccis_sim/weather/client.py` | 197 | NASA POWER REST API client for fetching meteorological time series. |
| `src/ccis_sim/weather/disaggregator.py` | 209 | Daily-to-hourly weather disaggregation engine. |
| `src/ccis_sim/weather/loader.py` | 78 | Loader utility for cached offline weather CSV fixtures. |
| `src/ccis_sim/weather/parser.py` | 126 | Parser for NASA POWER meteorological JSON and CSV payloads. |
| `src/ccis_sim/weather/sanitizer.py` | 190 | Weather data sanitizer for missing-value filtering, timezone alignment, and validation. |
| `tests/__init__.py` | 1 | Test suite for ccis-sim. |
| `tests/test_baseline_smoke.py` | 235 | Unit and integration tests for baseline grid-only simulation (CORE-005 Phase 1 Exit Gate). |
| `tests/test_battery_dynamics.py` | 367 | Unit tests and property-based verification for BAT-001 Battery Dispatch Dynamics. |
| `tests/test_battery_reserve.py` | 333 | Unit tests and verification for BAT-002 Battery Outage Reserve & State-of-Charge Constraints. |
| `tests/test_conservation_checker.py` | 584 | Unit tests for verification harness and invariant checker (CORE-004). |
| `tests/test_cooling_response.py` | 295 | Unit tests for temperature and humidity sensitive AC cooling demand model. |
| `tests/test_core_models.py` | 334 | Unit test suite for core canonical domain models and interface contracts. |
| `tests/test_decision.py` | 251 | Unit tests for decision analysis module (DEC-001, DEC-002, and DEC-003 figures). |
| `tests/test_demand_schedule.py` | 226 | Unit tests for academic calendar and building occupancy schedule engine. |
| `tests/test_engine.py` | 288 | Unit and integration tests for CCIS simulation engine and CLI (INT-001). |
| `tests/test_equipment_audit.py` | 187 | Unit and integration test suite for CCIS equipment audit model and fixtures. |
| `tests/test_hypothesis.py` | 187 | Unit tests for validation.hypothesis (DOC-FIX-001 Part B). |
| `tests/test_interfaces.py` | 185 | Unit tests for Phase 2 interface types and data contracts per [D-26]. |
| `tests/test_load_shedding.py` | 455 | Unit and property tests for priority-based tiered load shedding controller (OUT-002). |
| `tests/test_mock_bills.py` | 143 | Unit and integration test suite for synthetic mock electricity bills and EUI validation. |
| `tests/test_non_cooling_demand.py` | 215 | Unit tests for diurnal non-cooling electrical demand model. |
| `tests/test_outage_sampler.py` | 411 | Unit and statistical integration tests for stochastic outage sampler (OUT-001). |
| `tests/test_scenarios.py` | 166 | Unit and regression tests for INT-002 Scenario Grid and Monte Carlo runner. |
| `tests/test_smoke.py` | 53 | Smoke test suite verifying basic environment and package layout. |
| `tests/test_solar_array.py` | 177 | Unit and integration test suite for solar array sizing and inverter clipping. |
| `tests/test_solar_irradiance.py` | 204 | Unit and integration test suite for solar irradiance and NOCT thermal derating. |
| `tests/test_validation.py` | 286 | Comprehensive test suite for simulation verification, plausibility, and sensitivity (INT-003). |
| `tests/test_weather_ingest.py` | 424 | Unit and integration test suite for NASA POWER weather ingestion pipeline. |
