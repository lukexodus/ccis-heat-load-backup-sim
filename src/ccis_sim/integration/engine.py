"""Integrated time-step simulation engine for CCIS microgrid.

Composes demand (DEM-001/002), solar generation (SOL-001/002), stochastic outages
(OUT-001), priority load shedding (OUT-002), battery dispatch dynamics (BAT-001),
and reserve constraints/idle losses (BAT-002) into a unified deterministic hourly loop.

Conforms strictly to Phase 2 interface contract (docs/context/phase2-interface-contract.md)
and architectural decisions [D-26] through [D-35].
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from ccis_sim.battery.dynamics import step_battery
from ccis_sim.battery.reserve import apply_idle_losses, soc_floor_kwh
from ccis_sim.core.interfaces import OutageSchedule, TieredDemand
from ccis_sim.core.models import Battery, Building, HourlyRecord, LoadTier, SolarArray
from ccis_sim.core.verification import assert_simulation_valid
from ccis_sim.demand.cooling import compute_cooling_demand
from ccis_sim.demand.equipment import EquipmentAudit
from ccis_sim.demand.non_cooling import compute_non_cooling_demand
from ccis_sim.demand.schedule import AcademicCalendar, build_occupancy_schedule
from ccis_sim.outage.sampler import apply_ghi_multiplier, sample_outage_schedule
from ccis_sim.outage.shedding import UnservedTracker, shed_for_hour
from ccis_sim.solar.array import compute_ac_generation
from ccis_sim.solar.irradiance import compute_dc_power_per_kwp
from ccis_sim.weather.loader import load_weather_fixture


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration parameters for the CCIS hourly microgrid simulation engine.

    All parameters are strictly validated upon initialization.
    """

    solar_kwp: float = 0.0
    """Installed DC capacity of the rooftop solar PV array (kWp). Range: [0.0, 200.0]."""

    battery_kwh: float = 0.0
    """Rated nominal capacity of the Lithium Iron Phosphate (LFP) battery (kWh). Range: [0.0, 200.0]."""

    weather_year: int = 2019
    """Weather reference fixture year: 2019 (baseline) or 2016 (El Niño hot year)."""

    temp_offset_c: float = 0.0
    """Additive ambient temperature perturbation in °C (e.g. +2.0°C for climate sensitivity)."""

    outage_regime: Literal["normal", "typhoon"] = "normal"
    """Stochastic utility outage arrival regime ('normal' or 'typhoon') per [D-11]."""

    seed: int = 42
    """Deterministic random seed for the numpy random generator driving stochastic outages."""

    initial_soc_kwh: float | None = None
    """Initial battery stored chemical energy (kWh). If None, defaults to full battery capacity."""

    tier2_shed_soc_fraction: float = 0.20
    """Battery SoC fraction threshold below which Tier 2 load is shed during blackouts per [D-34]."""

    emergency_reserve_pct: float = 0.20
    """Operational blackout reserve buffer fraction held from routine daily cycling per [D-17]."""

    allow_emergency_drawdown: bool = False
    """Permit catastrophic emergency drawdown below 10% min_soc during blackouts per [D-25]."""

    def __post_init__(self) -> None:
        if self.solar_kwp < 0.0 or self.solar_kwp > 200.0:
            raise ValueError(f"solar_kwp must be in [0.0, 200.0], got {self.solar_kwp}")
        if self.battery_kwh < 0.0 or self.battery_kwh > 200.0:
            raise ValueError(f"battery_kwh must be in [0.0, 200.0], got {self.battery_kwh}")
        if self.weather_year not in (2016, 2019):
            raise ValueError(f"weather_year must be 2016 or 2019, got {self.weather_year}")
        if self.outage_regime not in ("normal", "typhoon"):
            raise ValueError(f"outage_regime must be 'normal' or 'typhoon', got '{self.outage_regime}'")
        if not (0.0 <= self.tier2_shed_soc_fraction <= 1.0):
            raise ValueError(
                f"tier2_shed_soc_fraction must be in [0.0, 1.0], got {self.tier2_shed_soc_fraction}"
            )
        if not (0.0 <= self.emergency_reserve_pct <= 1.0):
            raise ValueError(
                f"emergency_reserve_pct must be in [0.0, 1.0], got {self.emergency_reserve_pct}"
            )
        if self.initial_soc_kwh is not None:
            if self.battery_kwh > 0.0:
                if not (0.0 <= self.initial_soc_kwh <= self.battery_kwh):
                    raise ValueError(
                        f"initial_soc_kwh must be in [0.0, {self.battery_kwh}], got {self.initial_soc_kwh}"
                    )
            elif self.initial_soc_kwh != 0.0:
                raise ValueError("initial_soc_kwh must be 0.0 when battery_kwh is 0.0")


@dataclass(frozen=True)
class SimulationResult:
    """Complete output artifact from an annual simulation execution.

    Contains the configuration, chronological hourly records, aggregate energy metrics,
    the active outage schedule, and the load shedding tracker summary.
    """

    config: SimulationConfig
    records: list[HourlyRecord]
    metrics: dict[str, Any]
    outage_schedule: OutageSchedule
    tracker_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert simulation outcome to a dictionary representation."""
        return {
            "config": asdict(self.config),
            "metrics": self.metrics,
            "tracker_summary": self.tracker_summary,
            "record_count": len(self.records),
        }


def _compute_simulation_metrics(
    records: Sequence[HourlyRecord],
    config: SimulationConfig,
    tracker: UnservedTracker,
    building: Building,
) -> dict[str, Any]:
    """Calculate key headline, performance, and reliability metrics from simulation records."""
    if not records:
        return {}

    annual_gross_demand = sum(r.demand_gross_kwh for r in records)
    annual_served_demand = sum(r.demand_served_kwh for r in records)
    annual_unserved_load = sum(r.unserved_load_kwh for r in records)
    annual_grid_import = sum(r.grid_import_kwh for r in records)
    annual_solar_generation = sum(r.solar_generation_kwh for r in records)
    annual_solar_to_demand = sum(r.solar_to_demand_kwh for r in records)
    annual_solar_to_battery = sum(r.solar_to_battery_kwh for r in records)
    annual_solar_curtailed = sum(r.solar_curtailed_kwh for r in records)
    annual_battery_charge = sum(r.battery_charge_kwh for r in records)
    annual_battery_discharge = sum(r.battery_discharge_kwh for r in records)

    peak_record = max(records, key=lambda r: r.demand_gross_kwh)
    peak_demand_kw = peak_record.demand_gross_kwh
    peak_timestamp = peak_record.timestamp
    peak_hour = peak_record.hour

    eui_kwh_per_m2 = annual_served_demand / building.gross_floor_area_m2
    gross_eui_kwh_per_m2 = annual_gross_demand / building.gross_floor_area_m2

    self_sufficiency_pct = (
        (1.0 - annual_grid_import / annual_served_demand) * 100.0
        if annual_served_demand > 0.0
        else 0.0
    )

    solar_specific_yield_kwh_per_kwp = (
        annual_solar_generation / config.solar_kwp
        if config.solar_kwp > 0.0
        else 0.0
    )

    max_residual = max(r.energy_balance_residual_kwh for r in records)
    net_drift = sum(r.signed_residual_kwh for r in records)

    return {
        "annual_gross_demand_kwh": annual_gross_demand,
        "annual_served_demand_kwh": annual_served_demand,
        "annual_unserved_load_kwh": annual_unserved_load,
        "annual_grid_import_kwh": annual_grid_import,
        "annual_solar_generation_kwh": annual_solar_generation,
        "annual_solar_to_demand_kwh": annual_solar_to_demand,
        "annual_solar_to_battery_kwh": annual_solar_to_battery,
        "annual_solar_curtailed_kwh": annual_solar_curtailed,
        "annual_battery_charge_kwh": annual_battery_charge,
        "annual_battery_discharge_kwh": annual_battery_discharge,
        "battery_throughput_kwh": annual_battery_discharge,
        "solar_specific_yield_kwh_per_kwp": solar_specific_yield_kwh_per_kwp,
        "peak_demand_kw": peak_demand_kw,
        "peak_hour": peak_hour,
        "peak_timestamp": peak_timestamp,
        "eui_kwh_per_m2_year": eui_kwh_per_m2,
        "gross_eui_kwh_per_m2_year": gross_eui_kwh_per_m2,
        "self_sufficiency_pct": self_sufficiency_pct,
        "total_outage_hours": tracker.total_outage_hours,
        "unserved_tier1_kwh": tracker.unserved_tier1_kwh,
        "unserved_tier2_kwh": tracker.unserved_tier2_kwh,
        "unserved_tier3_kwh": tracker.unserved_tier3_kwh,
        "outage_hours_tier1_served": tracker.outage_hours_tier1_served,
        "outage_hours_tier2_served": tracker.outage_hours_tier2_served,
        "outage_hours_tier3_served": tracker.outage_hours_tier3_served,
        "outage_tier1_coverage_pct": tracker.outage_hours_tier1_served_pct,
        "outage_tier2_coverage_pct": tracker.outage_hours_tier2_served_pct,
        "outage_tier3_coverage_pct": tracker.outage_hours_tier3_served_pct,
        "max_energy_balance_residual_kwh": max_residual,
        "cumulative_net_drift_kwh": net_drift,
    }


def simulate(
    config: SimulationConfig,
    weather_df: pd.DataFrame | None = None,
    seed: int | None = None,
    *,
    audit: EquipmentAudit | None = None,
    building: Building | None = None,
    calendar: AcademicCalendar | None = None,
    verify: bool = True,
) -> SimulationResult:
    """Execute integrated annual simulation across all microgrid sub-models.

    Follows the 8-step dispatch sequence defined in docs/context/phase2-interface-contract.md §5:
    1. Demand decomposition: non-cooling (DEM-001) + cooling response (DEM-002) summed per tier.
    2. Grid availability query: OutageSchedule (OUT-001).
    3. Priority load shedding: shed_for_hour (OUT-002).
    4. Solar AC generation: irradiance transposition (SOL-001) + inverter clipping (SOL-002)
       with typhoon GHI multiplier applied to weather before transposition.
    5. Bus energy balance & battery dispatch: step_battery (BAT-001) with soc_floor_kwh (BAT-002).
    6. Idle losses: apply_idle_losses on resulting chemical SoC (BAT-002).
    7. Grid balance & unserved load tracking: import or blackout unserved tracking (OUT-002).
    8. Canonical record construction: HourlyRecord creation and physical invariant checks.

    Parameters
    ----------
    config : SimulationConfig
        Sizing, weather, and operational regime configuration.
    weather_df : pd.DataFrame, optional
        Pre-loaded weather DataFrame. If None, loads canonical fixture for config.weather_year.
    seed : int, optional
        Random seed override for stochastic outage generation.
    audit : EquipmentAudit, optional
        Equipment inventory audit instance. If None, loads canonical CSV fixture.
    building : Building, optional
        Building archetype instance. If None, initializes default CCIS Building.
    calendar : AcademicCalendar, optional
        SUC academic calendar instance. If None, initializes default AcademicCalendar.
    verify : bool, optional
        If True, invokes assert_simulation_valid across records before returning (default: True).

    Returns
    -------
    SimulationResult
        Completed simulation run containing hourly records, summary metrics, and trackers.
    """
    bldg = building or Building()
    cal = calendar or AcademicCalendar()
    aud = audit or EquipmentAudit.load_from_csv("data/fixtures/equipment-audit-ccis.csv")

    # 1. Ingest & sanitize weather input
    if weather_df is None:
        raw_weather = load_weather_fixture(config.weather_year)
    else:
        raw_weather = weather_df.copy(deep=True)

    w_df = raw_weather.copy(deep=True)
    if config.temp_offset_c != 0.0:
        w_df["t_amb"] = w_df["t_amb"] + config.temp_offset_c

    n_hours = len(w_df)
    if n_hours == 0:
        raise ValueError("Weather DataFrame must not be empty.")

    # 2. Stochastic Outage Schedule (OUT-001)
    run_seed = seed if seed is not None else config.seed
    rng = np.random.default_rng(run_seed)
    outage_schedule = sample_outage_schedule(config.outage_regime, rng, n_hours=n_hours)

    # 3. Demand Sub-Models (DEM-001 + DEM-002)
    # [ASSUMPTION] Build annual occupancy schedule and non-cooling demand per [D-27]
    occupancy_schedule = build_occupancy_schedule(w_df["timestamp"], calendar=cal)
    non_cooling_demand = compute_non_cooling_demand(occupancy_schedule, aud, bldg)

    # [ASSUMPTION] Compute temperature/humidity cooling demand response per [D-28]
    cooling_demand = compute_cooling_demand(
        w_df,
        occupancy_schedule.occupancy_fraction,
        aud,
        bldg,
    )

    # Linear tier summation per Phase 2 contract §4.1
    t1_demand_arr = non_cooling_demand.tier1_kwh + cooling_demand.tier1_kwh
    t2_demand_arr = non_cooling_demand.tier2_kwh + cooling_demand.tier2_kwh
    t3_demand_arr = non_cooling_demand.tier3_kwh + cooling_demand.tier3_kwh

    # 4. Solar Sub-Models (SOL-001 + SOL-002)
    # Apply typhoon solar GHI depression window if active per [D-11] and [D-33]
    weather_for_solar = apply_ghi_multiplier(w_df, outage_schedule)

    if config.solar_kwp > 0.0:
        dc_per_kwp = compute_dc_power_per_kwp(weather_for_solar)
        solar_array = SolarArray(capacity_kwp=config.solar_kwp)
        ac_generation_arr = compute_ac_generation(dc_per_kwp, solar_array)
    else:
        ac_generation_arr = np.zeros(n_hours, dtype=np.float64)

    # 5. Battery Initialization (BAT-001 + BAT-002)
    battery = Battery(
        capacity_kwh=config.battery_kwh,
        emergency_reserve_pct=config.emergency_reserve_pct,
    )

    if config.battery_kwh > 0.0:
        current_soc_kwh = (
            config.initial_soc_kwh
            if config.initial_soc_kwh is not None
            else config.battery_kwh  # Default full battery at simulation start
        )
    else:
        current_soc_kwh = 0.0

    initial_soc_for_verify = current_soc_kwh

    # 6. Hourly Dispatch Loop
    records: list[HourlyRecord] = []
    tracker = UnservedTracker()

    hours_list = w_df["hour"].to_numpy(dtype=int)
    timestamps_list = w_df["timestamp"].to_list()
    t_amb_list = w_df["t_amb"].to_numpy(dtype=float)
    rh_list = w_df["rh"].to_numpy(dtype=float)
    ghi_list = w_df["ghi"].to_numpy(dtype=float)

    for i in range(n_hours):
        hour_val = int(hours_list[i])
        ts_val = str(timestamps_list[i])
        t_amb_val = float(t_amb_list[i])
        rh_val = float(rh_list[i])
        ghi_val = float(ghi_list[i])

        # Step 1: Tiered demand components for hour i
        t1_val = float(t1_demand_arr[i])
        t2_val = float(t2_demand_arr[i])
        t3_val = float(t3_demand_arr[i])
        tier_demand_kwh = (t1_val, t2_val, t3_val)
        demand_gross_kwh = t1_val + t2_val + t3_val

        # Step 2: Grid availability for hour i
        grid_avail = bool(outage_schedule.grid_available[i])

        # Step 3: Priority load shedding
        shed_res = shed_for_hour(
            tier_demand_kwh,
            grid_available=grid_avail,
            soc_kwh=current_soc_kwh,
            battery=battery,
            tier2_shed_soc_fraction=config.tier2_shed_soc_fraction,
        )
        active_tier_int = int(shed_res.active_tier)
        target_served_kwh = sum(shed_res.served_kwh)

        # Step 4: Solar generation available
        solar_gen_kwh = float(ac_generation_arr[i])

        # Step 5: Bus energy routing & battery request
        if solar_gen_kwh >= target_served_kwh:
            # Solar surplus: load is fully served by solar
            solar_to_demand_kwh = target_served_kwh
            surplus_solar_kwh = solar_gen_kwh - target_served_kwh

            charge_req_kwh = surplus_solar_kwh
            discharge_req_kwh = 0.0
            floor_kwh = 0.0

            step_res = step_battery(
                current_soc_kwh,
                battery,
                charge_req_kwh,
                0.0,
                soc_floor_kwh=floor_kwh,
                delta_t_hours=1.0,
            )

            battery_charge_kwh = step_res.charge_kwh
            battery_discharge_kwh = 0.0
            solar_to_battery_kwh = step_res.charge_kwh
            solar_curtailed_kwh = step_res.charge_curtailed_kwh

            grid_import_kwh = 0.0
            shortfall_kwh = 0.0
            soc_after_step = step_res.soc_kwh
        else:
            # Solar deficit: all solar serves load, deficit requested from battery
            solar_to_demand_kwh = solar_gen_kwh
            solar_to_battery_kwh = 0.0
            solar_curtailed_kwh = 0.0
            battery_charge_kwh = 0.0

            deficit_kwh = target_served_kwh - solar_gen_kwh

            floor_kwh = soc_floor_kwh(
                battery,
                grid_available=grid_avail,
                active_load_tier=active_tier_int,
                allow_emergency_drawdown=config.allow_emergency_drawdown,
            )

            step_res = step_battery(
                current_soc_kwh,
                battery,
                0.0,
                deficit_kwh,
                soc_floor_kwh=floor_kwh,
                delta_t_hours=1.0,
            )

            battery_discharge_kwh = step_res.discharge_kwh
            shortfall_kwh = deficit_kwh - battery_discharge_kwh
            soc_after_step = step_res.soc_kwh

            if grid_avail:
                grid_import_kwh = shortfall_kwh
                shortfall_kwh = 0.0
            else:
                grid_import_kwh = 0.0

        # Step 6: Battery chemical idle losses (ambient self-discharge + tare)
        if config.battery_kwh > 0.0:
            final_soc_kwh, idle_loss_kwh = apply_idle_losses(
                soc_after_step,
                battery,
                delta_t_hours=1.0,
            )
        else:
            final_soc_kwh = 0.0

        # Step 7: Unserved energy tracking & allocation
        act_served_tiers, act_unserved_tiers = tracker.record(
            shed_res,
            grid_available=grid_avail,
            battery_shortfall_kwh=shortfall_kwh,
        )

        demand_served_kwh = sum(act_served_tiers)
        unserved_load_kwh = sum(act_unserved_tiers)

        # Advance SoC for next chronological hour
        current_soc_kwh = final_soc_kwh

        # Step 8: Construct canonical HourlyRecord
        record = HourlyRecord(
            hour=hour_val,
            timestamp=ts_val,
            temp_ambient_c=t_amb_val,
            humidity_rel_pct=rh_val,
            ghi_w_m2=ghi_val,
            demand_gross_kwh=demand_gross_kwh,
            demand_served_kwh=demand_served_kwh,
            solar_generation_kwh=solar_gen_kwh,
            solar_to_demand_kwh=solar_to_demand_kwh,
            solar_to_battery_kwh=solar_to_battery_kwh,
            solar_curtailed_kwh=solar_curtailed_kwh,
            battery_soc_kwh=final_soc_kwh,
            battery_charge_kwh=battery_charge_kwh,
            battery_discharge_kwh=battery_discharge_kwh,
            grid_import_kwh=grid_import_kwh,
            unserved_load_kwh=unserved_load_kwh,
            grid_available=grid_avail,
            active_load_tier=active_tier_int,
        )
        records.append(record)

    # 7. Verification Invariant Check
    if verify:
        assert_simulation_valid(
            records=records,
            battery=battery if config.battery_kwh > 0.0 else None,
            allow_emergency_drawdown=config.allow_emergency_drawdown,
            initial_soc_kwh=initial_soc_for_verify if config.battery_kwh > 0.0 else None,
        )

    # 8. Compute headline & reliability metrics
    metrics = _compute_simulation_metrics(records, config, tracker, bldg)

    return SimulationResult(
        config=config,
        records=records,
        metrics=metrics,
        outage_schedule=outage_schedule,
        tracker_summary=tracker.summary(),
    )
