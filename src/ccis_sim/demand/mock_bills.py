"""Synthetic monthly electricity bill generator calibrated against CCIS equipment audit.

Conforms to specifications locked in:
- docs/prompts/CORE-003-PROMPT.md
- docs/context/complete-context.md §3 (Public & synthetic data only, clearly labelled)
- docs/decisions/decision-log.md [D-03] (Zero institutional data requests)
- docs/decisions/decision-log.md [D-10] (Tiers 1, 2, 3 load shedding classification)
- docs/decisions/decision-log.md [D-16] (CCIS equipment audit & synthetic billing calibration)
"""

from __future__ import annotations

import calendar
import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from ccis_sim.demand.equipment import EquipmentAudit


# Standard higher-education academic operational calendar weights for Philippine State Universities (MMSU):
DEFAULT_ACADEMIC_WEIGHTS: dict[int, float] = {
    1: 0.90,   # January: Second semester resumption (~early Jan)
    2: 1.00,   # February: Full semester academic operations
    3: 1.00,   # March: Full semester academic operations (hot season onset)
    4: 1.00,   # April: Full semester academic operations (peak summer heat)
    5: 0.90,   # May: Final examinations and commencement activities
    6: 0.65,   # June: Midyear / summer classes and faculty research
    7: 0.65,   # July: Midyear / summer classes and departmental maintenance
    8: 0.90,   # August: Enrollment, freshmen orientation, semester opening
    9: 1.00,   # September: Full first semester academic operations
    10: 1.00,  # October: Full first semester academic operations (midterms)
    11: 1.00,  # November: Full first semester academic operations
    12: 0.80,  # December: Semestral conclusion and holiday break
}

# Empirical monthly cooling multipliers reflecting Batac, Ilocos Norte Type I tropical climate:
DEFAULT_COOLING_MULTIPLIERS: dict[int, float] = {
    1: 0.88,   # January: Amihan cool dry period
    2: 0.95,   # February: Rising daytime insolation
    3: 1.18,   # March: Dry summer onset, intense thermal load
    4: 1.25,   # April: Peak extreme heat in Ilocos Norte (>36°C)
    5: 1.20,   # May: Severe heat index, early convective rains
    6: 1.05,   # June: Southwest monsoon onset, high humidity
    7: 1.00,   # July: Rainy monsoon season, moderated dry-bulb
    8: 0.98,   # August: Peak tropical cyclone & rainfall period
    9: 1.00,   # September: Monsoon transition
    10: 0.98,  # October: Post-monsoon clearing
    11: 0.92,  # November: Amihan cool air masses begin
    12: 0.85,  # December: Coolest dry month
}


@dataclass(frozen=True)
class SyntheticMonthlyBill:
    """Synthetic monthly electricity bill record clearly marked as mock data.

    This record represents a calibrated mock utility bill for the MMSU CCIS
    facility, used strictly for model calibration and validation in the absence
    of institutional utility bills per decision [D-03].
    """

    month: int
    month_name: str
    billing_period_start: str
    billing_period_end: str
    days: int
    weekdays: int
    weekends: int
    total_kwh: float
    peak_kw: float
    tier1_kwh: float
    tier2_kwh: float
    tier3_kwh: float
    eui_kwh_per_m2: float
    academic_factor: float
    cooling_multiplier: float
    is_synthetic: bool = True
    data_origin: str = "SYNTHETIC_MOCK_CALIBRATED_AUDIT"
    notes: str = ""

    def __post_init__(self) -> None:
        if self.month < 1 or self.month > 12:
            raise ValueError(f"month must be 1..12, got {self.month}")
        if self.total_kwh < 0.0:
            raise ValueError(f"total_kwh must be non-negative, got {self.total_kwh}")
        if self.peak_kw < 0.0:
            raise ValueError(f"peak_kw must be non-negative, got {self.peak_kw}")
        if not self.is_synthetic:
            raise ValueError("is_synthetic must remain True to prevent confusion with real data.")

    def to_dict(self) -> dict[str, Any]:
        """Convert bill to a dictionary."""
        return asdict(self)


class SyntheticBillGenerator:
    """Generates 12 monthly synthetic electricity bills calibrated against an equipment audit.

    Incorporates academic calendar weighting, seasonal cooling degree multipliers,
    load tier separation, unoccupied nighttime baseload (DEM-001.3), and realistic meter measurement noise.
    """

    def __init__(
        self,
        audit: EquipmentAudit,
        floor_area_m2: float = 2500.0,
        seed: int | None = 42,
        academic_weights: dict[int, float] | None = None,
        cooling_multipliers: dict[int, float] | None = None,
        standby_power_kw: float = 8.0,
    ) -> None:
        self.audit = audit
        self.floor_area_m2 = floor_area_m2 if floor_area_m2 > 0 else audit.floor_area_m2
        self.seed = seed
        self.academic_weights = academic_weights or DEFAULT_ACADEMIC_WEIGHTS.copy()
        self.cooling_multipliers = cooling_multipliers or DEFAULT_COOLING_MULTIPLIERS.copy()
        self.standby_power_kw = standby_power_kw

    def generate_annual_bills(
        self,
        year: int = 2026,
        noise_std: float = 0.025,
    ) -> list[SyntheticMonthlyBill]:
        """Generate 12 monthly synthetic bills for the specified calendar year.

        Args:
            year: Calendar year (default 2026).
            noise_std: Relative standard deviation of Gaussian meter noise (default 2.5%).

        Returns:
            List of 12 SyntheticMonthlyBill records.
        """
        rng = np.random.default_rng(self.seed)
        df = self.audit.to_dataframe()

        # Separate items by tier and cooling attribute:
        t1_items = df[df["tier"] == 1]
        t2_247 = df[(df["tier"] == 2) & (df["hours_per_day"] == 24.0)]
        t2_active = df[(df["tier"] == 2) & (df["hours_per_day"] < 24.0)]
        t3_cool = df[(df["tier"] == 3) & (df["is_cooling"])]
        t3_noncool = df[(df["tier"] == 3) & (~df["is_cooling"])]

        # Base daily energy rates:
        t1_daily_base = (t1_items["total_kw"] * 24.0 * t1_items["duty_cycle"]).sum()
        t2_247_daily = (t2_247["total_kw"] * 24.0 * t2_247["duty_cycle"]).sum()

        bills: list[SyntheticMonthlyBill] = []

        for m in range(1, 13):
            num_days = calendar.monthrange(year, m)[1]
            weekdays = sum(1 for d in range(1, num_days + 1) if calendar.weekday(year, m, d) < 5)
            saturdays = sum(1 for d in range(1, num_days + 1) if calendar.weekday(year, m, d) == 5)
            sundays = num_days - weekdays - saturdays
            weekends = saturdays + sundays

            acad = self.academic_weights.get(m, 1.0)
            cool = self.cooling_multipliers.get(m, 1.0)

            # Apply pseudo-random noise factor to simulate billing meter variability:
            noise = float(rng.normal(1.0, noise_std)) if noise_std > 0 else 1.0

            # Tier 1 (constant 24/7/365 life safety & core monitoring):
            t1_month = t1_daily_base * num_days * noise

            # Tier 2 (essential IT and telecom):
            # Weekday: 24/7 loads + active office hours scaled by academic factor
            t2_weekday = t2_247_daily + (
                t2_active["total_kw"] * t2_active["hours_per_day"] * t2_active["duty_cycle"] * acad
            ).sum()
            # Saturday: 24/7 loads + reduced graduate/capstone office access (40%)
            t2_saturday = t2_247_daily + (
                t2_active["total_kw"] * 8.0 * t2_active["duty_cycle"] * acad * 0.40
            ).sum()
            # Sunday: 24/7 baseline only
            t2_sunday = t2_247_daily
            t2_month = (weekdays * t2_weekday + saturdays * t2_saturday + sundays * t2_sunday) * noise

            # Tier 3 (comfort cooling & high-density student lab loads):
            # Weekday: active daytime hours (cooling scaled by cool * acad, non-cooling by acad)
            # plus 12 hours of nighttime standby baseload per DEM-001.3
            t3_weekday = (
                t3_cool["total_kw"] * t3_cool["hours_per_day"] * t3_cool["duty_cycle"] * cool * acad
            ).sum() + (
                t3_noncool["total_kw"] * t3_noncool["hours_per_day"] * t3_noncool["duty_cycle"] * acad
            ).sum() + (self.standby_power_kw * 12.0)

            # Saturday: partial lab utilization (~45% student, ~40% AC) + 16h nighttime standby
            t3_saturday = (
                t3_cool["total_kw"] * 8.0 * t3_cool["duty_cycle"] * cool * acad * 0.40
            ).sum() + (
                t3_noncool["total_kw"] * 8.0 * t3_noncool["duty_cycle"] * acad * 0.45
            ).sum() + (self.standby_power_kw * 16.0)

            # Sunday: unoccupied facility standby load (24h)
            t3_sunday = self.standby_power_kw * 24.0
            t3_month = (weekdays * t3_weekday + saturdays * t3_saturday + sundays * t3_sunday) * noise

            total_kwh = t1_month + t2_month + t3_month

            # Estimated coincident peak demand in kW:
            peak_t1 = t1_items["total_kw"].sum()
            peak_t2 = t2_247["total_kw"].sum() + (t2_active["total_kw"].sum() * acad * 0.85)
            peak_t3 = (
                (t3_cool["total_kw"].sum() * cool * 0.80) + (t3_noncool["total_kw"].sum() * 0.82)
            ) * acad
            coincident_peak_kw = (peak_t1 + peak_t2 + peak_t3) * noise

            eui_mo = total_kwh / self.floor_area_m2
            start_date = f"{year}-{m:02d}-01"
            end_date = f"{year}-{m:02d}-{num_days:02d}"

            notes = (
                f"Synthetic mock bill for {calendar.month_name[m]} {year}; "
                f"acad_factor={acad:.2f}, cool_mult={cool:.2f}"
            )

            bills.append(
                SyntheticMonthlyBill(
                    month=m,
                    month_name=calendar.month_name[m],
                    billing_period_start=start_date,
                    billing_period_end=end_date,
                    days=num_days,
                    weekdays=weekdays,
                    weekends=weekends,
                    total_kwh=round(total_kwh, 2),
                    peak_kw=round(coincident_peak_kw, 2),
                    tier1_kwh=round(t1_month, 2),
                    tier2_kwh=round(t2_month, 2),
                    tier3_kwh=round(t3_month, 2),
                    eui_kwh_per_m2=round(eui_mo, 2),
                    academic_factor=acad,
                    cooling_multiplier=cool,
                    is_synthetic=True,
                    data_origin="SYNTHETIC_MOCK_CALIBRATED_AUDIT",
                    notes=notes,
                )
            )

        return bills

    def compute_annual_eui(self, bills: Sequence[SyntheticMonthlyBill]) -> float:
        """Compute the annual Energy Use Intensity (kWh/m²·yr) from a 12-month bill set."""
        if len(bills) != 12:
            raise ValueError(f"Expected 12 monthly bills, got {len(bills)}")
        total_annual_kwh = sum(b.total_kwh for b in bills)
        return total_annual_kwh / self.floor_area_m2

    @staticmethod
    def to_dataframe(bills: Sequence[SyntheticMonthlyBill]) -> pd.DataFrame:
        """Convert a sequence of SyntheticMonthlyBill records to a pandas DataFrame."""
        return pd.DataFrame([b.to_dict() for b in bills])

    def save_to_csv(self, bills: Sequence[SyntheticMonthlyBill], output_path: Path | str) -> Path:
        """Save synthetic monthly bills to CSV with explicit mock provenance metadata."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df = self.to_dataframe(bills)
        df.to_csv(path, index=False)
        return path

    @staticmethod
    def load_from_csv(csv_path: Path | str) -> list[SyntheticMonthlyBill]:
        """Load and parse previously saved synthetic monthly bills from CSV."""
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Synthetic bills file not found: {path}")

        bills: list[SyntheticMonthlyBill] = []
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                bill = SyntheticMonthlyBill(
                    month=int(row["month"]),
                    month_name=row["month_name"].strip(),
                    billing_period_start=row["billing_period_start"].strip(),
                    billing_period_end=row["billing_period_end"].strip(),
                    days=int(row["days"]),
                    weekdays=int(row["weekdays"]),
                    weekends=int(row["weekends"]),
                    total_kwh=float(row["total_kwh"]),
                    peak_kw=float(row["peak_kw"]),
                    tier1_kwh=float(row["tier1_kwh"]),
                    tier2_kwh=float(row["tier2_kwh"]),
                    tier3_kwh=float(row["tier3_kwh"]),
                    eui_kwh_per_m2=float(row["eui_kwh_per_m2"]),
                    academic_factor=float(row["academic_factor"]),
                    cooling_multiplier=float(row["cooling_multiplier"]),
                    is_synthetic=row["is_synthetic"].lower() in ("true", "1"),
                    data_origin=row["data_origin"].strip(),
                    notes=row.get("notes", "").strip(),
                )
                bills.append(bill)
        return bills
