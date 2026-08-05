"""Input contract validator for the Justified P/E V2.2.1 engine.

Implements, verbatim, the input-domain contract of:
  references/K3_Regression_Tests_v2.2.1.json  -> "input_contract"
  references/Justified_PE_AI_Manual_v2.2.1.md -> section 11.11

Classification vocabulary (a single input vector can carry several labels;
INVALID is the only one that blocks computation):

  INVALID                                  -> engine must NOT run until corrected
  SUPPORTED_BOUNDARY                       -> canonical K3 runs (exact limit branches where applicable)
  SUPPORTED_VIA_COMPANION_IMPLEMENTATION   -> run only through the P/B companion / A2_cancelled path
  REVIEW                                   -> mathematically supported; run only with documented rationale

The 16 canonical inputs (exactly these; nothing else enters the formula):
  ROE1, ROE2, g1, g2, Ke1, Ke2, n1, n2, NDE1, NDE2, GDE1, GDE2, F, g_T, Kd_F2, t

NI0 / Book0 are valuation scales, not additional economic inputs; they are
validated here only for scale-singularity classification.

The frozen V2.2.1 methodology defines every INVALID / SUPPORTED / COMPANION
condition. This validator auto-flags ONLY conditions the canonical sources
state explicitly (exact domains, `t<0 or t>1`, `Kd_F2<0`, `Ke<=Kd_F2`,
`GDE-NDE>1`, the `1e-12<=|Ke-g|<1e-6` stability zone). Qualitative REVIEW
categories the sources name WITHOUT numbers — "economically extreme" returns/
growth/leverage, NDE "near" -1 rebasing, "material"/"long"/"high" judgments —
carry no universal numeric cutoff in V2.2.1 and are therefore DELEGATED to the
analyst layer: the implementation must not invent thresholds and present them
as methodology rules (implementation patch 1.1.0).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

CANONICAL_INPUTS = (
    "ROE1", "ROE2", "g1", "g2", "Ke1", "Ke2", "n1", "n2",
    "NDE1", "NDE2", "GDE1", "GDE2", "F", "g_T", "Kd_F2", "t",
)

# Numerical-stability contract (MATHEMATICAL INVARIANT — do not change).
LIMIT_EPS = 1e-12          # |Ke-g| below this -> exact finite limit branch
ILL_CONDITION_EPS = 1e-6   # 1e-12 <= |Ke-g| < 1e-6 -> REVIEW zone


@dataclass
class ValidationReport:
    """Full classification of one 16-input vector (plus optional scale)."""
    status: str = "VALID"  # INVALID | SUPPORTED_VIA_COMPANION_IMPLEMENTATION | REVIEW | SUPPORTED_BOUNDARY | VALID
    invalid: list = field(default_factory=list)
    boundaries: list = field(default_factory=list)
    companion: list = field(default_factory=list)
    review: list = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.invalid

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "is_computable": self.is_valid,
            "invalid": list(self.invalid),
            "boundaries": list(self.boundaries),
            "companion": list(self.companion),
            "review": list(self.review),
        }


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _is_integer_valued(x) -> bool:
    return _finite(x) and float(x).is_integer()


def fade_growth_path(g2: float, g_T: float, F: int):
    """[FF] g_k = g2 + (g_T - g2) * k / F for k = 1..F (empty when F = 0)."""
    F = int(F)
    return [g2 + (g_T - g2) * k / F for k in range(1, F + 1)]


def validate_inputs(inputs: dict, NI0=None, Book0=None) -> ValidationReport:
    """Classify one canonical input vector against the V2.2.1 input contract.

    `inputs` must contain exactly the 16 canonical keys. NI0/Book0 are optional
    valuation scales used only for scale-singularity classification.
    """
    rep = ValidationReport()

    missing = [k for k in CANONICAL_INPUTS if k not in inputs]
    if missing:
        rep.invalid.append(f"INVALID INPUT — missing canonical inputs: {', '.join(missing)}.")
        rep.status = "INVALID"
        return rep
    unknown = [k for k in inputs if k not in CANONICAL_INPUTS]
    if unknown:
        rep.invalid.append(
            "INVALID INPUT — unknown keys (only the 16 canonical inputs enter K3): "
            + ", ".join(sorted(unknown)) + "."
        )

    # ---------------- INVALID (blocking) ----------------
    non_finite = [k for k in CANONICAL_INPUTS if not _finite(inputs[k])]
    if non_finite:
        rep.invalid.append("INVALID INPUT — all inputs must be finite. Offending: " + ", ".join(non_finite) + ".")
        rep.status = "INVALID"
        return rep  # nothing else can be evaluated safely

    ROE1, ROE2 = inputs["ROE1"], inputs["ROE2"]
    g1, g2 = inputs["g1"], inputs["g2"]
    Ke1, Ke2 = inputs["Ke1"], inputs["Ke2"]
    n1, n2, F = inputs["n1"], inputs["n2"], inputs["F"]
    NDE1, NDE2 = inputs["NDE1"], inputs["NDE2"]
    GDE1, GDE2 = inputs["GDE1"], inputs["GDE2"]
    g_T, Kd_F2, t = inputs["g_T"], inputs["Kd_F2"], inputs["t"]

    if any(_finite(v) and v < 0 for v in (n1, n2, F)):
        rep.invalid.append("INVALID INPUT — n1, n2 and F must be non-negative integers.")
    if not all(_is_integer_valued(v) for v in (n1, n2, F)):
        rep.invalid.append("INVALID INPUT — n1, n2 and F must be integers.")
    if Ke1 <= -1:
        rep.invalid.append("INVALID INPUT — Ke1 must be greater than -1.")
    if Ke2 <= -1:
        rep.invalid.append("INVALID INPUT — Ke2 must be greater than -1.")
    if g1 <= -1:
        rep.invalid.append("INVALID INPUT — g1 must be greater than -1.")
    if g2 <= -1:
        rep.invalid.append("INVALID INPUT — g2 must be greater than -1.")
    if _is_integer_valued(F) and F >= 1 and g2 > -1:
        if any(gk <= -1 for gk in fade_growth_path(g2, g_T, int(F))):
            rep.invalid.append("INVALID INPUT — every fade growth point must be greater than -1.")
    if 1 + NDE2 == 0:
        rep.invalid.append("INVALID INPUT — NDE2 cannot equal -1.")
    if GDE1 < 0 or GDE2 < 0:
        rep.invalid.append("INVALID INPUT — GDE1 and GDE2 must be non-negative.")
    if GDE1 < NDE1:
        rep.invalid.append("INVALID INPUT — GDE1 must be greater than or equal to NDE1.")
    if GDE2 < NDE2:
        rep.invalid.append("INVALID INPUT — GDE2 must be greater than or equal to NDE2.")

    if rep.invalid:
        rep.status = "INVALID"
        return rep

    n1, n2, F = int(n1), int(n2), int(F)

    # ---------- SUPPORTED_VIA_COMPANION_IMPLEMENTATION ----------
    if ROE1 == 0:
        rep.companion.append(
            "SUPPORTED BOUNDARY VIA COMPANION IMPLEMENTATION — do not evaluate literal K3 first. "
            "(ROE1 = 0: use the direct algebraically cancelled P/B companion form with Book0.)"
        )
    if ROE2 == 0:
        rep.companion.append(
            "SUPPORTED BOUNDARY VIA CANCELLED IMPLEMENTATION — literal K3 remains singular. "
            "(ROE2 = 0: F2 must be evaluated through A2_cancelled / V_F2_cancelled.)"
        )
    if NI0 is not None and NI0 == 0:
        rep.companion.append(
            "SUPPORTED VIA COMPANION IMPLEMENTATION — use Book0 as valuation scale. "
            "(NI0 = 0 makes Equity Value = K3 x NI0 singular; use Equity Value = K_PB x Book0.)"
        )

    # ---------------- SUPPORTED_BOUNDARY ----------------
    if n1 == 0:
        rep.boundaries.append("SUPPORTED BOUNDARY — V_F1 is zero; retain ROE1, g1 and F1 structure.")
    if n2 == 0:
        rep.boundaries.append("SUPPORTED BOUNDARY — V_F2 is zero; retain F2 inputs for fade entry.")
    if F == 0:
        rep.boundaries.append("SUPPORTED BOUNDARY — use the exact zero-fade branch.")
    if abs(Ke1 - g1) < LIMIT_EPS:
        rep.boundaries.append("SUPPORTED BOUNDARY — use the exact Ke1=g1 limit.")
    if abs(Ke2 - g2) < LIMIT_EPS:
        rep.boundaries.append("SUPPORTED BOUNDARY — use the exact Ke2=g2 limit.")
    if ROE1 < 0 or ROE2 < 0:
        rep.boundaries.append(
            "SUPPORTED BOUNDARY — preserve block signs and report Equity Value when P/E is not interpretable."
        )
    if NI0 is not None and NI0 < 0:
        rep.boundaries.append("SUPPORTED BOUNDARY — report Equity Value and P/B, not a cheap/expensive negative P/E.")
    if NDE1 < 0 or NDE2 < 0:
        rep.boundaries.append("SUPPORTED BOUNDARY — verify required versus distributable cash. (Negative net debt = net cash.)")
    if (ROE1 != 0 and g1 > ROE1 > 0) or (ROE2 != 0 and g2 > ROE2 > 0) or (ROE1 < 0 < g1) or (ROE2 < 0 < g2):
        rep.boundaries.append("SUPPORTED BOUNDARY — negative FCFE is funding, not an automatic rejection. (g > ROE.)")
    if (n1 > 0 and g1 > Ke1) or (n2 > 0 and g2 > Ke2):
        rep.boundaries.append("SUPPORTED BOUNDARY — validate finite duration and economic funding. (g > Ke in a finite phase.)")

    # ---------------- REVIEW (non-blocking warnings) ----------------
    # Only conditions the canonical sources state EXPLICITLY are auto-flagged.
    # Qualitative categories ("economically extreme" inputs, NDE "near" -1,
    # "material"/"long"/"high") have no canonical numeric definition: they are
    # the analyst's judgment call and must never be reduced to invented cutoffs.
    if t < 0 or t > 1:
        rep.review.append("REVIEW — unusual tax-rate convention.")
    if Kd_F2 < 0:
        rep.review.append("REVIEW — negative debt cost requires evidence.")
    if Ke1 <= Kd_F2 or Ke2 <= Kd_F2:
        rep.review.append("REVIEW — reconcile equity and debt risk conventions. (Ke <= Kd_F2.)")
    if (GDE1 - NDE1) > 1 or (GDE2 - NDE2) > 1:
        rep.review.append("REVIEW — cash/equity exceeds 100%.")

    if LIMIT_EPS <= abs(Ke1 - g1) < ILL_CONDITION_EPS or LIMIT_EPS <= abs(Ke2 - g2) < ILL_CONDITION_EPS:
        rep.review.append("REVIEW: numerically ill-conditioned standard branch")

    # ---------------- overall status ----------------
    if rep.invalid:
        rep.status = "INVALID"
    elif rep.companion:
        rep.status = "SUPPORTED_VIA_COMPANION_IMPLEMENTATION"
    elif rep.review:
        rep.status = "REVIEW"
    elif rep.boundaries:
        rep.status = "SUPPORTED_BOUNDARY"
    else:
        rep.status = "VALID"
    return rep


if __name__ == "__main__":
    import json, sys
    data = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else json.load(sys.stdin)
    inputs = data.get("inputs", data)
    scale = data.get("scale", {}) if isinstance(data.get("scale", {}), dict) else {}
    rep = validate_inputs(inputs, NI0=scale.get("NI0"), Book0=scale.get("Book0"))
    print(json.dumps(rep.as_dict(), indent=2))
