"""Analytic Hierarchy Process (AHP) multi-criteria weighting engine (DEC-001).

Implements Saaty's eigenvalue method, consistency checking (CR <= 0.10),
and candidate scoring across microgrid sizing alternatives.
"""

from __future__ import annotations

from typing import Sequence
import numpy as np
import pandas as pd

# Saaty Random Index (RI) table for matrix sizes n = 1..10
SAATY_RI: dict[int, float] = {
    1: 0.0,
    2: 0.0,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}

CRITERIA_NAMES: list[str] = [
    "Reliability",
    "Cost",
    "Self-sufficiency",
    "Curtailment",
]


def ahp_weights(
    matrix: np.ndarray | Sequence[Sequence[float]],
) -> tuple[np.ndarray, float, float, float]:
    """Calculate priority weight vector and consistency ratio via principal eigenvector method.

    Parameters
    ----------
    matrix : np.ndarray | Sequence[Sequence[float]]
        Positive reciprocal pairwise comparison matrix of size (n, n).

    Returns
    -------
    tuple[np.ndarray, float, float, float]
        (weights, lambda_max, CI, CR):
        - weights: 1D numpy array of normalized priority weights summing to 1.0.
        - lambda_max: Principal eigenvalue (scalar float).
        - CI: Consistency Index = (lambda_max - n) / (n - 1).
        - CR: Consistency Ratio = CI / RI[n].

    Raises
    ------
    ValueError
        If matrix is not square, not positive, or if CR > 0.10.
    """
    A = np.asarray(matrix, dtype=np.float64)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError(f"Pairwise comparison matrix must be square (n, n), got shape {A.shape}")

    n = A.shape[0]
    if n == 0:
        raise ValueError("Matrix cannot be empty.")
    if np.any(A <= 0.0):
        raise ValueError("All entries in pairwise comparison matrix must be strictly positive.")

    if n == 1:
        return np.array([1.0], dtype=np.float64), 1.0, 0.0, 0.0

    # Compute eigenvalues and right eigenvectors
    eigvals, eigvecs = np.linalg.eig(A)

    # Find principal eigenvalue (largest real component)
    max_idx = int(np.argmax(np.real(eigvals)))
    lambda_max = float(np.real(eigvals[max_idx]))

    # Extract corresponding principal eigenvector
    principal_vec = np.real(eigvecs[:, max_idx])

    # Ensure all components have positive sign
    if np.all(principal_vec < 0.0):
        principal_vec = -principal_vec
    elif np.any(principal_vec < 0.0):
        # In case of small numerical rounding near zero
        principal_vec = np.abs(principal_vec)

    total_sum = float(np.sum(principal_vec))
    if total_sum <= 0.0:
        raise ValueError("Principal eigenvector elements sum to non-positive value.")

    weights = principal_vec / total_sum

    # Consistency Index (CI)
    ci = (lambda_max - n) / (n - 1)
    if abs(ci) < 1e-12:
        ci = 0.0

    # Consistency Ratio (CR)
    ri = SAATY_RI.get(n, 1.49)
    cr = (ci / ri) if ri > 0.0 else 0.0

    # Saaty consistency threshold check
    if cr > 0.10:
        raise ValueError(
            f"AHP Consistency Ratio {cr:.4f} exceeds allowable threshold (CR <= 0.10). "
            f"Matrix is inconsistent (lambda_max={lambda_max:.4f}, CI={ci:.4f})."
        )

    return weights, lambda_max, ci, cr


def get_base_pairwise_matrix() -> np.ndarray:
    """Construct the baseline 4x4 pairwise comparison matrix per task specification [D-38].

    Criteria order:
    1. Reliability (Tier 1+2 outage coverage in typhoon regime)
    2. Cost Index
    3. Self-sufficiency
    4. Curtailment (lower is better)

    Pairwise judgments:
    - Reliability vs Cost = 3
    - Reliability vs Self-sufficiency = 5
    - Reliability vs Curtailment = 7
    - Cost vs Self-sufficiency = 2
    - Cost vs Curtailment = 3
    - Self-sufficiency vs Curtailment = 2
    """
    matrix = np.array(
        [
            [1.0, 3.0, 5.0, 7.0],
            [1.0 / 3.0, 1.0, 2.0, 3.0],
            [1.0 / 5.0, 1.0 / 2.0, 1.0, 2.0],
            [1.0 / 7.0, 1.0 / 3.0, 1.0 / 2.0, 1.0],
        ],
        dtype=np.float64,
    )
    return matrix


def get_ahp_weight_sets() -> dict[str, np.ndarray]:
    """Return dictionary of the 3 canonical AHP weight profiles evaluated in DEC-001/002."""
    base_matrix = get_base_pairwise_matrix()
    base_w, _, _, _ = ahp_weights(base_matrix)

    equal_w = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)
    reliability_heavy_w = np.array([0.60, 0.20, 0.10, 0.10], dtype=np.float64)

    return {
        "base": base_w,
        "equal": equal_w,
        "reliability_heavy": reliability_heavy_w,
    }


def compute_cost_index(
    solar_kwp: float | np.ndarray,
    battery_kwh: float | np.ndarray,
    r: float = 0.6,
) -> float | np.ndarray:
    """Calculate relative system cost index per [D-38].

    Cost = solar_kwp * 1.0 + battery_kwh * r
    where r is the relative unit capacity cost assumption of storage vs solar PV.

    Parameters
    ----------
    solar_kwp : float | np.ndarray
        Installed solar capacity in kWp.
    battery_kwh : float | np.ndarray
        Installed battery capacity in kWh.
    r : float, optional
        Relative unit cost factor (default: 0.6, sensitivity {0.3, 1.0}).
    """
    return solar_kwp * 1.0 + battery_kwh * r


def score_candidates(
    candidates_df: pd.DataFrame,
    weights: np.ndarray | Sequence[float],
    r: float = 0.6,
) -> pd.DataFrame:
    """Score and rank candidate sizings using min-max normalized multi-criteria synthesis.

    Criteria directions:
    - Reliability (fraction of outage hours T1+2 served): MAXIMIZE
    - Cost Index: MINIMIZE
    - Self-sufficiency: MAXIMIZE
    - Curtailment (kWh): MINIMIZE

    Parameters
    ----------
    candidates_df : pd.DataFrame
        DataFrame containing candidate performance metrics with columns:
        'solar_kwp', 'battery_kwh', 'typhoon_t1_2_served_pct', 'self_sufficiency_mean', 'curtailed_mean'.
    weights : np.ndarray | Sequence[float]
        4-element vector of criterion weights summing to 1.0.
    r : float, optional
        Relative cost parameter (default: 0.6).

    Returns
    -------
    pd.DataFrame
        Sorted DataFrame with normalized criterion scores, composite 'ahp_score', and 'ahp_rank'.
    """
    df = candidates_df.copy()
    w = np.asarray(weights, dtype=np.float64)
    if len(w) != 4:
        raise ValueError(f"Weights must have length 4, got {len(w)}")

    # 1. Compute Cost Index if not already present
    if "cost_index" not in df.columns:
        df["cost_index"] = compute_cost_index(df["solar_kwp"], df["battery_kwh"], r=r)

    # 2. Extract raw criteria
    # Reliability: outage hours served fraction (0.0 to 1.0)
    if "reliability" in df.columns:
        rel = df["reliability"].to_numpy(dtype=np.float64)
    elif "typhoon_t1_2_served_pct" in df.columns:
        rel = df["typhoon_t1_2_served_pct"].to_numpy(dtype=np.float64) / 100.0
    else:
        raise KeyError("Candidates DataFrame must include 'reliability' or 'typhoon_t1_2_served_pct'")

    cost = df["cost_index"].to_numpy(dtype=np.float64)

    if "self_sufficiency" in df.columns:
        ss = df["self_sufficiency"].to_numpy(dtype=np.float64)
    elif "self_sufficiency_mean" in df.columns:
        ss = df["self_sufficiency_mean"].to_numpy(dtype=np.float64)
    else:
        raise KeyError("Candidates DataFrame must include 'self_sufficiency' or 'self_sufficiency_mean'")

    if "curtailment" in df.columns:
        curt = df["curtailment"].to_numpy(dtype=np.float64)
    elif "curtailed_mean" in df.columns:
        curt = df["curtailed_mean"].to_numpy(dtype=np.float64)
    else:
        raise KeyError("Candidates DataFrame must include 'curtailment' or 'curtailed_mean'")

    def _norm_benefit(val: np.ndarray) -> np.ndarray:
        v_min, v_max = float(np.min(val)), float(np.max(val))
        if abs(v_max - v_min) < 1e-12:
            return np.ones_like(val)
        return (val - v_min) / (v_max - v_min)

    def _norm_cost(val: np.ndarray) -> np.ndarray:
        v_min, v_max = float(np.min(val)), float(np.max(val))
        if abs(v_max - v_min) < 1e-12:
            return np.ones_like(val)
        return (v_max - val) / (v_max - v_min)

    norm_rel = _norm_benefit(rel)
    norm_cost = _norm_cost(cost)
    norm_ss = _norm_benefit(ss)
    norm_curt = _norm_cost(curt)

    df["norm_reliability"] = norm_rel
    df["norm_cost"] = norm_cost
    df["norm_self_sufficiency"] = norm_ss
    df["norm_curtailment"] = norm_curt

    # Composite weighted score
    ahp_score = (
        w[0] * norm_rel
        + w[1] * norm_cost
        + w[2] * norm_ss
        + w[3] * norm_curt
    )
    df["ahp_score"] = ahp_score

    # Rank descending by score (with unserved T1+2 kWh as tie-breaker if available)
    sort_cols = ["ahp_score"]
    ascending_flags = [False]
    if "unserved_t1_2_mean" in df.columns:
        sort_cols.append("unserved_t1_2_mean")
        ascending_flags.append(True)

    df = df.sort_values(by=sort_cols, ascending=ascending_flags).reset_index(drop=True)
    df["ahp_rank"] = np.arange(1, len(df) + 1)

    return df
