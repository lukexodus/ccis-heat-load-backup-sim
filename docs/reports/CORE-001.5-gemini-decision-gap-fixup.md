# Task Report: CORE-001.5 — Reconcile Uncredited Modeling Assumptions in Domain Models

**Date:** 2026-10-20  
**Agent:** gemini  
**Task ID:** CORE-001.5  
**Status:** done  
**Commit:** pending  
**Patch File:** `patch/CORE-001.5-gemini-decision-gap-fixup.patch`  

---

## 1. Executive Summary

This task executes `CORE-001.5` (Correction / Decision-Recording Gap Closure), resolving two uncredited modeling parameters identified during the APC AI review of `CORE-001`. The prior `CORE-001` report claimed that no new decisions were required beyond `[D-05]`–`[D-11]`; however, two numeric defaults in `src/ccis_sim/core/models.py` represented real architectural choices that lacked explicit decision log entries:
1. `Battery.emergency_reserve_pct = 0.20`: An operational emergency blackout reserve buffer distinct from the physical cell protection floor (`min_soc_pct = 0.10`) locked in `[D-09]`.
2. `Building.usable_rooftop_area_m2 = 1200.0`: A physical unshaded rooftop racking constraint derived from the 2-storey facility's footprint (~1,250 m²) minus mechanical setbacks, which upper-bounds solar array capacity to 200 kWp.

Both parameters have been documented, validated, and formally locked in `docs/decisions/decision-log.md` under **[D-17]** and **[D-18]**. `Battery.emergency_reserve_pct` was retained as an operational decision variable (evaluating in $[0.10, 0.50]$ for `BAT-002` and `DEC-002`), equipped with $[0, 1]$ range validation in `__post_init__`, and accompanied by new unit tests. `Building.usable_rooftop_area_m2` was explicitly labeled as `[ASSUMPTION]` in the code and docstrings. All 56 test cases in the test suite pass cleanly (100% green).

---

## 2. Implementation Details

### 2.1 Changes Made

- `src/ccis_sim/core/models.py`:
  - Updated `Building` docstring and inline comment to reference `[D-18]` and tag `usable_rooftop_area_m2 = 1200.0` as an explicit `[ASSUMPTION]` derived from the ~1,250 m² building footprint minus parapet/HVAC clearances.
  - Updated `Battery` docstring and inline comment to reference `[D-17]`, explaining that `emergency_reserve_pct = 0.20` is a provisional default decision variable for blackouts (evaluating in range $[0.10, 0.50]$ in `BAT-002`), distinct from and additional to the physical cell protection floor (`min_soc_pct = 0.10`) from `[D-09]`.
  - Added boundary validation in `Battery.__post_init__` enforcing `0.0 <= self.emergency_reserve_pct <= 1.0`.
- `tests/test_core_models.py`:
  - Added `test_battery_configurable_emergency_reserve()` verifying that `emergency_reserve_pct` is configurable across the operational range (`0.10`, `0.20`, `0.50`) and properly scales `emergency_reserve_kwh`.
  - Added boundary validation check verifying that out-of-range `emergency_reserve_pct` (e.g. `1.5`) raises `ValueError`.
- `docs/decisions/decision-log.md`:
  - Appended **[D-17]** (Battery configurable emergency outage reserve allocation).
  - Appended **[D-18]** (CCIS usable rooftop solar PV area sizing constraint).
- `docs/tasks/status.md`:
  - Added `CORE-001.5` tracking row linked to this report.

### 2.2 Rationale for Retaining `emergency_reserve_pct`

Rather than deleting `emergency_reserve_pct`, retaining it was chosen because:
1. `docs/context/conceptual-model.md` §3.2 and `docs/tasks/status.md` (`BAT-002.2`) explicitly specify an "Outage Emergency Reserve Allocation ($R_{\text{reserve}} \in [0.10, 0.50]$, Default: 0.20)" as an institutional decision variable.
2. Deleting the field would break backwards compatibility with downstream tasks and existing property methods (`Battery.emergency_reserve_kwh`).
3. Formally recording it under `[D-17]` resolves the governance gap while leaving the dispatch behavior to be implemented in `BAT-002`.

---

## 3. Verification & Test Evidence

### 3.1 Test Execution

Command executed:
```bash
pytest -v
```

**Results:**
- Tests passed: 56
- Tests failed: 0
- Tests skipped: 0

```text
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.0, pytest-sugar-1.1.1
rootdir: /home/lukexodus/projects/ccis-heat-load-backup-sim
configfile: pyproject.toml
testpaths: tests

 tests/test_core_models.py::test_models_immutability ✓             2% ▎         
 tests/test_core_models.py::test_building_archetype_room_count ✓   4% ▍         
 tests/test_core_models.py::test_building_invalid_parameters ✓     5% ▋         
 tests/test_core_models.py::test_solar_array_scenario_capacities[0.0] ✓7% ▊         
 tests/test_core_models.py::test_solar_array_scenario_capacities[50.0] ✓9% ▉         
 tests/test_core_models.py::test_solar_array_scenario_capacities[100.0] ✓11% █▏        
 tests/test_core_models.py::test_solar_array_scenario_capacities[200.0] ✓12% █▍        
 tests/test_core_models.py::test_solar_array_invalid ✓            14% █▌        
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[0.0] ✓16% █▋        
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[50.0] ✓18% █▊        
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[100.0] ✓20% █▉        
 tests/test_core_models.py::test_battery_scenario_capacities_and_properties[200.0] ✓21% ██▎       
 tests/test_core_models.py::test_battery_invalid ✓                23% ██▍       
 tests/test_core_models.py::test_battery_configurable_emergency_reserve ✓25% ██▌       
 tests/test_core_models.py::test_outage_event_normal ✓            27% ██▋       
 tests/test_core_models.py::test_outage_event_typhoon ✓           29% ██▉       
 tests/test_core_models.py::test_outage_invalid ✓                 30% ███       
 tests/test_core_models.py::test_hourly_record_dict_serialization_roundtrip ✓32% ███▎      
 tests/test_core_models.py::test_hourly_record_energy_conservation_invariant ✓34% ███▌      
 tests/test_core_models.py::test_hourly_record_validation ✓       36% ███▋      
 tests/test_equipment_audit.py::test_audit_fixture_files_exist ✓  38% ███▊      
 tests/test_equipment_audit.py::test_schema_csv_format ✓          39% ███▉      
 tests/test_equipment_audit.py::test_equipment_item_valid_instantiation ✓41% ████▏     
 tests/test_equipment_audit.py::test_equipment_item_cooling_detection ✓43% ████▍     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs0-count must be a positive integer] ✓45% ████▌     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs1-count must be a positive integer] ✓46% ████▋     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs2-rated_kw must be non-negative] ✓48% ████▊     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs3-hours_per_day must be in [0, 24]] ✓50% █████     
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs4-hours_per_day must be in [0, 24]] ✓52% █████▎    
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs5-tier must be 1, 2, or 3] ✓54% █████▍    
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs6-tier must be 1, 2, or 3] ✓55% █████▋    
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs7-duty_cycle must be in [0.0, 1.0]] ✓57% █████▊    
 tests/test_equipment_audit.py::test_equipment_item_boundary_validation[kwargs8-duty_cycle must be in [0.0, 1.0]] ✓59% █████▉    
 tests/test_equipment_audit.py::test_load_audit_from_csv ✓        61% ██████▏   
 tests/test_all_18_rooms_archetype_covered ✓                      62% ██████▍   
 tests/test_tier_distribution_and_shedding_alignment ✓            64% ██████▌   
 tests/test_building_dataclass_compatibility ✓                    66% ██████▋   
 tests/test_load_nonexistent_file_raises ✓                        68% ██████▊   
 tests/test_mock_bills.py::test_generate_12_monthly_bills ✓       70% ██████▉   
 tests/test_mock_bills.py::test_mock_bill_internal_energy_conservation ✓71% ███████▎  
 tests/test_mock_bills.py::test_annual_eui_benchmark_conformance ✓73% ███████▍  
 tests/test_mock_bills.py::test_committed_fixture_eui_plausibility ✓75% ███████▌  
 tests/test_mock_bills.py::test_hot_season_cooling_elevation ✓    77% ███████▊  
 tests/test_mock_bills.py::test_academic_break_reduction ✓        79% ███████▉  
 tests/test_mock_bills.py::test_csv_save_and_load_roundtrip ✓     80% ████████▏ 
 tests/test_mock_bills.py::test_generator_seed_reproducibility ✓  82% ████████▎ 
 tests/test_smoke.py::test_package_version ✓                      84% ████████▍ 
 tests/test_smoke.py::test_submodules_importable[ccis_sim.core] ✓ 86% ████████▋ 
 tests/test_smoke.py::test_submodules_importable[ccis_sim.demand] ✓88% ████████▊ 
 tests/test_smoke.py::test_submodules_importable[ccis_sim.solar] ✓89% ████████▉ 
 tests/test_smoke.py::test_submodules_importable[ccis_sim.battery] ✓91% █████████▎
 tests/test_smoke.py::test_submodules_importable[ccis_sim.outage] ✓93% █████████▍
 tests/test_smoke.py::test_submodules_importable[ccis_sim.integration] ✓95% █████████▌
 tests/test_smoke.py::test_submodules_importable[ccis_sim.decision] ✓96% █████████▋
 tests/test_smoke.py::test_numpy_environment_sanity ✓             98% █████████▊
 tests/test_smoke.py::test_scipy_environment_sanity ✓            100% ██████████

Results (6.55s):
      56 passed
```

---

## 4. Decisions Recorded

Two new architectural decisions were recorded in `docs/decisions/decision-log.md`:

- **[D-17]**: Battery configurable emergency outage reserve allocation locked. Establishes `Battery.emergency_reserve_pct` (provisional default 0.20, configurable in $[0.10, 0.50]$), distinct from the 10% min SoC protection floor from `[D-09]`.
- **[D-18]**: CCIS usable rooftop solar PV area sizing constraint locked. Parameterizes `Building.usable_rooftop_area_m2 = 1200.0` as an explicit `[ASSUMPTION]` based on 2-storey footprint (~1,250 m²) minus mechanical setbacks, bounding maximum solar capacity to 200 kWp at 6.0 m²/kWp.

---

## 5. Unified Git Diff

```diff
diff --git a/docs/decisions/decision-log.md b/docs/decisions/decision-log.md
index ea9b7cc..1ef0a22 100644
--- a/docs/decisions/decision-log.md
+++ b/docs/decisions/decision-log.md
@@ -87,3 +87,17 @@
 - **Reasoning:** Reconciles the operator-confirmed 18-room spatial ground truth [D-06] with verified hardware power ratings (dual 3.0 HP inverter ACs and 40 desktop PCs per lab to reject high thermal heat loads in Batac). Replaces inaccessible real utility bills with an auditable, reproducible synthetic calibration baseline satisfying the zero-institutional-data constraint [D-03].  
 - **Affects:** `CORE-003`, `CORE-005`, `DEM-001`, `DEM-002`, `OUT-002`, `INT-001`.
+
+**[D-17]** Battery configurable emergency outage reserve allocation locked.  
+- **Date / Session:** 2026-10-20  
+- **Decision:** Establish `Battery.emergency_reserve_pct` with a provisional default value of 0.20 (20% of rated capacity), representing a dedicated operational blackout reserve buffer. This parameter is distinct from and additional to the non-discretionary 10% minimum state-of-charge protection floor ($SoC_{\text{min}} = 0.10 \times C_{\text{bat}}$) locked in [D-09]. It is configurable across $[0.10, 0.50]$ to support the outage resilience sweeps in `BAT-002.2` and multi-criteria decision analysis in `DEC-002`.  
+- **Reasoning:** While [D-09] protects battery cell physical longevity by preventing deep discharge below 10% SoC under all conditions, resilience during extended blackouts requires an operational buffer held in reserve rather than depleted during daily evening peak load. A default 20% allocation ensures critical Tier 1 and Tier 2 loads can sustain initial transfer and runtime during unanticipated utility outages while preserving the cell longevity floor.  
+- **Affects:** `Battery`, `BAT-001`, `BAT-002`, `INT-001`, `DEC-002`.
+
+**[D-18]** CCIS usable rooftop solar PV area sizing constraint locked.  
+- **Date / Session:** 2026-10-20  
+- **Decision:** Parameterize the CCIS facility with a maximum usable unshaded rooftop PV mounting area of 1,200 m² (`Building.usable_rooftop_area_m2 = 1200.0`), tagged as an explicit `[ASSUMPTION]`. At a commercial monocrystalline packing density of 6.0 m²/kWp (~167 W/m² module rating accounting for maintenance walkways and inter-row spacing), this directly caps maximum rooftop solar capacity at 200 kWp, bounding the project's scenario matrix ($P_{\text{kWp}} \in \{0, 50, 100, 200\}\text{ kWp}$).  
+- **Reasoning:** Conforms to physical building geometry: a 2-storey building of ~2,500 m² gross floor area has a building footprint of ~1,250 m². Deducting ~50 m² for parapets, rooftop access, and mechanical HVAC compressor clearances yields ~1,200 m² of usable racking space.  
+- **Affects:** `Building`, `SOL-001`, `SOL-002`, `INT-003`.
diff --git a/docs/tasks/status.md b/docs/tasks/status.md
index 18ff78b..fa7a346 100644
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -45,2 +45,3 @@
 | CORE-001.4   | Write unit test suite for domain models and data invariants                      | `done` | 29 pytest tests passing (100% green)                                             |
+| CORE-001.5   | Reconcile uncredited assumptions in Battery & Building ([D-17], [D-18])          | `done` | [CORE-001.5-gemini-decision-gap-fixup.md](../reports/CORE-001.5-gemini-decision-gap-fixup.md) |
diff --git a/src/ccis_sim/core/models.py b/src/ccis_sim/core/models.py
index a543ec8..b8293ad 100644
--- a/src/ccis_sim/core/models.py
+++ b/src/ccis_sim/core/models.py
@@ -53,4 +53,6 @@
-    """Building envelope and architectural baseline for MMSU CCIS per decision [D-06].
+    """Building envelope and architectural baseline for MMSU CCIS per decisions [D-06], [D-07], and [D-18].
 
      Static building envelope parameters. Equipment electrical loading and schedules
      are parameterized and loaded separately in CORE-003.
+    usable_rooftop_area_m2 is derived from the ~1,250 m² footprint of the 2-storey facility
+    minus parapets and mechanical setbacks, accommodating up to 200 kWp PV at 6.0 m²/kWp (per [D-18]).
      """
@@ -64,3 +66,3 @@
-    usable_rooftop_area_m2: float = 1200.0
+    usable_rooftop_area_m2: float = 1200.0   # [ASSUMPTION / [D-18]] ~1,250 m² 2-storey footprint minus setbacks (~1,200 m² usable)
@@ -104,4 +106,6 @@
-    """Lithium Iron Phosphate (LFP) Battery Energy Storage System (BESS) per decision [D-09].
+    """Lithium Iron Phosphate (LFP) Battery Energy Storage System (BESS) per decisions [D-09] and [D-17].
 
      Can be instantiated across scenario matrix capacities (0, 50, 100, 200 kWh).
      Static parameters and boundary limits. Dispatch logic is handled in Phase 2 (BAT-001/002).
+    emergency_reserve_pct specifies a configurable operational blackout reserve (per [D-17] and BAT-002),
+    distinct from and additional to the non-discretionary 10% min SoC protection floor from [D-09].
      """
@@ -119,3 +123,3 @@
-    emergency_reserve_pct: float = 0.20      # 20% reserved for blackouts per [D-09]
+    emergency_reserve_pct: float = 0.20      # [D-17] Default 20% emergency blackout reserve (configurable in [0.10, 0.50] for BAT-002)
@@ -131,2 +135,6 @@
+        if not (0.0 <= self.emergency_reserve_pct <= 1.0):
+            raise ValueError(
+                f"emergency_reserve_pct must be in [0, 1], got {self.emergency_reserve_pct}"
+            )
diff --git a/tests/test_core_models.py b/tests/test_core_models.py
index b6b6f72..8ca549e 100644
--- a/tests/test_core_models.py
+++ b/tests/test_core_models.py
@@ -153,2 +153,18 @@
+    with pytest.raises(ValueError, match="emergency_reserve_pct"):
+        Battery(capacity_kwh=50.0, emergency_reserve_pct=1.5)
+
+
+def test_battery_configurable_emergency_reserve():
+    """Verify emergency_reserve_pct is configurable across [0.10, 0.50] for BAT-002 per [D-17]."""
+    bat_low = Battery(capacity_kwh=100.0, emergency_reserve_pct=0.10)
+    assert bat_low.emergency_reserve_kwh == 10.0
+
+    bat_mid = Battery(capacity_kwh=100.0, emergency_reserve_pct=0.20)
+    assert bat_mid.emergency_reserve_kwh == 20.0
+
+    bat_high = Battery(capacity_kwh=100.0, emergency_reserve_pct=0.50)
+    assert bat_high.emergency_reserve_kwh == 50.0
```

---

## 6. Flagged for APC / Operator Attention

- [x] Both uncredited parameters are formally locked under `[D-17]` and `[D-18]`.
- [x] Battery emergency reserve is verified as a configurable decision variable $[0.10, 0.50]$.
- [x] Fully unblocks `CORE-004` (Energy Balance & Battery Boundary Invariant Checker).
