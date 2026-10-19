"""Unit test suite for core canonical domain models and interface contracts."""

from dataclasses import FrozenInstanceError
import pytest

from ccis_sim.core import (
    Battery,
    Building,
    HourlyRecord,
    LoadTier,
    OutageEvent,
    OutageType,
    RoomInventory,
    SolarArray,
)


# --- 1. Immutability Tests ---


def test_models_immutability():
    """Verify that all domain model dataclasses are frozen and immutable."""
    building = Building()
    with pytest.raises(FrozenInstanceError):
        building.gross_floor_area_m2 = 3000.0  # type: ignore

    solar = SolarArray(capacity_kwp=50.0)
    with pytest.raises(FrozenInstanceError):
        solar.capacity_kwp = 100.0  # type: ignore

    battery = Battery(capacity_kwh=100.0)
    with pytest.raises(FrozenInstanceError):
        battery.capacity_kwh = 150.0  # type: ignore

    outage = OutageEvent(start_hour=100, duration_hours=4.0)
    with pytest.raises(FrozenInstanceError):
        outage.duration_hours = 8.0  # type: ignore

    record = HourlyRecord(
        hour=1,
        timestamp="2026-01-01T00:00:00+08:00",
        temp_ambient_c=24.0,
        humidity_rel_pct=80.0,
        ghi_w_m2=0.0,
        demand_gross_kwh=10.0,
        demand_served_kwh=10.0,
        solar_generation_kwh=0.0,
        solar_to_demand_kwh=0.0,
        solar_to_battery_kwh=0.0,
        solar_curtailed_kwh=0.0,
        battery_soc_kwh=20.0,
        battery_charge_kwh=0.0,
        battery_discharge_kwh=0.0,
        grid_import_kwh=10.0,
        unserved_load_kwh=0.0,
        grid_available=True,
        active_load_tier=3,
    )
    with pytest.raises(FrozenInstanceError):
        record.demand_gross_kwh = 15.0  # type: ignore


# --- 2. Building & Room Inventory Tests ---


def test_building_archetype_room_count():
    """Verify 18-room CCIS building archetype locked in decision [D-06]."""
    building = Building()
    assert building.rooms.hyflex_smart_rooms == 2
    assert building.rooms.lecture_rooms == 6
    assert building.rooms.cod_office == 1
    assert building.rooms.dean_and_secretary == 1
    assert building.rooms.faculty_rooms == 2
    assert building.rooms.computer_labs == 6
    assert building.rooms.total_rooms == 18
    assert building.gross_floor_area_m2 == 2500.0
    assert building.usable_rooftop_area_m2 == 1200.0
    assert building.t_base_cooling_c == 24.0
    assert building.cooling_sensitivity_per_c == 0.04
    assert building.latent_cooling_penalty == 0.20


def test_building_invalid_parameters():
    """Verify validation triggers on non-physical building dimensions."""
    with pytest.raises(ValueError, match="gross_floor_area_m2"):
        Building(gross_floor_area_m2=0.0)

    with pytest.raises(ValueError, match="usable_rooftop_area_m2"):
        Building(usable_rooftop_area_m2=-100.0)

    with pytest.raises(ValueError, match="floors"):
        Building(floors=0)


# --- 3. SolarArray Tests ---


@pytest.mark.parametrize("capacity", [0.0, 50.0, 100.0, 200.0])
def test_solar_array_scenario_capacities(capacity: float):
    """Verify solar array instantiation across the scenario matrix."""
    pv = SolarArray(capacity_kwp=capacity)
    assert pv.capacity_kwp == capacity
    assert pv.tilt_deg == 15.0
    assert pv.performance_ratio == 0.77
    assert pv.temp_coeff_pct_per_c == -0.40
    assert pv.noct_c == 45.0
    assert pv.roof_mount_derate_c == 10.0
    assert pv.t_ref_c == 25.0


def test_solar_array_invalid():
    """Verify validation on negative capacity or out-of-range PR."""
    with pytest.raises(ValueError, match="capacity_kwp"):
        SolarArray(capacity_kwp=-5.0)

    with pytest.raises(ValueError, match="performance_ratio"):
        SolarArray(capacity_kwp=50.0, performance_ratio=1.2)


# --- 4. Battery Tests ---


@pytest.mark.parametrize("capacity", [0.0, 50.0, 100.0, 200.0])
def test_battery_scenario_capacities_and_properties(capacity: float):
    """Verify battery instantiation and physical boundary calculations."""
    bat = Battery(capacity_kwh=capacity)
    assert bat.capacity_kwh == capacity
    assert bat.round_trip_efficiency == 0.92
    assert bat.usable_dod == 0.90
    assert bat.min_soc_pct == 0.10
    assert bat.max_charge_c_rate == 0.5
    assert bat.max_discharge_c_rate == 1.0

    # Boundary metrics
    assert bat.min_soc_kwh == capacity * 0.10
    assert bat.max_soc_kwh == capacity * (0.10 + 0.90)
    assert bat.usable_capacity_kwh == capacity * 0.90
    assert bat.emergency_reserve_kwh == capacity * 0.20
    assert bat.max_charge_power_kw == capacity * 0.5
    assert bat.max_discharge_power_kw == capacity * 1.0


def test_battery_invalid():
    """Verify validation on negative capacity, invalid efficiencies, or DoD limits."""
    with pytest.raises(ValueError, match="capacity_kwh"):
        Battery(capacity_kwh=-10.0)

    with pytest.raises(ValueError, match="round_trip_efficiency"):
        Battery(capacity_kwh=50.0, round_trip_efficiency=0.0)

    with pytest.raises(ValueError, match="min_soc_pct \\+ usable_dod"):
        Battery(capacity_kwh=50.0, min_soc_pct=0.20, usable_dod=0.85)


# --- 5. OutageEvent Tests ---


def test_outage_event_normal():
    """Verify normal random outage event behavior."""
    outage = OutageEvent(start_hour=500, duration_hours=4.0, outage_type=OutageType.NORMAL)
    assert outage.start_hour == 500
    assert outage.end_hour == 504.0
    assert outage.outage_type == OutageType.NORMAL
    assert not outage.is_active_at(499)
    assert outage.is_active_at(500)
    assert outage.is_active_at(503)
    assert not outage.is_active_at(504)
    assert not outage.is_solar_depressed_at(500)


def test_outage_event_typhoon():
    """Verify typhoon outage event with solar depression coupling per [D-11]."""
    outage = OutageEvent(
        start_hour=6000,
        duration_hours=24.0,
        outage_type=OutageType.TYPHOON,
        solar_depression_factor=0.25,
        solar_depression_duration_hours=96.0,  # 4 days
    )
    assert outage.is_active_at(6000)
    assert outage.is_active_at(6023)
    assert not outage.is_active_at(6024)

    # Solar depression lasts 96 hours (up to hour 6096)
    assert outage.is_solar_depressed_at(6000)
    assert outage.is_solar_depressed_at(6050)
    assert outage.is_solar_depressed_at(6095)
    assert not outage.is_solar_depressed_at(6096)


def test_outage_invalid():
    """Verify out-of-bounds start hour or non-positive duration."""
    with pytest.raises(ValueError, match="start_hour"):
        OutageEvent(start_hour=0, duration_hours=4.0)

    with pytest.raises(ValueError, match="start_hour"):
        OutageEvent(start_hour=8761, duration_hours=4.0)

    with pytest.raises(ValueError, match="duration_hours"):
        OutageEvent(start_hour=100, duration_hours=0.0)


# --- 6. HourlyRecord Serialization & Conservation Invariants ---


def make_sample_record(
    solar_gen: float = 30.0,
    grid_in: float = 0.0,
    bat_dis: float = 0.0,
    demand_served: float = 15.0,
    bat_chg: float = 10.0,
    curtail: float = 5.0,
) -> HourlyRecord:
    """Helper creating an HourlyRecord with specified energy balance flows."""
    return HourlyRecord(
        hour=1200,
        timestamp="2026-02-19T12:00:00+08:00",
        temp_ambient_c=32.5,
        humidity_rel_pct=75.0,
        ghi_w_m2=850.0,
        demand_gross_kwh=15.0,
        demand_served_kwh=demand_served,
        solar_generation_kwh=solar_gen,
        solar_to_demand_kwh=min(solar_gen, demand_served),
        solar_to_battery_kwh=bat_chg,
        solar_curtailed_kwh=curtail,
        battery_soc_kwh=45.0,
        battery_charge_kwh=bat_chg,
        battery_discharge_kwh=bat_dis,
        grid_import_kwh=grid_in,
        unserved_load_kwh=0.0,
        grid_available=True,
        active_load_tier=LoadTier.TIER_3_SHEDDABLE,
    )


def test_hourly_record_dict_serialization_roundtrip():
    """Verify to_dict and from_dict roundtrip fidelity."""
    rec = make_sample_record()
    data = rec.to_dict()

    assert isinstance(data, dict)
    assert len(data) == 18
    assert data["hour"] == 1200
    assert data["temp_ambient_c"] == 32.5

    rec_reconstructed = HourlyRecord.from_dict(data)
    assert rec_reconstructed == rec


def test_hourly_record_energy_conservation_invariant():
    """Verify physical energy conservation check (sum in == sum out within 1e-5 kWh)."""
    # Balanced case: In = 30 + 0 + 0 = 30; Out = 15 + 10 + 5 = 30. Residual = 0.
    rec_balanced = make_sample_record(
        solar_gen=30.0, grid_in=0.0, bat_dis=0.0, demand_served=15.0, bat_chg=10.0, curtail=5.0
    )
    assert rec_balanced.energy_balance_residual_kwh <= 1e-5
    assert rec_balanced.is_energy_conserved()

    # Slightly noisy balanced case within float precision (1e-6 diff)
    rec_slight = make_sample_record(
        solar_gen=30.000001, grid_in=0.0, bat_dis=0.0, demand_served=15.0, bat_chg=10.0, curtail=5.0
    )
    assert rec_slight.is_energy_conserved(tolerance=1e-5)

    # Unbalanced case (phantom 2 kWh energy deficit): In = 30; Out = 32. Residual = 2.0.
    rec_unbalanced = make_sample_record(
        solar_gen=30.0, grid_in=0.0, bat_dis=0.0, demand_served=17.0, bat_chg=10.0, curtail=5.0
    )
    assert rec_unbalanced.energy_balance_residual_kwh > 1e-5
    assert not rec_unbalanced.is_energy_conserved()


def test_hourly_record_validation():
    """Verify validation triggers on out-of-range hours or invalid load tier."""
    with pytest.raises(ValueError, match="hour"):
        HourlyRecord(
            hour=0,
            timestamp="2026-01-01T00:00:00+08:00",
            temp_ambient_c=25.0,
            humidity_rel_pct=70.0,
            ghi_w_m2=0.0,
            demand_gross_kwh=10.0,
            demand_served_kwh=10.0,
            solar_generation_kwh=0.0,
            solar_to_demand_kwh=0.0,
            solar_to_battery_kwh=0.0,
            solar_curtailed_kwh=0.0,
            battery_soc_kwh=0.0,
            battery_charge_kwh=0.0,
            battery_discharge_kwh=0.0,
            grid_import_kwh=10.0,
            unserved_load_kwh=0.0,
            grid_available=True,
            active_load_tier=1,
        )

    with pytest.raises(ValueError, match="active_load_tier"):
        HourlyRecord(
            hour=1,
            timestamp="2026-01-01T00:00:00+08:00",
            temp_ambient_c=25.0,
            humidity_rel_pct=70.0,
            ghi_w_m2=0.0,
            demand_gross_kwh=10.0,
            demand_served_kwh=10.0,
            solar_generation_kwh=0.0,
            solar_to_demand_kwh=0.0,
            solar_to_battery_kwh=0.0,
            solar_curtailed_kwh=0.0,
            battery_soc_kwh=0.0,
            battery_charge_kwh=0.0,
            battery_discharge_kwh=0.0,
            grid_import_kwh=10.0,
            unserved_load_kwh=0.0,
            grid_available=True,
            active_load_tier=4,  # Invalid tier
        )
