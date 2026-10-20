# Shared Golden Reference Fixtures

This directory and the `ccis_sim.core.verification` module provide shared golden reference fixtures and assertion harnesses for validating simulation outputs across sub-model tasks (`DEM-001/002`, `SOL-001/002`, `BAT-001/002`, `OUT-001/002`, `CORE-005`, and `INT-001/002/003`).

## Golden Scenario Fixture: `create_golden_scenario()`

`create_golden_scenario(battery: Battery | None = None) -> list[HourlyRecord]`

Constructs a 48-hour continuous synthetic scenario (Hour 1 to Hour 48) containing known-correct, hand-calculated energy flows covering all primary microgrid operational modes:
- **Nighttime battery discharge**: Discharges down to the 10% non-discretionary minimum protection floor ($SoC_{\min} = 10.0\text{ kWh}$).
- **Nighttime grid import**: Grid sustains building baseload while battery remains at the protection floor.
- **Solar generation ramp**: PV output serves building load and routes excess into battery storage.
- **Solar curtailment**: Battery reaches 100% capacity ($100.0\text{ kWh}$), and remaining solar surplus is curtailed.
- **Zero net-load hour**: Hour 15 has solar generation exactly matching building load.
- **Afternoon/evening battery dispatch**: Battery supplements declining solar generation.
- **Grid outage & priority load shedding**: Hours 30–37 simulate an 8-hour utility blackout (`grid_available = False`), shedding Tier 3 load to Tier 2 essential load ($5.0\text{ kW}$), sustained by islanded battery and depressed solar.
- **Grid restoration & recovery**: Grid returns at Hour 38, restoring normal Tier 3 operations.

Every single record has an exact residual of $0.000000\text{ kWh}$ and strictly satisfies all battery boundary conditions.

## Usage in Downstream Test Suites

Instead of reinventing fixture generation or copy-pasting assertion boilerplate, import and use the shared harness:

```python
import pytest
from ccis_sim.core import (
    Battery,
    HourlyRecord,
    assert_simulation_valid,
    check_energy_conservation,
    create_golden_scenario,
    run_verification_harness,
    validate_battery_boundaries,
)

def test_my_submodel_energy_balance():
    # 1. Obtain golden reference sequence or generate records from your submodel
    battery = Battery(capacity_kwh=100.0)
    records = create_golden_scenario(battery=battery)

    # 2. Run verification harness
    report = run_verification_harness(records, battery=battery)
    assert report.is_valid, report.summary()

def test_my_submodel_assertions():
    # Or use direct assertion helper (raises AssertionError with full diagnostic summary on failure)
    records = ... # your simulation records
    assert_simulation_valid(records, battery=battery)
```

## Available Verification Functions

1. `check_energy_conservation(records, tolerance=1e-5, cumulative_tolerance=None) -> list[ConservationViolation]`
   - Validates per-hour energy conservation ($\text{residual} \le 10^{-5}\text{ kWh}$).
   - Validates cumulative conservation drift ($\Delta E_{\text{net}} \le \max(10^{-5}, \sqrt{N} \times 10^{-5})$ per decision `[D-21]`).
2. `validate_battery_boundaries(records, battery, allow_emergency_drawdown=False) -> list[BatteryBoundaryViolation]`
   - Validates $0 \le SoC(t) \le C_{\text{bat}}$.
   - Validates $SoC(t) \ge SoC_{\min}$ (10% floor outside permitted emergency blackouts).
   - Validates C-rate power bounds ($0.5\text{C}$ charge, $1.0\text{C}$ discharge).
   - Validates mutual exclusivity (no simultaneous charge and discharge $> 10^{-6}\text{ kWh}$).
3. `run_verification_harness(records, battery=None, ...) -> VerificationReport`
   - Complete verification run returning structured diagnostic report with `summary()`.
4. `assert_simulation_valid(records, battery=None, ...) -> None`
   - Test assertion helper.
