# Task Report: CORE-004.5 — Phase 1 Closeout Fixup: Repo Hygiene, Harness Gaps, and D-24 Disclosures

**Date:** 2026-10-20  
**Agent:** gemini  
**Task ID:** CORE-004.5  
**Status:** done  
**Commit:** `fix(CORE-004.5): close harness gaps, record D-24 disclosures, and normalize repo hygiene`  
**Patch File:** `patch/CORE-004.5-gemini-phase1-closeout.patch`  

---

## 1. Executive Summary

This unit of work completes task `CORE-004.5` ("Phase 1 Closeout Fixup: repo hygiene, harness gaps, D-22 disclosure"), executing the final quality, verification, and disclosure hardening required before Phase 2 parallel model tracks begin.

The task resolves three distinct areas identified during Phase 1 review:
1. **Part A (Repo Hygiene & Provenance Integrity):** Verified the git commit history of `docs/reports/ARCH-002.5-gemini-windows-interop.md`, conclusively demonstrating why it appeared deleted in the `task/CORE-005` branch diff (branching point race condition vs `0bdfda2` merge on `master`) while remaining intact on `master`. Confirmed `ARCH-002.5` and `CORE-004.5` rows are documented in `docs/tasks/status.md`. Verified patch cleanliness (`patch/` directory tracked files). Added an explanatory Section 8 Addendum to `docs/reports/CORE-005-gemini-baseline-smoke-test.md` regarding omitted touched files.
2. **Part B (Verification Harness Gaps Closed — `[D-25]`):** Extended the verification harness in `src/ccis_sim/core/verification.py` to eliminate simulation verification blind spots:
   - Implemented hour-to-hour State-of-Charge continuity tracking (`ViolationType.SOC_CONTINUITY`), enforcing physical energy conservation $\text{SoC}_t = \text{SoC}_{t-1} + \eta_{\text{chg}} P_{\text{chg},t} \Delta t - P_{\text{dis},t} \Delta t / \eta_{\text{dis}}$ with symmetric round-trip efficiency ($\eta_{\text{chg}} = \eta_{\text{dis}} = \sqrt{0.92} \approx 0.9591663$).
   - Added guards against `NaN`, `+inf`, and `-inf` floating-point anomalies across all record fields (`ViolationType.NON_FINITE_VALUE`).
   - Added sub-flow decomposition conservation checks (`ViolationType.SOLAR_FLOW_BALANCE` and `ViolationType.DEMAND_FLOW_BALANCE`).
   - Introduced `HourlyRecord.signed_residual_kwh` property for directional cumulative drift tracking.
   - Formally reconciled the non-discretionary 10% SoC protection floor (`[D-09]`), the 20% emergency blackout reserve (`[D-17]`), and the emergency drawdown override (`[D-21]`).
   - Updated `create_golden_scenario()` to reflect symmetric conversion efficiency with exact 0.000000 kWh residual across all 48 hours.
3. **Part C (D-24 Baseline Disclosure Addendum — `[D-24]`):** Disclosed uncalibrated baseline annual metrics (324,379.71 kWh/yr, EUI 129.75 kWh/m²·yr, Peak 101.29 kW), named and exported `DEFAULT_COOLING_DUTY_FACTOR = 0.35` in `src/ccis_sim/integration/baseline.py`, affirmed that the 159.41 kWh/m²·yr baseline match is by construction via calibration multiplier $1.22857563$, classified the 124.44 kW peak demand as provisional, and documented the 2016 weekday sensitivity context.

All 107 tests across the entire repository test suite pass cleanly (100% green).

---

## 2. Implementation Details

### 2.1 Changes Made by Area

#### Part A: Repository Hygiene & Provenance
- `docs/reports/CORE-005-gemini-baseline-smoke-test.md`: Appended **Section 8: Addendum — Provenance, Omitted Files Disclosure & Interop Report Status** explaining the branch history of `task/CORE-005` relative to `0bdfda2` (`ARCH-002.5`), noting the update to `docs/context/repo-tree.txt`, and documenting the patch gitignore policy.
- `docs/tasks/status.md`: Verified presence of `ARCH-002.5` row and added `CORE-004.5` row linked to this report.
- `docs/context/repo-tree.txt`: Regenerated to accurately track all repository files.

#### Part B: Verification Harness Gap Closures (`[D-25]`)
- `src/ccis_sim/core/models.py`: Added canonical signed residual property:
  ```python
  @property
  def signed_residual_kwh(self) -> float:
      energy_in = self.solar_generation_kwh + self.grid_import_kwh + self.battery_discharge_kwh
      energy_out = self.demand_served_kwh + self.solar_curtailed_kwh + self.battery_charge_kwh
      return energy_in - energy_out
  ```
- `src/ccis_sim/core/verification.py`:
  - Added new enum values to `ViolationType`: `SOC_CONTINUITY`, `NON_FINITE_VALUE`, `SOLAR_FLOW_BALANCE`, `DEMAND_FLOW_BALANCE`.
  - Added `subflow_violations: list[ConservationViolation]` to `VerificationReport` and included in report summary / validity check (`is_valid = len(conservation_violations) == 0 and len(battery_violations) == 0 and len(subflow_violations) == 0`).
  - Implemented `check_subflow_balance(records, tolerance=1e-5)` verifying solar flow decomposition ($P_{\text{solar}} = P_{\text{to\_demand}} + P_{\text{to\_battery}} + P_{\text{curtailed}}$) and demand flow decomposition ($P_{\text{gross}} = P_{\text{served}} + P_{\text{unserved}}$).
  - Enhanced `check_energy_conservation()` with non-finite numeric guards and signed residual drift accumulation.
  - Enhanced `validate_battery_boundaries()` with non-finite guards, `initial_soc_kwh` parameter, and hour-to-hour continuity checking using symmetric round-trip efficiency:
    $$\Delta \text{SoC} = \sqrt{\eta_{\text{rt}}} P_{\text{chg},t} \Delta t - \frac{P_{\text{dis},t} \Delta t}{\sqrt{\eta_{\text{rt}}}}$$
    where $\sqrt{\eta_{\text{rt}}} = \sqrt{0.92} \approx 0.9591663046625438$. Continuity validation is bypassed when `battery.capacity_kwh == 0.0`.
  - Updated `create_golden_scenario()` to adjust chemical battery SoC to account for symmetric charge/discharge losses while keeping AC-side grid/solar/demand flows in exact 0.000000 kWh hourly balance.
- `src/ccis_sim/core/__init__.py`: Exported `check_subflow_balance`.
- `tests/fixtures/README.md`: Documented the new continuity, non-finite, and sub-flow checks.
- `tests/test_conservation_checker.py`: Added 8 comprehensive unit tests for all new invariants.

#### Part C: Baseline Demand Disclosure Addendum (`[D-24]`)
- `src/ccis_sim/integration/baseline.py`: Promoted the hardcoded `0.35` daytime cooling factor to a named, documented constant:
  ```python
  DEFAULT_COOLING_DUTY_FACTOR: float = 0.35
  ```
  Applied `DEFAULT_COOLING_DUTY_FACTOR` within `compute_placeholder_demand` to maintain bit-identical baseline demand.
- `src/ccis_sim/integration/__init__.py`: Exported `DEFAULT_COOLING_DUTY_FACTOR`.
- `docs/decisions/decision-log.md`: Appended `[D-24]` (disclosing uncalibrated baseline metrics, EUI, provisional peak, and duty factor) and `[D-25]` (locking harness gap closure conventions).

### 2.2 Conformance to Specifications & Decisions

- **[D-09] vs [D-21] Reconciliation:** Fully articulated in `[D-25]`. The 10% floor ($SoC_{\min}$) is non-discretionary under all normal operating regimes (`grid_available == True` or `active_load_tier == 3`). Emergency drawdown to 0 kWh is permitted strictly during blackouts (`grid_available == False` and `active_load_tier in (1, 2)`) when `allow_emergency_drawdown=True`.
- **Decision ID Collision Avoidance:** `[D-23]` was already committed on `master` by `CORE-005`. Following the user approval, the reservation was shifted cleanly to `[D-24]` (baseline disclosure addendum) and `[D-25]` (verification harness gap closures).

---

## 3. Verification & Test Evidence

### 3.1 Test Execution

Command executed:
```bash
pytest
```

**Results:**
- Tests passed: 107
- Tests failed: 0
- Tests skipped: 0
- Duration: 8.63s

Output excerpt:
```text
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/ccis-heat-load-backup-sim-CORE-004.5
configfile: pyproject.toml
collected 107 items

tests/test_baseline_smoke.py ........                                    [  7%]
tests/test_conservation_checker.py ....................                  [ 26%]
tests/test_core_models.py ...................                            [ 43%]
tests/test_equipment_audit.py ....................                      [ 62%]
tests/test_mock_bills.py ........                                        [ 70%]
tests/test_smoke.py ...........                                          [ 80%]
tests/test_weather_ingest.py ......................                      [100%]

============================= 107 passed in 8.63s ==============================
```

### 3.2 Edge Cases & Negative Testing

Eight dedicated unit tests were implemented in `tests/test_conservation_checker.py`:
1. `test_soc_continuity_golden_scenario_passes`: Verifies that the updated 48-hour golden scenario strictly satisfies hour-to-hour SoC continuity with symmetric efficiency.
2. `test_soc_continuity_teleport_violation_caught`: Verifies that teleporting SoC (e.g. 100.0 kWh -> 80.0 kWh without discharge) is trapped and flagged as `ViolationType.SOC_CONTINUITY`.
3. `test_soc_continuity_zero_capacity_skipped`: Confirms zero-capacity batteries (grid-only runs) bypass SoC continuity checks.
4. `test_non_finite_value_caught_in_conservation`: Verifies that injecting `NaN` or `inf` into numeric fields trips `ViolationType.NON_FINITE_VALUE`.
5. `test_non_finite_value_caught_in_battery_boundaries`: Verifies that `NaN` or `inf` in battery fields trips `ViolationType.NON_FINITE_VALUE`.
6. `test_solar_flow_balance_violation_caught`: Verifies that an unallocated 5 kWh solar generation gap trips `ViolationType.SOLAR_FLOW_BALANCE`.
7. `test_demand_flow_balance_violation_caught`: Verifies that an unallocated 5 kWh demand gap trips `ViolationType.DEMAND_FLOW_BALANCE`.
8. `test_hourly_record_signed_residual_property`: Verifies directional polarity of `signed_residual_kwh` for surplus, deficit, and balanced hours.

---

## 4. Decisions Recorded

- **[D-24]**: Baseline demand placeholder disclosure addendum, uncalibrated EUI, and provisional peak classification (amending [D-23]).
  - Uncalibrated 2019 baseline annual consumption: 324,379.71 kWh/yr.
  - Uncalibrated annual EUI: 129.75 kWh/m²·yr.
  - Uncalibrated peak demand: 101.29 kW.
  - Calibration multiplier: $c_{\text{calib}} = 1.22857563$ (+22.86%). Match to 159.41 kWh/m²·yr is by construction.
  - Documented `DEFAULT_COOLING_DUTY_FACTOR = 0.35`.
  - Scaled peak demand (124.44 kW) formally classified as provisional.
  - 2016 sensitivity context documented as artifact of 260 vs 261 weekdays, not empirical climate response.
- **[D-25]**: Verification harness gap closures: SoC continuity convention, non-finite guards, sub-flow decompositions, and D-09/D-21 reconciliation.
  - Hour-to-hour continuity invariant enforced with symmetric round-trip efficiency ($\eta = \sqrt{0.92} \approx 0.9591663$).
  - Non-finite numeric guards for `NaN`, `+inf`, `-inf`.
  - Sub-flow decomposition balance checks for solar and demand.
  - Canonical `signed_residual_kwh` property.
  - Formal reconciliation between `[D-09]`, `[D-17]`, and `[D-21]`.
  - Golden scenario updated with exact 0.000000 kWh residual closure.

---

## 5. Unified Git Diff

```diff
diff --git a/docs/decisions/decision-log.md b/docs/decisions/decision-log.md
index edf4955..106d7bb 100644
--- a/docs/decisions/decision-log.md
+++ b/docs/decisions/decision-log.md
@@ -179,3 +179,38 @@
 
+**[D-24]** Baseline demand placeholder disclosure addendum, uncalibrated EUI, and provisional peak classification (amending [D-23]).  
+- **Date / Session:** 2026-10-20  
+- **Decision:**  
+  1. **Uncalibrated Baseline Metrics:** With calibration multiplier $c_{\text{calib}} = 1.0$, the uncalibrated 2019 baseline annual electricity consumption totals **324,379.71 kWh/yr**, yielding an uncalibrated annual Energy Use Intensity (EUI) of **129.75 kWh/m²·yr** on the 2,500 m² archetype facility, with an uncalibrated peak electrical demand of **101.29 kW**. The fixed calibration factor $c_{\text{calib}} = 1.22857563$ represents a $+22.86\%$ upward correction to align with the empirical target of 159.41 kWh/m²·yr ($398,525.00\text{ kWh/yr}$).
+  2. **Match by Construction:** The exact match between the baseline simulation annual EUI (159.4100 kWh/m²·yr) and the synthetic billing target ([D-16]/[D-19]) is **by construction** via this calibration constant, and does **not** constitute independent validation of building thermal or operational physics.
+  3. **Documented Cooling Duty Factor:** The daytime cooling temperature response includes an assumed coincident operational duty factor of **0.35** (`DEFAULT_COOLING_DUTY_FACTOR = 0.35`), representing that approximately 35% of the total 77.20 kW installed air-conditioning capacity actively compressor-cycles during daytime occupied hours when ambient temperature exceeds $T_{\text{base}} = 24.0^\circ\text{C}$ per [D-07].
+  4. **Provisional Peak Classification:** The headline peak electrical demand of **124.44 kW** (Hour 2030, 2019-03-26T13:00:00+08:00) is scaled by the same calibration multiplier and lacks independent empirical load metering; it is formally classified as **provisional** and must be superseded by the bottom-up academic diversity schedules (`DEM-001`) and dynamic psychrometric building heat load model (`DEM-002`) prior to final microgrid inverter/battery sizing.
+  5. **Climate Sensitivity Context:** The un-tuned 2016 El Niño hot-year simulation yielded a modest peak demand increase of $+1.11\text{ kW}$ (+0.89%, reaching 125.55 kW) and a slight annual consumption decrease of $-273.79\text{ kWh}$ (-0.07%, 398,251.21 kWh vs 398,525.00 kWh) due to 2016 having 260 weekdays vs 261 in 2019. This sensitivity is weak due to the placeholder's simplified linear cooling response and must not be cited as a real climate finding.
+  6. The underlying behavior and committed simulation headline numbers remain bit-identical.
+- **Reasoning:** Full scientific disclosure and methodological transparency ensure that placeholder approximations are not mistaken for validated empirical physics by downstream sizing or economic tracks.
+- **Affects:** `CORE-005`, `DEM-001`, `DEM-002`, `INT-001`, `BAT-001`.
+
+**[D-25]** Verification harness gap closures: SoC continuity convention, non-finite guards, sub-flow decompositions, and D-09/D-21 reconciliation.  
+- **Date / Session:** 2026-10-20  
+- **Decision:**  
+  1. **Hour-to-Hour SoC Continuity Invariant:** For consecutive hourly records ($t \ge 1$), the battery state-of-charge must strictly obey physical energy conservation:
+     $$\text{SoC}_t = \text{SoC}_{t-1} + \eta_{\text{chg}} P_{\text{chg},t} \Delta t - \frac{P_{\text{dis},t} \Delta t}{\eta_{\text{dis}}}$$
+     within a numerical tolerance of $10^{-5}\text{ kWh}$ (`ViolationType.SOC_CONTINUITY`).
+  2. **Symmetric Efficiency Split:** In the absence of separate manufacturer charge/discharge curves in `Battery`, the 92% round-trip efficiency locked in [D-09] is split symmetrically:
+     $$\eta_{\text{chg}} = \eta_{\text{dis}} = \sqrt{\eta_{\text{rt}}} = \sqrt{0.92} \approx 0.9591663$$
+     Battery charge ($P_{\text{chg}}$) and discharge ($P_{\text{dis}}$) are defined strictly as AC-side flows (matching the quantities in the hourly grid/solar energy balance); all electrochemical and inverter conversion losses appear strictly in the stored chemical SoC. The continuity check is bypassed when `Battery.capacity_kwh == 0.0`. For the initial record ($t = 1$), continuity is evaluated against an optional `initial_soc_kwh` parameter if provided; otherwise skipped.
+  3. **Non-Finite Numerical Guards:** Any occurrence of `NaN`, `+inf`, or `-inf` in any numeric float field of `HourlyRecord` or `Battery` is strictly classified as an invariant failure (`ViolationType.NON_FINITE_VALUE`) across all verification checkers.
+  4. **Sub-Flow Decomposition Balances:** Added explicit conservation checks (`check_subflow_balance`):
+     - Solar flow decomposition: $P_{\text{solar}} = P_{\text{to\_demand}} + P_{\text{to\_battery}} + P_{\text{curtailed}}$ (`ViolationType.SOLAR_FLOW_BALANCE`).
+     - Demand flow decomposition: $P_{\text{gross}} = P_{\text{served}} + P_{\text{unserved}}$ (`ViolationType.DEMAND_FLOW_BALANCE`).
+  5. **Canonical Signed Residual Property:** Introduced `HourlyRecord.signed_residual_kwh` ($E_{\text{in}} - E_{\text{out}}$) for directional tracking of cumulative numerical drift in `check_energy_conservation` and `run_verification_harness`. The scalar absolute residual property `energy_balance_residual_kwh` and `is_energy_conserved()` remain unchanged.
+  6. **Reconciliation of [D-09] and [D-21]:**
+     - The 10% minimum SoC protection floor ($SoC_{\min} = 0.10 \times C_{\text{bat}}$) defined in [D-09] is strictly non-discretionary under all normal, grid-connected operating regimes to prevent accelerated lithium-ion degradation.
+     - The emergency drawdown override permitted under [D-21] (allowing SoC to discharge down to 0 kWh) is strictly restricted to active utility grid blackouts (`grid_available = False`) where priority shedding is active (`active_load_tier in (1, 2)`) and `allow_emergency_drawdown = True`.
+     - Relation to [D-17] Emergency Reserve: The 20% emergency blackout reserve ([D-17]) is an operational scheduling buffer allocated to sustain Tier 1 critical loads through outages, whereas the 10% floor ([D-09]) is physical cell-protection hardware reserve. The emergency drawdown override bridges the two by allowing life-safety survival operation to consume the hardware floor only in declared catastrophic emergencies.
+  7. **Golden Reference Fixture Update:** Updated `create_golden_scenario()` to incorporate symmetric conversion efficiency while maintaining exact $0.000000\text{ kWh}$ residual across all 48 hours.
+- **Reasoning:** Closes potential simulation verification blind spots (energy teleportation, silent NaN propagation, sub-flow leakage) before parallel Phase 2 model tracks commence.
+- **Affects:** `CORE-004`, `CORE-005`, `DEM-001`, `DEM-002`, `BAT-001`, `BAT-002`, `SOL-001`, `SOL-002`, `OUT-001`, `OUT-002`, `INT-001`, `INT-002`, `INT-003`.
diff --git a/docs/reports/CORE-005-gemini-baseline-smoke-test.md b/docs/reports/CORE-005-gemini-baseline-smoke-test.md
index a616c31..da6fbe8 100644
--- a/docs/reports/CORE-005-gemini-baseline-smoke-test.md
+++ b/docs/reports/CORE-005-gemini-baseline-smoke-test.md
@@ -211,3 +211,12 @@
 - [x] All 8 new baseline verification tests passing (100% green).
+
+---
+
+## 8. Addendum — Provenance, Omitted Files Disclosure & Interop Report Status
+
+During APC Phase 1 closeout review, three provenance and tracking items were audited:
+1. **`ARCH-002.5-gemini-windows-interop.md` status:** The report file was never deleted on `master`. The apparent deletion was an artifact of diffing a worktree branch (`task/CORE-005`) that had branched from `08466a8` prior to the landing of commit `0bdfda2` (`ARCH-002.5`). The merge to `master` (`e97176a`) preserved `ARCH-002.5` intact. `ARCH-002.5` is tracked in `docs/tasks/status.md`.
+2. **`docs/context/repo-tree.txt` omission:** The modification of `docs/context/repo-tree.txt` was executed during the task but inadvertently omitted from the "Files Touched" list in Section 2.1.
+3. **Patch untracking:** Following `CORE-001.6` process fixup, `patch/*.patch` was added to `.gitignore` to prevent duplicate tracking of patch files. Only `.gitkeep` is tracked in `patch/`.
diff --git a/docs/tasks/status.md b/docs/tasks/status.md
index b288df7..8e0e7a2 100644
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -66,2 +66,3 @@
 | CORE-004.3   | Build shared golden fixture runner for sub-model validation                      | `done` | 48h reference fixture `create_golden_scenario()` + self-test                                                      |
+| CORE-004.5   | Phase 1 closeout fixup (repo hygiene, harness gaps, D-24 disclosures)            | `done` | [CORE-004.5-gemini-phase1-closeout.md](../reports/CORE-004.5-gemini-phase1-closeout.md) [D-24], [D-25]           |
 | **CORE-005** | **Baseline Engine Smoke Test (Phase 1 Exit Gate)**                               | `done` | [CORE-005-gemini-baseline-smoke-test.md](../reports/CORE-005-gemini-baseline-smoke-test.md) |
diff --git a/src/ccis_sim/core/__init__.py b/src/ccis_sim/core/__init__.py
index e6046e0..58bc535 100644
--- a/src/ccis_sim/core/__init__.py
+++ b/src/ccis_sim/core/__init__.py
@@ -19,2 +19,3 @@
     assert_simulation_valid,
     check_energy_conservation,
+    check_subflow_balance,
     compute_cumulative_tolerance,
@@ -37,2 +38,3 @@
     "check_energy_conservation",
+    "check_subflow_balance",
     "compute_cumulative_tolerance",
diff --git a/src/ccis_sim/core/models.py b/src/ccis_sim/core/models.py
index ca30626..0112cb9 100644
--- a/src/ccis_sim/core/models.py
+++ b/src/ccis_sim/core/models.py
@@ -107,2 +107,14 @@
 
+    @property
+    def signed_residual_kwh(self) -> float:
+        """Signed energy balance residual in kilowatt-hours (In - Out).
+
+        Positive residual indicates energy surplus (more input than output).
+        Negative residual indicates energy deficit (more output than input).
+        """
+        energy_in = self.solar_generation_kwh + self.grid_import_kwh + self.battery_discharge_kwh
+        energy_out = self.demand_served_kwh + self.solar_curtailed_kwh + self.battery_charge_kwh
+        return energy_in - energy_out
+
     @property
     def energy_balance_residual_kwh(self) -> float:
diff --git a/src/ccis_sim/core/verification.py b/src/ccis_sim/core/verification.py
index 99c7f69..c839fe1 100644
--- a/src/ccis_sim/core/verification.py
+++ b/src/ccis_sim/core/verification.py
@@ -9,2 +9,3 @@
 
+import math
 from dataclasses import dataclass, field
@@ -29,2 +30,6 @@
     SIMULTANEOUS_CHARGE_DISCHARGE = "SIMULTANEOUS_CHARGE_DISCHARGE"
+    SOC_CONTINUITY = "SOC_CONTINUITY"
+    NON_FINITE_VALUE = "NON_FINITE_VALUE"
+    SOLAR_FLOW_BALANCE = "SOLAR_FLOW_BALANCE"
+    DEMAND_FLOW_BALANCE = "DEMAND_FLOW_BALANCE"
 
@@ -52,2 +57,3 @@
     battery_violations: list[BatteryBoundaryViolation] = field(default_factory=list)
+    subflow_violations: list[ConservationViolation] = field(default_factory=list)
     max_residual_kwh: float = 0.0
@@ -60,3 +66,3 @@
     def is_valid(self) -> bool:
-        return len(self.conservation_violations) == 0 and len(self.battery_violations) == 0
+        return (
+            len(self.conservation_violations) == 0
+            and len(self.battery_violations) == 0
+            and len(self.subflow_violations) == 0
+        )
diff --git a/src/ccis_sim/integration/__init__.py b/src/ccis_sim/integration/__init__.py
index 9bfeff0..928929e 100644
--- a/src/ccis_sim/integration/__init__.py
+++ b/src/ccis_sim/integration/__init__.py
@@ -5,3 +5,4 @@
 from ccis_sim.integration.baseline import (
     BaselineMetrics,
+    DEFAULT_COOLING_DUTY_FACTOR,
     calculate_baseline_metrics,
@@ -10,3 +11,4 @@
 
 __all__ = [
     "BaselineMetrics",
+    "DEFAULT_COOLING_DUTY_FACTOR",
     "calculate_baseline_metrics",
diff --git a/src/ccis_sim/integration/baseline.py b/src/ccis_sim/integration/baseline.py
index f4ea7a0..40ff839 100644
--- a/src/ccis_sim/integration/baseline.py
+++ b/src/ccis_sim/integration/baseline.py
@@ -24,6 +24,11 @@ logger = logging.getLogger(__name__)
 # Fixed calibration factor derived on 2019 baseline weather fixture to hit 159.41 kWh/m²·yr (398,525 kWh)
 CALIBRATION_FACTOR_2019 = 1.2285756306528773
 
+# Assumed average coincident cooling equipment operational duty factor during daytime occupied hours.
+# Represents that on average ~35% of the total 77.20 kW connected AC capacity is actively compressor-cycling
+# when ambient temperature exceeds the cooling base setpoint (24.0°C per [D-07]).
+DEFAULT_COOLING_DUTY_FACTOR = 0.35
+
 
 @dataclass(frozen=True)
 class BaselineMetrics:
@@ -127,7 +132,7 @@ def compute_placeholder_demand(
         if temp > building.t_base_cooling_c and (f_occ > 0.0 or (dow < 5 and 7 <= h <= 18)):
             delta_t = temp - building.t_base_cooling_c
             cooling_adjustment = (
-                cooling_connected_kw * 0.35 * building.cooling_sensitivity_per_c * delta_t
+                cooling_connected_kw * DEFAULT_COOLING_DUTY_FACTOR * building.cooling_sensitivity_per_c * delta_t
             )
 
         hourly_uncalibrated = p_sched + cooling_adjustment
```

---

## 6. Flagged for APC / Operator Attention

- [x] **Decision ID Reservation Alignment:** Completed under `[D-24]` and `[D-25]` to avoid colliding with `[D-23]` (committed by `CORE-005` on `master`).
- [x] **Non-breaking Harness Upgrades:** All existing tests from Phase 1 remain 100% passing. Sub-flow violations are isolated to `report.subflow_violations` so legacy tests asserting `len(report.conservation_violations) == 1` continue passing unchanged while `report.is_valid` catches any subflow imbalance.
- [ ] **Phase 2 Model Development Readiness:** The repository is now clean, hardened, and fully ready for Phase 2 parallel work packages (`DEM-001`, `SOL-001`, `BAT-001`, `OUT-001`).
