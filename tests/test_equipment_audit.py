"""Unit and integration test suite for CCIS equipment audit model and fixtures."""

from pathlib import Path
import re
import pytest

from ccis_sim.core import Building, RoomInventory
from ccis_sim.demand.equipment import EquipmentAudit, EquipmentItem

FIXTURES_DIR = Path(__file__).parent.parent / "data" / "fixtures"
AUDIT_CSV_PATH = FIXTURES_DIR / "equipment-audit-ccis.csv"
SCHEMA_CSV_PATH = FIXTURES_DIR / "equipment-audit-schema.csv"


# --- 1. Fixture & Schema Existence Tests ---


def test_audit_fixture_files_exist():
    """Verify that both schema definition and CCIS audit CSV fixtures exist."""
    assert SCHEMA_CSV_PATH.exists(), f"Schema file missing: {SCHEMA_CSV_PATH}"
    assert AUDIT_CSV_PATH.exists(), f"CCIS audit fixture missing: {AUDIT_CSV_PATH}"


def test_schema_csv_format():
    """Verify that the schema definition file has required descriptor columns."""
    with open(SCHEMA_CSV_PATH, mode="r", encoding="utf-8") as f:
        header = f.readline().strip().split(",")
    expected_header = ["column_name", "data_type", "required", "description", "example"]
    assert header == expected_header


# --- 2. EquipmentItem Domain Model Invariants ---


def test_equipment_item_valid_instantiation():
    """Verify valid EquipmentItem creation and derived properties."""
    item = EquipmentItem(
        item="Lab Desktop PC",
        room_type="computer_lab",
        count=40,
        rated_kw=0.180,
        hours_per_day=12.0,
        tier=3,
        duty_cycle=0.85,
        notes="[ASSUMPTION] Student workstations",
    )
    assert item.total_kw == pytest.approx(40 * 0.180)
    assert item.nominal_daily_kwh == pytest.approx(40 * 0.180 * 12.0)
    assert item.effective_daily_kwh == pytest.approx(40 * 0.180 * 12.0 * 0.85)
    assert not item.is_cooling


def test_equipment_item_cooling_detection():
    """Verify that cooling appliances are accurately identified by is_cooling."""
    ac_item = EquipmentItem(
        item="Inverter Split AC Units (3.0 HP)",
        room_type="computer_lab",
        count=2,
        rated_kw=2.800,
        hours_per_day=12.0,
        tier=3,
    )
    assert ac_item.is_cooling

    spot_cool = EquipmentItem(
        item="IDF Network Closets Dedicated Spot Cooling (1.0 HP)",
        room_type="building_common",
        count=2,
        rated_kw=1.200,
        hours_per_day=24.0,
        tier=2,
    )
    assert spot_cool.is_cooling


@pytest.mark.parametrize(
    "kwargs, expected_error",
    [
        ({"count": 0}, "count must be a positive integer"),
        ({"count": -5}, "count must be a positive integer"),
        ({"rated_kw": -0.1}, "rated_kw must be non-negative"),
        ({"hours_per_day": -1.0}, "hours_per_day must be in [0, 24]"),
        ({"hours_per_day": 25.0}, "hours_per_day must be in [0, 24]"),
        ({"tier": 0}, "tier must be 1, 2, or 3"),
        ({"tier": 4}, "tier must be 1, 2, or 3"),
        ({"duty_cycle": -0.1}, "duty_cycle must be in [0.0, 1.0]"),
        ({"duty_cycle": 1.5}, "duty_cycle must be in [0.0, 1.0]"),
    ],
)
def test_equipment_item_boundary_validation(kwargs, expected_error):
    """Verify that invalid equipment item attributes trigger ValueErrors."""
    valid_args = {
        "item": "Test Item",
        "room_type": "lecture_room",
        "count": 5,
        "rated_kw": 0.5,
        "hours_per_day": 8.0,
        "tier": 2,
        "duty_cycle": 0.9,
    }
    valid_args.update(kwargs)
    with pytest.raises(ValueError, match=re.escape(expected_error)):
        EquipmentItem(**valid_args)


# --- 3. CCIS Archetype Audit Ingestion & Conformance ---


def test_load_audit_from_csv():
    """Verify successful loading and parsing of the official CCIS audit CSV."""
    audit = EquipmentAudit.load_from_csv(AUDIT_CSV_PATH)
    assert len(audit.items) > 0
    assert audit.floor_area_m2 == 2500.0

    errors = audit.validate()
    assert not errors, f"Validation errors found: {errors}"


def test_all_18_rooms_archetype_covered():
    """Verify that all room archetypes from [D-06] are present in the inventory."""
    audit = EquipmentAudit.load_from_csv(AUDIT_CSV_PATH)
    summary = audit.summary_by_room_type()

    expected_rooms = {
        "computer_lab",
        "lecture_room",
        "hyflex_smart_room",
        "dean_and_secretary",
        "cod_office",
        "faculty_room",
        "building_common",
    }
    assert expected_rooms.issubset(set(summary.keys()))

    # Verify building room counts match [D-06] baseline via RoomInventory
    room_inv = RoomInventory()
    assert room_inv.hyflex_smart_rooms == 2
    assert room_inv.lecture_rooms == 6
    assert room_inv.cod_office == 1
    assert room_inv.dean_and_secretary == 1
    assert room_inv.faculty_rooms == 2
    assert room_inv.computer_labs == 6
    assert room_inv.total_rooms == 18


def test_tier_distribution_and_shedding_alignment():
    """Verify load classification conforms to [D-10] shedding hierarchy."""
    audit = EquipmentAudit.load_from_csv(AUDIT_CSV_PATH)

    tot_kw = audit.total_connected_kw()
    assert tot_kw > 100.0, f"Expected total capacity > 100 kW, got {tot_kw} kW"

    pcts = audit.tier_breakdown_pct()
    # Tier 1 (Life safety): ~1% - 2%
    assert 0.5 <= pcts[1] <= 3.0, f"Tier 1 percentage out of expected range: {pcts[1]:.2f}%"
    # Tier 2 (Essential IT/Admin): ~10% - 20%
    assert 8.0 <= pcts[2] <= 22.0, f"Tier 2 percentage out of expected range: {pcts[2]:.2f}%"
    # Tier 3 (Sheddable comfort & general labs): ~75% - 90%
    assert 75.0 <= pcts[3] <= 90.0, f"Tier 3 percentage out of expected range: {pcts[3]:.2f}%"


def test_building_dataclass_compatibility():
    """Verify compatibility and alignment with CORE-001 Building domain model."""
    building = Building()
    audit = EquipmentAudit.load_from_csv(AUDIT_CSV_PATH, floor_area_m2=building.gross_floor_area_m2)

    assert audit.floor_area_m2 == building.gross_floor_area_m2
    assert building.gross_floor_area_m2 == 2500.0
    assert audit.total_connected_kw() > 0.0


def test_load_nonexistent_file_raises():
    """Verify loading a nonexistent CSV file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        EquipmentAudit.load_from_csv("data/fixtures/non_existent_file.csv")
