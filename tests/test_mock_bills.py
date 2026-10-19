"""Unit and integration test suite for synthetic mock electricity bills and EUI validation."""

from pathlib import Path
import pytest

from ccis_sim.demand import EquipmentAudit, SyntheticBillGenerator, SyntheticMonthlyBill

FIXTURES_DIR = Path(__file__).parent.parent / "data" / "fixtures"
AUDIT_CSV_PATH = FIXTURES_DIR / "equipment-audit-ccis.csv"
MOCK_BILLS_CSV_PATH = FIXTURES_DIR / "synthetic-mock-bills-ccis.csv"


@pytest.fixture
def ccis_audit() -> EquipmentAudit:
    """Load canonical CCIS 18-room equipment audit fixture."""
    return EquipmentAudit.load_from_csv(AUDIT_CSV_PATH)


@pytest.fixture
def bill_generator(ccis_audit: EquipmentAudit) -> SyntheticBillGenerator:
    """Instantiate standard synthetic bill generator for CCIS."""
    return SyntheticBillGenerator(audit=ccis_audit, floor_area_m2=2500.0, seed=42)


# --- 1. Generation Structure & Synthetic Provenance ---


def test_generate_12_monthly_bills(bill_generator: SyntheticBillGenerator):
    """Verify that generator produces exactly 12 chronological monthly bills."""
    bills = bill_generator.generate_annual_bills(year=2026, noise_std=0.025)
    assert len(bills) == 12

    for idx, bill in enumerate(bills, start=1):
        assert bill.month == idx
        assert bill.is_synthetic is True
        assert bill.data_origin == "SYNTHETIC_MOCK_CALIBRATED_AUDIT"
        assert bill.total_kwh > 0.0
        assert bill.peak_kw > 0.0


def test_mock_bill_internal_energy_conservation(bill_generator: SyntheticBillGenerator):
    """Verify each monthly bill satisfies total_kwh = tier1 + tier2 + tier3."""
    bills = bill_generator.generate_annual_bills(year=2026, noise_std=0.025)
    for bill in bills:
        tier_sum = bill.tier1_kwh + bill.tier2_kwh + bill.tier3_kwh
        assert abs(bill.total_kwh - tier_sum) <= 0.05, (
            f"Month {bill.month} total {bill.total_kwh} differs from sum of tiers {tier_sum}"
        )


# --- 2. Regional EUI Benchmark Automated Verification ---


def test_annual_eui_benchmark_conformance(bill_generator: SyntheticBillGenerator):
    """Verify implied annual EUI strictly falls within the regional benchmark band [150, 300] kWh/m²·yr.

    Mandated by CORE-003.4 and docs/prompts/CORE-003-PROMPT.md.
    """
    bills = bill_generator.generate_annual_bills(year=2026, noise_std=0.025)
    annual_eui = bill_generator.compute_annual_eui(bills)
    total_kwh = sum(b.total_kwh for b in bills)

    # Assert within locked regional benchmark band:
    assert 150.0 <= annual_eui <= 300.0, (
        f"Annual EUI of {annual_eui:.2f} kWh/m²·yr is outside required benchmark [150, 300]. "
        f"Total annual consumption: {total_kwh:,.2f} kWh across 2,500 m²."
    )


def test_committed_fixture_eui_plausibility():
    """Verify the committed synthetic-mock-bills-ccis.csv fixture satisfies the EUI benchmark."""
    assert MOCK_BILLS_CSV_PATH.exists(), f"Committed fixture missing: {MOCK_BILLS_CSV_PATH}"
    bills = SyntheticBillGenerator.load_from_csv(MOCK_BILLS_CSV_PATH)
    assert len(bills) == 12

    total_kwh = sum(b.total_kwh for b in bills)
    annual_eui = total_kwh / 2500.0

    assert 150.0 <= annual_eui <= 300.0, (
        f"Committed fixture EUI {annual_eui:.2f} kWh/m²·yr falls outside [150, 300]"
    )


# --- 3. Seasonal & Academic Schedule Response ---


def test_hot_season_cooling_elevation(bill_generator: SyntheticBillGenerator):
    """Verify peak summer months (April/May) exhibit higher demand than cool dry months (January)."""
    bills = bill_generator.generate_annual_bills(year=2026, noise_std=0.0)
    bill_jan = bills[0]   # Month 1: cool dry (Amihan)
    bill_apr = bills[3]   # Month 4: peak summer heat in Batac

    # April should have significantly higher total consumption and peak demand
    assert bill_apr.total_kwh > bill_jan.total_kwh * 1.15
    assert bill_apr.peak_kw > bill_jan.peak_kw * 1.15
    assert bill_apr.tier3_kwh > bill_jan.tier3_kwh * 1.20


def test_academic_break_reduction(bill_generator: SyntheticBillGenerator):
    """Verify summer term months (June/July) have lower demand than regular semester months (September/October)."""
    bills = bill_generator.generate_annual_bills(year=2026, noise_std=0.0)
    bill_jun = bills[5]   # Month 6: midyear / summer break
    bill_sep = bills[8]   # Month 9: full first semester

    assert bill_jun.total_kwh < bill_sep.total_kwh * 0.80
    assert bill_jun.peak_kw < bill_sep.peak_kw * 0.80


# --- 4. Serialization & Determinism ---


def test_csv_save_and_load_roundtrip(bill_generator: SyntheticBillGenerator, tmp_path: Path):
    """Verify synthetic bills CSV export and reload preserve all numerical values and metadata."""
    bills = bill_generator.generate_annual_bills(year=2026, noise_std=0.02)
    temp_csv = tmp_path / "test_mock_bills.csv"

    bill_generator.save_to_csv(bills, temp_csv)
    loaded_bills = SyntheticBillGenerator.load_from_csv(temp_csv)

    assert len(loaded_bills) == 12
    for orig, loaded in zip(bills, loaded_bills):
        assert orig.month == loaded.month
        assert orig.month_name == loaded.month_name
        assert orig.days == loaded.days
        assert orig.total_kwh == pytest.approx(loaded.total_kwh)
        assert orig.peak_kw == pytest.approx(loaded.peak_kw)
        assert orig.tier1_kwh == pytest.approx(loaded.tier1_kwh)
        assert orig.tier2_kwh == pytest.approx(loaded.tier2_kwh)
        assert orig.tier3_kwh == pytest.approx(loaded.tier3_kwh)
        assert orig.is_synthetic is True
        assert loaded.data_origin == "SYNTHETIC_MOCK_CALIBRATED_AUDIT"


def test_generator_seed_reproducibility(bill_generator: SyntheticBillGenerator, ccis_audit: EquipmentAudit):
    """Verify bill generation is deterministic with fixed random seed."""
    bills_a = bill_generator.generate_annual_bills(year=2026, noise_std=0.03)

    gen_b = SyntheticBillGenerator(audit=ccis_audit, floor_area_m2=2500.0, seed=42)
    bills_b = gen_b.generate_annual_bills(year=2026, noise_std=0.03)

    for a, b in zip(bills_a, bills_b):
        assert a.total_kwh == pytest.approx(b.total_kwh)
        assert a.peak_kw == pytest.approx(b.peak_kw)
