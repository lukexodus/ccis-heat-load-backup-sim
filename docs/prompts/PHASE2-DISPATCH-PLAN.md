# Phase 2 Dispatch Plan

## Order
1. **CORE-006** first, alone. Review, merge to `master`, regenerate the bundle.
2. Then dispatch the eight tracks in parallel from the new `master` tip. Each prompt checks that `interfaces.py` exists and stops if CORE-006 has not landed.
3. After all eight merge, dispatch the two deferred validation tasks and then Phase 3 (INT-001).

## Reserved decision IDs (next free ID at writing: D-26)
| Task | ID | Task | ID |
| :-- | :-- | :-- | :-- |
| CORE-006 | D-26 | SOL-002 | D-30 |
| DEM-001 | D-27 | BAT-001 | D-31 |
| DEM-002 | D-28 | BAT-002 | D-32 |
| SOL-001 | D-29 | OUT-001 | D-33 |
| | | OUT-002 | D-34 |

Unused reservations: record a one-line "reserved, unused" entry at merge so the log has no silent gaps. Merging eight branches will conflict in `decision-log.md` and `status.md` (all append at the same place): resolve by keeping every entry, in ID order. Never renumber an ID after a track is dispatched (the D-22 collision came from reserving against a stale view of `master`).

## Dependencies and deliberately deferred subtasks
- **DEM-002.4** (validate combined demand against mock bills): needs DEM-001 and DEM-002 merged. Left `open`.
- **SOL-002.4** (annual yield vs 1,298 kWh/kWp): needs SOL-001 and SOL-002 merged; this is where the assumed thermal factor in SOL-002 gets recalibrated. Left `open`.
- Both become small `*-VERIFY` prompts after merge.
- BAT-002 depends on CORE-006 only (idle-loss allowance in the harness), not on BAT-001; its tests use a local reference loop.

## Points for APC/operator confirmation before dispatch
1. **Typhoon solar depression wording** ([D-11]): "20–30% GHI" is implemented as GHI = 20–30% of normal. If you meant a 20–30% *reduction*, edit OUT-001 before dispatch.
2. **Tare loss** is modelled as a SoC-side loss (CORE-006 / [D-26]) so AC-side energy balance is unchanged. Say so if you want it AC-side instead.
3. **BAT-002 floor semantics**: operational floor is `min_soc + emergency_reserve` while the grid is up, released to `min_soc` in an outage, and 0 under emergency drawdown. The harness hard floor stays `min_soc`.
4. **20% Tier 2 shed threshold** (OUT-002) is kept separate from `emergency_reserve_pct`; INT-001 decides whether to link them.
5. **PR double counting**: SOL-001 applies thermal derate explicitly; SOL-002 budgets the rest of PR = 0.77 against an assumed mean thermal factor, to be recalibrated in SOL-002.4.
6. **Tier split**: D-10 says 2/18/80, the audit gives ≈1.5/17/81 ([D-16]/[D-19]). OUT-002 reports the difference rather than forcing it.

## Prompt hygiene lessons built in
Verbatim `pytest` output (the CORE-004.5 report's excerpt was not from this repo); report must list every touched file; no amending `master`; patches are gitignored; stop-and-report on state mismatch; one decision ID per task, reserved up front.
