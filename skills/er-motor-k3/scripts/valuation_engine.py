#!/usr/bin/env python3
"""Deterministic valuation engine — Justified P/E closed formula V2.2.1 (frozen).

Canonical mathematical source: cell K3 of sheet "JM 2 phases + Fade ROE",
workbook vF19 (03.08.26), sha256 15a10de2...a2fb5b, as transcribed in
references/Justified_PE_AI_Manual_v2.2.1.md section 1.1. This module is a
faithful re-implementation of that exact formula plus its companion
implementations defined by the manual:

  * four-block identity      K3 = V_F1 + V_F2 + Bridge + V_fade   [FF]
  * exact |Ke-g| < 1e-12 limit branches in F1 and F2              [MI]
  * A2_cancelled / V_F2_cancelled (exact, required at ROE2 = 0)   [MI]
  * direct P/B companion form K_PB (exact, required at ROE1 = 0)  [MI]
  * numerically stable log1p/expm1 evaluation of 1 - r^n          [contract]
  * direct year-by-year recurrence used as an internal auditor    [RA]
  * probability-weighted equity value (distress, outside K3)      [DG]
  * fair-value funding equivalence helper                         [MI]
  * market-implied (reverse) single-input solver — diagnostic only

The 16 canonical inputs are the ONLY economic inputs:
  ROE1, ROE2, g1, g2, Ke1, Ke2, n1, n2, NDE1, NDE2, GDE1, GDE2, F, g_T, Kd_F2, t
NI0 (or Book0 for the companion scale) is the valuation scale, not a 17th input.
Fixed relationships (never overridable): ROE_T = Ke2, linear ROE/g fade,
F2 capital structure through fade, TV = Book_T, phase-specific discounting.

DO NOT modify the mathematics. The methodology is frozen; any change must fail
run_regressions.py, which reproduces references/K3_Regression_Tests_v2.2.1.json
in full.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from input_validator import (  # noqa: E402
    CANONICAL_INPUTS, LIMIT_EPS, ILL_CONDITION_EPS,
    fade_growth_path, validate_inputs,
)

ENGINE_VERSION = "K3-vF19-2026-08-03 / manual-v2.2.1"
# Implementation patch level of this skill. The METHODOLOGY is frozen at
# V2.2.1 FINAL — bumping this number never changes K3 mathematics.
IMPLEMENTATION_VERSION = "1.1.0"

# Base-case anchor used as a tamper fingerprint (CASE-BASE REGRESSION ANCHOR).
_FINGERPRINT_INPUTS = {
    "ROE1": 0.10846315789473689, "ROE2": 0.43447894736842096,
    "g1": 0.12, "g2": 0.15, "Ke1": 0.22, "Ke2": 0.16,
    "n1": 5, "n2": 12, "NDE1": 0.6, "NDE2": 0.2, "GDE1": 0.8, "GDE2": 0.3,
    "F": 5, "g_T": 0.05, "Kd_F2": 0.11, "t": 0.3,
}
_FINGERPRINT_K3 = 36.56588914350101

# Output-label contract (HOUSE HEURISTIC / REVIEW PRIOR — communication rules).
PERMITTED_HURDLE_LABELS = ("Hurdle-conditioned Equity Value", "Required-return scenario value")
PROHIBITED_HURDLE_LABELS = ("fair value", "pure target IRR solve", "automatically implied IRR")
REVERSE_KE_LABEL = "market-implied Ke (reverse Ke; fixed-point diagnostic — not automatically an IRR)"
PROBABILITY_WEIGHTED_LABEL = "Probability-weighted Equity Value"  # never called K3


# ----------------------------------------------------------------------------
# Core annuity evaluation (numerical-stability contract, manual section 11.11.1)
# ----------------------------------------------------------------------------

def phase_annuity(g: float, ke: float, n: int, naive: bool = False) -> float:
    """sum_{t=1..n} ((1+g)/(1+ke))^t  ==  (1+g)*(1-r^n)/(ke-g),  r=(1+g)/(1+ke).

    Branch policy (numerical-stability contract, manual 11.11.1 — formula unchanged):
    * |ke-g| < 1e-12          -> exact finite limit branch: n   [MI, never remove]
    * 1e-12 <= |ke-g| < 1e-6  -> REVIEW zone: the plain standard branch is
                                  ill-conditioned (r ~ 1 cancellation), so 1-r^n
                                  is evaluated stably via -expm1(n*log1p(-d)),
                                  d=(ke-g)/(1+ke). Mathematically identical.
    * |ke-g| >= 1e-6          -> plain standard branch (well conditioned; this is
                                  the evaluation the canonical anchors were cut from).
    * naive=True              -> force the plain branch even in the REVIEW zone
                                  (used ONLY by the regression suite to demonstrate
                                  the degradation the stable path must avoid).
    """
    n = int(n)
    if n == 0:
        return 0.0
    diff = ke - g
    if abs(diff) < LIMIT_EPS:
        return float(n)
    if naive or abs(diff) >= ILL_CONDITION_EPS:
        return (1.0 + g) * (1.0 - ((1.0 + g) / (1.0 + ke)) ** n) / diff
    d = diff / (1.0 + ke)
    one_minus_rn = -math.expm1(n * math.log1p(-d))
    return (1.0 + g) * one_minus_rn / diff


def phase_annuity_hp(g: float, ke: float, n: int, prec: int = 60) -> float:
    """High-precision (Decimal) reference for the same annuity; regression aid."""
    from decimal import Decimal, localcontext
    n = int(n)
    if n == 0:
        return 0.0
    with localcontext() as ctx:
        ctx.prec = prec
        r = (Decimal(1) + Decimal(g)) / (Decimal(1) + Decimal(ke))
        acc = Decimal(0)
        p = Decimal(1)
        for _ in range(n):
            p *= r
            acc += p
        return float(acc)


# ----------------------------------------------------------------------------
# Derived variables ([FF] — calculated, never calibrated)
# ----------------------------------------------------------------------------

def derived_variables(i: dict) -> dict:
    alpha1 = 1.0 - (i["GDE1"] - i["NDE1"])
    alpha2 = 1.0 - (i["GDE2"] - i["NDE2"])
    rz = (1.0 + i["NDE1"]) / (1.0 + i["NDE2"])
    kd_at = i["Kd_F2"] * (1.0 - i["t"])
    return {"alpha1": alpha1, "alpha2": alpha2, "rz": rz, "kd_at": kd_at}


def fade_paths(i: dict) -> dict:
    """[FF] g_k = g2+(g_T-g2)k/F ; ROE_k = ROE2+(Ke2-ROE2)k/F ; ROE_T = Ke2."""
    F = int(i["F"])
    g_path = fade_growth_path(i["g2"], i["g_T"], F)
    roe_path = [i["ROE2"] + (i["Ke2"] - i["ROE2"]) * k / F for k in range(1, F + 1)]
    return {"g_path": g_path, "roe_path": roe_path}


def funding_ratios(alpha: float, g: float, roe: float):
    """[FF] Canonical K3 funding economics (manual 1.3/1.4/5.1):

        Equity reinvestment requirement = alpha * g / ROE
        Net FCFE distribution ratio     = 1 - alpha * g / ROE

    These are the ONLY correct payout/reinvestment metrics of K3. `g/ROE` and
    `1-g/ROE` are NOT K3 quantities when alpha != 1, and `g > ROE` alone does
    NOT imply a negative net distribution — the exact negative-funding
    condition is `1 - alpha*g/ROE < 0`. Returns (None, None) when ROE == 0
    (companion-implementation territory).
    """
    if roe == 0:
        return None, None
    er = alpha * g / roe
    return er, 1.0 - er


# ----------------------------------------------------------------------------
# Closed-form blocks
# ----------------------------------------------------------------------------

def compute_blocks(i: dict, naive: bool = False) -> dict:
    """All closed-form blocks of V2.2.1.

    Returns the K3 (per unit NI0) block decomposition when ROE1 != 0 and,
    always, the exact P/B companion decomposition (per unit Book0).
    F2 is evaluated through A2_cancelled (exact for every ROE2, including 0);
    the literal spreadsheet F2 term is also computed as a diagnostic whenever
    ROE1 != 0 and ROE2 != 0.
    """
    ROE1, ROE2 = i["ROE1"], i["ROE2"]
    g1, g2, Ke1, Ke2 = i["g1"], i["g2"], i["Ke1"], i["Ke2"]
    n1, n2, F = int(i["n1"]), int(i["n2"]), int(i["F"])
    GDE1, GDE2 = i["GDE1"], i["GDE2"]
    d = derived_variables(i)
    alpha1, alpha2, rz, kd_at = d["alpha1"], d["alpha2"], d["rz"], d["kd_at"]

    ann1 = phase_annuity(g1, Ke1, n1, naive=naive)
    ann2 = phase_annuity(g2, Ke2, n2, naive=naive)
    A2_cancelled = (ROE2 - alpha2 * g2) * ann2

    g1p_n1 = (1.0 + g1) ** n1                 # (1+g1)^n1
    g1p_n1p1 = (1.0 + g1) ** (n1 + 1)        # (1+g1)^(n1+1)
    ke1p = (1.0 + Ke1) ** n1                  # (1+Ke1)^n1
    f2_disc_ratio_n2 = ((1.0 + g2) / (1.0 + Ke2)) ** n2

    # ---- fade path (F2 structure fixed; ROE_T = Ke2; g endpoint = g_T) ----
    paths = fade_paths(i)
    fade_sum = 0.0          # sum_k prod_g(k) * (ROE_k - alpha2*g_k) / (1+Ke2)^k
    fade_growth_product = 1.0
    prodg = 1.0             # prod_{j<k} (1+g_j); equals 1 for k=1
    for k in range(1, F + 1):
        gk = paths["g_path"][k - 1]
        roek = paths["roe_path"][k - 1]
        fade_sum += prodg * (roek - alpha2 * gk) / (1.0 + Ke2) ** k
        prodg *= (1.0 + gk)
    fade_growth_product = prodg
    if F == 0:
        fade_multiplier_div = 0.0
        fade_multiplier_term = 1.0
    else:
        fade_multiplier_div = fade_sum
        fade_multiplier_term = fade_growth_product / (1.0 + Ke2) ** F

    # ---------------- P/B companion blocks (universal) ----------------
    PB_F1 = (ROE1 - alpha1 * g1) * ann1 / (1.0 + g1)
    PB_F2 = (g1p_n1 / (1.0 + g2)) * rz / ke1p * A2_cancelled
    PB_Bridge = (g1p_n1 / ke1p) * (GDE2 * rz - GDE1) * (1.0 + kd_at) / (1.0 + Ke2)
    PB_pref = g1p_n1 * rz / ke1p * f2_disc_ratio_n2
    PB_Fade_Dividends = PB_pref * fade_multiplier_div
    PB_Terminal_Book_PV = PB_pref * fade_multiplier_term
    PB_Fade = PB_Fade_Dividends + PB_Terminal_Book_PV
    K_PB = PB_F1 + PB_F2 + PB_Bridge + PB_Fade

    # --- alpha-adjusted funding metrics (engine-provided; reporting must not
    #     re-derive these from g/ROE alone — implementation patch 1.1.0) ---
    er1, dr1 = funding_ratios(alpha1, g1, ROE1)
    er2, dr2 = funding_ratios(alpha2, g2, ROE2)
    fade_entries = []
    for k in range(1, F + 1):
        gk, roek = paths["g_path"][k - 1], paths["roe_path"][k - 1]
        erk, drk = funding_ratios(alpha2, gk, roek)
        fade_entries.append({"k": k, "g_k": gk, "ROE_k": roek,
                             "equity_reinvestment_ratio": erk,
                             "fcfe_distribution_ratio": drk})
    funding = {
        "equity_reinvestment_ratio_F1": er1, "fcfe_distribution_ratio_F1": dr1,
        "equity_reinvestment_ratio_F2": er2, "fcfe_distribution_ratio_F2": dr2,
        "net_distribution_negative_F1": bool(dr1 is not None and dr1 < 0),
        "net_distribution_negative_F2": bool(dr2 is not None and dr2 < 0),
        "fade_years_with_negative_distribution": [
            e["k"] for e in fade_entries
            if e["fcfe_distribution_ratio"] is not None and e["fcfe_distribution_ratio"] < 0
        ],
        "naming": "Equity reinvestment requirement = alpha*g/ROE; "
                  "Net FCFE distribution ratio = 1 - alpha*g/ROE (never g/ROE alone).",
    }

    out = {
        "derived": {**d, "fade_prefix": None},
        "funding": funding,
        "fade_path": fade_entries,
        "terminal": {"ROE_T": Ke2, "PB_T": 1.0, "TV_basis": "Book_T"},
        "branches": {
            "F1": "limit" if (n1 > 0 and abs(Ke1 - g1) < LIMIT_EPS) else "standard",
            "F2": "limit" if (n2 > 0 and abs(Ke2 - g2) < LIMIT_EPS) else "standard",
            "F1_ill_conditioned": bool(n1 > 0 and LIMIT_EPS <= abs(Ke1 - g1) < ILL_CONDITION_EPS),
            "F2_ill_conditioned": bool(n2 > 0 and LIMIT_EPS <= abs(Ke2 - g2) < ILL_CONDITION_EPS),
        },
        "A2_cancelled": A2_cancelled,
        "pb_blocks": {
            "PB_F1": PB_F1, "PB_F2": PB_F2, "PB_Bridge": PB_Bridge,
            "PB_Fade_Dividends": PB_Fade_Dividends,
            "PB_Terminal_Book_PV": PB_Terminal_Book_PV,
            "PB_Fade": PB_Fade, "K_PB": K_PB,
        },
    }

    # ---------------- K3 blocks per unit NI0 (require ROE1 != 0) ----------------
    if ROE1 != 0:
        ratio1 = 1.0 - alpha1 * g1 / ROE1
        V_F1 = ratio1 * ann1
        # cancelled F2 (exact for all ROE2, identical to literal when ROE2 != 0)
        V_F2 = (g1p_n1p1 / (1.0 + g2)) * rz / (ROE1 * ke1p) * A2_cancelled
        Bridge = (g1p_n1p1 / ROE1) / ke1p / (1.0 + Ke2) * (GDE2 * rz - GDE1) * (1.0 + kd_at)
        pref_fade = g1p_n1p1 / ROE1 * rz / ke1p * f2_disc_ratio_n2
        Fade_Dividends = pref_fade * fade_multiplier_div
        Terminal_Book_PV = pref_fade * fade_multiplier_term
        V_Fade = Fade_Dividends + Terminal_Book_PV
        K3 = V_F1 + V_F2 + Bridge + V_Fade

        V_F2_literal = None
        if ROE2 != 0:
            V_F2_literal = ((g1p_n1p1 / (1.0 + g2)) * (ROE2 / ROE1) * rz) / ke1p \
                * (1.0 - alpha2 * g2 / ROE2) * ann2

        out["derived"]["fade_prefix"] = pref_fade
        out["blocks"] = {
            "V_F1": V_F1, "V_F2": V_F2, "Bridge": Bridge,
            "Fade_Dividends": Fade_Dividends,
            "Terminal_Book_PV": Terminal_Book_PV, "V_Fade": V_Fade,
        }
        out["K3"] = K3
        out["V_F2_literal"] = V_F2_literal
        out["pb_identity_abs_diff"] = abs(K_PB - K3 * ROE1 / (1.0 + g1))
        out["block_shares_of_K3"] = (
            {k: v / K3 for k, v in out["blocks"].items()} if K3 != 0 else None
        )
    else:
        out["blocks"] = None
        out["K3"] = None
        out["V_F2_literal"] = None
        out["pb_identity_abs_diff"] = None
        out["block_shares_of_K3"] = None

    out["pb_block_shares_of_K_PB"] = (
        {k: v / K_PB for k, v in out["pb_blocks"].items() if k != "K_PB"}
        if K_PB != 0 else None
    )
    return out


# ----------------------------------------------------------------------------
# Direct year-by-year recurrence (internal auditor — [RA])
# ----------------------------------------------------------------------------

def direct_recurrence_pe(i: dict) -> dict:
    """Direct FCFE recurrence per unit NI0 (requires ROE1 != 0).

    Year conventions [FF]: F1 = years 1..n1 at Ke1; year n1+1 is the FIRST F2
    year and, like the bridge, discounts at (1+Ke1)^n1 * (1+Ke2)^j; fade years
    follow F2; terminal book at the end of fade with P/B_T = 1.
    """
    ROE1, ROE2 = i["ROE1"], i["ROE2"]
    g1, g2, Ke1, Ke2 = i["g1"], i["g2"], i["Ke1"], i["Ke2"]
    n1, n2, F = int(i["n1"]), int(i["n2"]), int(i["F"])
    GDE1, GDE2 = i["GDE1"], i["GDE2"]
    d = derived_variables(i)
    alpha1, alpha2, rz, kd_at = d["alpha1"], d["alpha2"], d["rz"], d["kd_at"]
    if ROE1 == 0:
        raise ValueError("direct_recurrence_pe requires ROE1 != 0; use direct_recurrence_pb.")

    ratio1 = 1.0 - alpha1 * g1 / ROE1
    V_F1 = 0.0
    for tt in range(1, n1 + 1):
        NI_t = (1.0 + g1) ** tt
        V_F1 += NI_t * ratio1 / (1.0 + Ke1) ** tt

    ke1p = (1.0 + Ke1) ** n1
    Book_n1 = (1.0 + g1) ** (n1 + 1) / ROE1        # beginning book of year n1+1, F1 basis
    Eq2 = Book_n1 * rz                              # rebased F2 equity base

    Bridge = (GDE2 * rz - GDE1) * Book_n1 * (1.0 + kd_at) / (ke1p * (1.0 + Ke2))

    V_F2 = 0.0
    B = Eq2
    first_f2_pv = None
    for j in range(1, n2 + 1):
        fcfe = B * (ROE2 - alpha2 * g2)             # = NI_j*(1-alpha2*g2/ROE2) when ROE2 != 0
        pv = fcfe / (ke1p * (1.0 + Ke2) ** j)
        if j == 1:
            first_f2_pv = pv
        V_F2 += pv
        B *= (1.0 + g2)

    paths = fade_paths(i)
    Fade_Dividends = 0.0
    for k in range(1, F + 1):
        gk = paths["g_path"][k - 1]
        roek = paths["roe_path"][k - 1]
        fcfe = B * (roek - alpha2 * gk)
        Fade_Dividends += fcfe / (ke1p * (1.0 + Ke2) ** (n2 + k))
        B *= (1.0 + gk)
    Terminal_Book_PV = B / (ke1p * (1.0 + Ke2) ** (n2 + F))
    V_Fade = Fade_Dividends + Terminal_Book_PV

    return {
        "V_F1": V_F1, "V_F2": V_F2, "Bridge": Bridge,
        "Fade_Dividends": Fade_Dividends, "Terminal_Book_PV": Terminal_Book_PV,
        "V_Fade": V_Fade, "total": V_F1 + V_F2 + Bridge + V_Fade,
        "first_f2_year_pv": first_f2_pv,
    }


def direct_recurrence_pb(i: dict) -> dict:
    """Direct FCFE recurrence per unit Book0 (universal, works at ROE1 = 0)."""
    ROE1, ROE2 = i["ROE1"], i["ROE2"]
    g1, g2, Ke1, Ke2 = i["g1"], i["g2"], i["Ke1"], i["Ke2"]
    n1, n2, F = int(i["n1"]), int(i["n2"]), int(i["F"])
    GDE1, GDE2 = i["GDE1"], i["GDE2"]
    d = derived_variables(i)
    alpha1, alpha2, rz, kd_at = d["alpha1"], d["alpha2"], d["rz"], d["kd_at"]

    PB_F1 = 0.0
    B = 1.0
    for tt in range(1, n1 + 1):
        fcfe = B * (ROE1 - alpha1 * g1)
        PB_F1 += fcfe / (1.0 + Ke1) ** tt
        B *= (1.0 + g1)

    ke1p = (1.0 + Ke1) ** n1
    B_n1 = B                                        # (1+g1)^n1
    PB_Bridge = (GDE2 * rz - GDE1) * B_n1 * (1.0 + kd_at) / (ke1p * (1.0 + Ke2))

    B = B_n1 * rz
    PB_F2 = 0.0
    for j in range(1, n2 + 1):
        fcfe = B * (ROE2 - alpha2 * g2)
        PB_F2 += fcfe / (ke1p * (1.0 + Ke2) ** j)
        B *= (1.0 + g2)

    paths = fade_paths(i)
    PB_Fade_Dividends = 0.0
    for k in range(1, F + 1):
        gk = paths["g_path"][k - 1]
        roek = paths["roe_path"][k - 1]
        fcfe = B * (roek - alpha2 * gk)
        PB_Fade_Dividends += fcfe / (ke1p * (1.0 + Ke2) ** (n2 + k))
        B *= (1.0 + gk)
    PB_Terminal_Book_PV = B / (ke1p * (1.0 + Ke2) ** (n2 + F))

    total = PB_F1 + PB_F2 + PB_Bridge + PB_Fade_Dividends + PB_Terminal_Book_PV
    return {
        "PB_F1": PB_F1, "PB_F2": PB_F2, "PB_Bridge": PB_Bridge,
        "PB_Fade_Dividends": PB_Fade_Dividends,
        "PB_Terminal_Book_PV": PB_Terminal_Book_PV,
        "PB_Fade": PB_Fade_Dividends + PB_Terminal_Book_PV,
        "total": total,
    }


# ----------------------------------------------------------------------------
# Scenario valuation
# ----------------------------------------------------------------------------

def _sanity_notes(i: dict, res: dict, NI0, Book0) -> list:
    """Mechanically checkable subset of manual section 8 equity-only checks.

    Discipline (implementation patch 1.1.0):
    * Funding conclusions use ONLY the exact alpha-adjusted condition
      `1 - alpha*g/ROE < 0` provided by the engine — never `g` vs `ROE` alone.
    * No invented numeric cutoffs: V2.2.1 defines no universal thresholds for
      "material" bridge, "extreme" P/B or spread-duration combinations, so
      notes state deterministic facts and the analyst judges materiality in
      the company's economic context. Remaining full checklist: manual sec. 8.
    """
    notes = []
    ROE1, ROE2, Ke1, Ke2 = i["ROE1"], i["ROE2"], i["Ke1"], i["Ke2"]
    g1, g2 = i["g1"], i["g2"]
    n1, n2 = int(i["n1"]), int(i["n2"])
    f = res.get("funding") or {}

    # Exact negative-net-distribution condition [FF 1 - alpha*g/ROE < 0]
    neg_phases = [ph for ph in ("F1", "F2") if f.get(f"net_distribution_negative_{ph}")]
    neg_fade = f.get("fade_years_with_negative_distribution") or []
    if neg_phases or neg_fade:
        parts = []
        for ph in neg_phases:
            parts.append(f"{ph} ({f.get('fcfe_distribution_ratio_' + ph):.1%})")
        if neg_fade:
            parts.append(f"fade years {neg_fade}")
        notes.append(
            "Net FCFE distribution ratio (1 - alpha*g/ROE) is NEGATIVE in " + ", ".join(parts) +
            ": growth requires net external equity, already deducted through negative FCFE — "
            "test funding access/dilution path and use current diluted shares only, "
            "with no extra dilution haircut (manual 5.1).")

    # g > ROE is a canonical review signal, NOT the negative-FCFE condition.
    gtr = [ph for ph, g_, roe_ in (("F1", g1, ROE1), ("F2", g2, ROE2)) if roe_ != 0 and g_ > roe_ > 0]
    if gtr:
        detail = "; ".join(
            f"{ph}: Net FCFE distribution ratio = {f.get('fcfe_distribution_ratio_' + ph):.1%}"
            for ph in gtr if f.get("fcfe_distribution_ratio_" + ph) is not None)
        notes.append(
            "g > ROE in " + ", ".join(gtr) + ": verify a credible external-equity/funding "
            "path (manual 3, D01). This alone does NOT imply negative FCFE — the exact "
            "condition is 1 - alpha*g/ROE < 0; engine values: " + detail + ".")

    if (n1 > 0 and ROE1 < Ke1 and g1 > 0) or (n2 > 0 and ROE2 < Ke2 and g2 > 0):
        notes.append("Growth with ROE<Ke destroys value on the reinvested equity — confirm the "
                     "transition is intentional (manual 3/8; no growth cutoff involved).")
    if Ke2 < Ke1:
        notes.append("CHECK: Ke2<Ke1 requires a real continuous-risk reduction, not thesis enthusiasm (manual 6.2).")
    if i["GDE1"] != i["GDE2"] or i["NDE1"] != i["NDE2"]:
        blocks = res.get("blocks") or {}
        shares = res.get("block_shares_of_K3") or {}
        b = blocks.get("Bridge")
        share = shares.get("Bridge")
        desc = (f"Bridge = {b:.6f}" if isinstance(b, float) else "bridge active")
        if isinstance(share, float):
            desc += f" ({share:+.1%} of K3)"
        notes.append(
            f"Structure change F1->F2: {desc}; its materiality must be judged in the company's "
            "economic context (no universal cutoff) — confirm executability and revisit "
            "ROE2/Ke2 (manual 1.5/4.7).")
    if (i["GDE1"] - i["NDE1"]) > 0 or (i["GDE2"] - i["NDE2"]) > 0:
        notes.append("CHECK cash carry: GDE>NDE with zero-cash-yield convention depresses ROE; reflect actual cash yield in normalized ROE (manual 4.2/4.7).")
    if NI0 is not None and NI0 <= 0:
        notes.append("NI0 <= 0: P/E is not interpretable — report Equity Value (and P/B) instead (manual 7.5).")
    if Book0 is not None and Book0 != 0 and NI0 not in (None, 0) and ROE1 != 0:
        implied_b0 = NI0 * (1.0 + g1) / ROE1
        gap = implied_b0 / Book0 - 1.0
        notes.append(
            f"Book0 reconciliation: implied {implied_b0:,.2f} vs provided {Book0:,.2f} "
            f"(gap {gap:+.1%}). A material gap is a review flag — judge materiality in "
            "context; no universal cutoff (manual 4.1).")
    return notes


def value_scenario(inputs: dict, NI0=None, Book0=None, shares=None, price=None,
                   label_mode: str = "fair_value", cross_check: bool = True) -> dict:
    """Value one internally coherent scenario. Returns a JSON-serializable dict."""
    rep = validate_inputs(inputs, NI0=NI0, Book0=Book0)
    result = {"validation": rep.as_dict(), "computed": False,
              "engine_version": ENGINE_VERSION, "label_mode": label_mode}
    if not rep.is_valid:
        return result

    i = dict(inputs)
    i["n1"], i["n2"], i["F"] = int(i["n1"]), int(i["n2"]), int(i["F"])
    cb = compute_blocks(i)
    ROE1, g1 = i["ROE1"], i["g1"]
    warnings = []

    route = None
    K3 = cb["K3"]
    K_PB = cb["pb_blocks"]["K_PB"]
    equity_value = None
    implied_Book0 = None
    implied_NI0 = None
    trailing_PE = K3
    forward_PE = (K3 / (1.0 + g1)) if K3 is not None else None
    implied_PB0 = (K3 * ROE1 / (1.0 + g1)) if K3 is not None else K_PB

    if ROE1 == 0:
        route = "pb_companion"
        if Book0 is None:
            warnings.append("ROE1=0: Book0 (economic book) is required to scale value; returning per-unit K_PB only.")
        else:
            equity_value = K_PB * Book0
    elif NI0 not in (None, 0):
        route = "k3_ni0"
        equity_value = K3 * NI0
        implied_Book0 = NI0 * (1.0 + g1) / ROE1
    elif Book0 is not None:
        route = "pb_scale"
        equity_value = K_PB * Book0
        implied_NI0 = Book0 * ROE1 / (1.0 + g1)
        warnings.append("P/E normalization singular or NI0 absent: Equity Value = K_PB x Book0 (companion scale; same 16 inputs).")
    else:
        route = "unit"
        warnings.append("No valuation scale provided (NI0/Book0): outputs are per-unit multiples only.")

    pe_interpretable = bool(K3 is not None and NI0 is not None and NI0 > 0)
    value_per_share = (equity_value / shares) if (equity_value is not None and shares) else None
    vs_market = None
    if price is not None and value_per_share is not None and price > 0:
        vs_market = {"price": price, "upside": value_per_share / price - 1.0}

    fu = cb["funding"]
    result.update({
        "computed": True, "route": route,
        "implementation_version": IMPLEMENTATION_VERSION,
        "derived": cb["derived"], "branches": cb["branches"],
        "blocks": cb["blocks"], "pb_blocks": cb["pb_blocks"],
        "block_shares_of_K3": cb["block_shares_of_K3"],
        "pb_block_shares_of_K_PB": cb["pb_block_shares_of_K_PB"],
        "A2_cancelled": cb["A2_cancelled"], "V_F2_literal": cb["V_F2_literal"],
        "fade_path": cb["fade_path"], "terminal": cb["terminal"],
        # alpha-adjusted funding metrics [FF] — reporting must consume these,
        # never re-derive payout/funding from g/ROE alone:
        "funding": fu,
        "equity_reinvestment_ratio_F1": fu["equity_reinvestment_ratio_F1"],
        "fcfe_distribution_ratio_F1": fu["fcfe_distribution_ratio_F1"],
        "equity_reinvestment_ratio_F2": fu["equity_reinvestment_ratio_F2"],
        "fcfe_distribution_ratio_F2": fu["fcfe_distribution_ratio_F2"],
        "K3_trailing_PE": K3, "forward_PE": forward_PE,
        "implied_Book0": implied_Book0, "implied_NI0": implied_NI0,
        "implied_PB0": implied_PB0, "K_PB": K_PB,
        "NI0": NI0, "Book0": Book0, "shares_diluted_t0": shares,
        "equity_value": equity_value, "value_per_share": value_per_share,
        "pe_interpretable": pe_interpretable, "vs_market": vs_market,
        "warnings": warnings,
    })

    if label_mode == "hurdle":
        result["output_label"] = PERMITTED_HURDLE_LABELS[0]
        result["label_note"] = ("Ke set to a hurdle: this is NOT fair value, an IRR or a pure "
                                "target-return solve; Ke2 also moves ROE_T/fade economics (manual 6.3).")
    else:
        result["output_label"] = "Current-holder Equity Value"

    if cross_check:
        checks = {}
        if ROE1 != 0:
            rec = direct_recurrence_pe(i)
            checks["direct_recurrence_total"] = rec["total"]
            checks["closed_total"] = K3
            checks["closed_vs_direct_abs_diff"] = abs(rec["total"] - K3)
            checks["pb_identity_abs_diff"] = cb["pb_identity_abs_diff"]
            if cb["V_F2_literal"] is not None:
                checks["literal_vs_cancelled_V_F2_abs_diff"] = abs(cb["V_F2_literal"] - cb["blocks"]["V_F2"])
        else:
            rec = direct_recurrence_pb(i)
            checks["direct_recurrence_K_PB"] = rec["total"]
            checks["closed_K_PB"] = K_PB
            checks["closed_vs_direct_abs_diff"] = abs(rec["total"] - K_PB)
        scale_ref = max(1.0, abs(K3 if K3 is not None else K_PB))
        checks["pass"] = checks["closed_vs_direct_abs_diff"] < 1e-9 * scale_ref
        if not checks["pass"]:
            warnings.append("INTERNAL AUDITOR MISMATCH: closed form vs direct recurrence diverge; do not use this run.")
        result["cross_checks"] = checks

    result["sanity_notes"] = _sanity_notes(i, result, NI0, Book0)
    return result


# ----------------------------------------------------------------------------
# Case-level valuation (multi-scenario, weights, distress, market comparison)
# ----------------------------------------------------------------------------

def fingerprint_ok() -> bool:
    cb = compute_blocks(_FINGERPRINT_INPUTS)
    return abs(cb["K3"] - _FINGERPRINT_K3) < 1e-9


def probability_weighted(states: list) -> dict:
    """[DG] Probability-weighted Equity Value = sum_s p_s * Equity_Value_s.

    states: [{"name":..., "p":..., "equity_value":...}, ...]; p must sum to 1.
    The blend is NOT K3 and is never labelled K3.
    """
    total_p = sum(s["p"] for s in states)
    if abs(total_p - 1.0) > 1e-9:
        raise ValueError(f"State probabilities must sum to 100% (got {total_p:.6f}).")
    value = sum(s["p"] * s["equity_value"] for s in states)
    return {"label": PROBABILITY_WEIGHTED_LABEL, "value": value,
            "states": states,
            "note": "Each going-concern state must use internally coherent K3 inputs; "
                    "recovery is residual equity value and may be zero; do not double-count "
                    "the same event in probability and Ke (manual 6.5)."}


def fair_value_issuance(pre_money_equity_value: float, current_shares: float,
                        new_capital_required: float) -> dict:
    """[MI] Fair-value funding equivalence (manual 11.12.2)."""
    issue_price = pre_money_equity_value / current_shares
    new_shares = new_capital_required / issue_price
    post_money = pre_money_equity_value + new_capital_required
    old_ownership = current_shares / (current_shares + new_shares)
    return {
        "issue_price": issue_price, "new_shares": new_shares,
        "post_money_total_equity_value": post_money,
        "old_holder_ownership": old_ownership,
        "old_holder_value_after_issue": post_money * old_ownership,
        "value_per_original_share": post_money * old_ownership / current_shares,
        "note": "Fair-value issuance leaves existing holders' value per original share unchanged; "
                "negative FCFE already reflects funding — no generic dilution haircut (manual 5.1).",
    }


def value_case(case: dict) -> dict:
    """Value every scenario in a case file; apply weights/distress if present."""
    market = case.get("market", {}) or {}
    shares = market.get("shares_diluted_t0")
    price = market.get("price_per_share")
    out = {
        "engine_version": ENGINE_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "engine_fingerprint_ok": fingerprint_ok(),
        "company": case.get("company"), "currency": case.get("currency"),
        "valuation_date": case.get("valuation_date"),
        "market": market, "scenarios": {},
    }
    for name, sc in (case.get("scenarios") or {}).items():
        scale = sc.get("scale", {}) or {}
        out["scenarios"][name] = value_scenario(
            sc["inputs"], NI0=scale.get("NI0"), Book0=scale.get("Book0"),
            shares=sc.get("shares_diluted_t0", shares), price=price,
            label_mode=sc.get("label_mode", "fair_value"),
        )

    weights = {n: sc.get("weight") for n, sc in (case.get("scenarios") or {}).items()
               if sc.get("weight") is not None}
    if weights:
        states = []
        for n, w in weights.items():
            ev = out["scenarios"][n].get("equity_value")
            if ev is None:
                states = []
                break
            states.append({"name": n, "p": w, "equity_value": ev})
        if states:
            try:
                out["probability_weighted"] = probability_weighted(states)
            except ValueError as e:
                out["probability_weighted"] = {"error": str(e)}

    dz = case.get("distress")
    if dz and dz.get("apply"):
        gc = dz.get("going_concern_scenario", "base")
        ev = out["scenarios"].get(gc, {}).get("equity_value")
        if ev is not None:
            out["distress_blend"] = probability_weighted([
                {"name": f"going-concern ({gc})", "p": dz["p_survival"], "equity_value": ev},
                {"name": "failure/recovery", "p": 1.0 - dz["p_survival"],
                 "equity_value": dz.get("recovery_equity_value", 0.0)},
            ])
    return out


# ----------------------------------------------------------------------------
# Sensitivity analysis (values chosen by the analyst; grids here are mechanics)
# ----------------------------------------------------------------------------

INTEGER_PARAMS = {"n1", "n2", "F"}


def _scenario_metric(case: dict, scenario: str, overrides: dict):
    sc = case["scenarios"][scenario]
    inputs = dict(sc["inputs"]); inputs.update(overrides)
    scale = sc.get("scale", {}) or {}
    market = case.get("market", {}) or {}
    r = value_scenario(inputs, NI0=scale.get("NI0"), Book0=scale.get("Book0"),
                       shares=sc.get("shares_diluted_t0", market.get("shares_diluted_t0")),
                       price=market.get("price_per_share"), cross_check=False)
    return r


def sensitivity_1d(case: dict, scenario: str, param: str, values: list) -> dict:
    base = _scenario_metric(case, scenario, {})
    rows = []
    for v in values:
        v2 = int(v) if param in INTEGER_PARAMS else float(v)
        r = _scenario_metric(case, scenario, {param: v2})
        rows.append({
            "value": v2, "computed": r["computed"],
            "validation_status": r["validation"]["status"],
            "K3_trailing_PE": r.get("K3_trailing_PE"),
            "equity_value": r.get("equity_value"),
            "value_per_share": r.get("value_per_share"),
            "upside": (r.get("vs_market") or {}).get("upside"),
            "pct_vs_base": (r["equity_value"] / base["equity_value"] - 1.0)
                           if (r.get("equity_value") and base.get("equity_value")) else None,
        })
    return {"scenario": scenario, "param": param, "base": {
        "value": case["scenarios"][scenario]["inputs"][param],
        "equity_value": base.get("equity_value"),
        "value_per_share": base.get("value_per_share")}, "rows": rows}


def sensitivity_2d(case: dict, scenario: str, p1: str, values1: list, p2: str, values2: list) -> dict:
    grid = []
    for v1 in values1:
        row = []
        for v2 in values2:
            o = {p1: int(v1) if p1 in INTEGER_PARAMS else float(v1),
                 p2: int(v2) if p2 in INTEGER_PARAMS else float(v2)}
            r = _scenario_metric(case, scenario, o)
            row.append({"K3_trailing_PE": r.get("K3_trailing_PE"),
                        "equity_value": r.get("equity_value"),
                        "value_per_share": r.get("value_per_share"),
                        "upside": (r.get("vs_market") or {}).get("upside"),
                        "status": r["validation"]["status"]})
        grid.append(row)
    return {"scenario": scenario, "param_rows": p1, "values_rows": list(values1),
            "param_cols": p2, "values_cols": list(values2), "grid": grid}


# ----------------------------------------------------------------------------
# Market-implied (reverse) single-input solver — labelled diagnostic only
# ----------------------------------------------------------------------------

SOLVER_DOMAINS = {
    "ROE1": (-0.50, 1.20), "ROE2": (-0.50, 1.20),
    "g1": (-0.60, 0.60), "g2": (-0.60, 0.60),
    "Ke1": (0.02, 0.60), "Ke2": (0.02, 0.60),
    "g_T": (-0.10, 0.15),
    "NDE1": (-0.90, 3.00), "NDE2": (-0.90, 3.00),
    "GDE1": (0.00, 3.00), "GDE2": (0.00, 3.00),
    "Kd_F2": (0.00, 0.40), "t": (0.00, 0.60),
}
SOLVER_INT_DOMAINS = {"n1": (0, 40), "n2": (0, 40), "F": (0, 40)}


def solve_market_implied(case: dict, scenario: str, param: str,
                         target_price=None, target_equity_value=None,
                         domain=None) -> dict:
    """Hold every other base-scenario input constant; solve `param` so the model
    reproduces the target (market price per share by default).

    This is labelled reverse valuation [FF]: a diagnostic of expectations.
    NEVER feed the solved value back into fundamental calibration, and never
    call an implied-Ke solution an IRR (manual 6.4; MICAP note in 4.5).
    """
    market = case.get("market", {}) or {}
    if target_price is None and target_equity_value is None:
        target_price = market.get("price_per_share")
    shares = case["scenarios"][scenario].get("shares_diluted_t0", market.get("shares_diluted_t0"))

    def metric(overrides):
        r = _scenario_metric(case, scenario, overrides)
        if not r["computed"]:
            return None
        if target_equity_value is not None:
            return r.get("equity_value")
        return r.get("value_per_share")

    target = target_equity_value if target_equity_value is not None else target_price
    if target is None:
        return {"error": "No target: provide market.price_per_share (with shares) or target_equity_value."}
    if target_equity_value is None and not shares:
        return {"error": "Per-share target requires shares_diluted_t0."}

    base_value = case["scenarios"][scenario]["inputs"][param]
    base_metric = metric({})
    label = None
    if param in ("Ke1", "Ke2"):
        label = REVERSE_KE_LABEL
    elif param == "n2":
        label = "market-implied full-spread duration (MICAP-style diagnostic, manual 4.5)"

    common = {"scenario": scenario, "param": param, "base_value": base_value,
              "base_metric": base_metric, "target": target,
              "target_kind": "equity_value" if target_equity_value is not None else "price_per_share",
              "label": label,
              "note": "Reverse valuation diagnostic — all other inputs held at base; "
                      "do not recalibrate fair value from this output."}

    # Integer parameters: scan and report nearest bracketing values.
    if param in SOLVER_INT_DOMAINS:
        lo, hi = domain or SOLVER_INT_DOMAINS[param]
        rows = []
        for v in range(int(lo), int(hi) + 1):
            m = metric({param: v})
            if m is not None:
                rows.append((v, m))
        if not rows:
            return {**common, "solution": None, "reason": "no valid points in domain"}
        best = min(rows, key=lambda r: abs(r[1] - target))
        bracket = None
        for (v1, m1), (v2, m2) in zip(rows, rows[1:]):
            if (m1 - target) * (m2 - target) <= 0:
                bracket = {"lower": {"value": v1, "metric": m1}, "upper": {"value": v2, "metric": m2}}
                break
        exact = abs(best[1] - target) <= 1e-9 * max(1.0, abs(target))
        return {**common, "solution": best[0] if exact else None,
                "nearest": {"value": best[0], "metric": best[1]},
                "bracket": bracket, "domain": [int(lo), int(hi)],
                "reason": None if (exact or bracket) else
                "target not reachable inside integer domain — no economically valid exact solution"}

    lo, hi = domain or SOLVER_DOMAINS[param]
    # Respect structural INVALID constraints when sweeping debt ratios.
    sc_in = case["scenarios"][scenario]["inputs"]
    if param == "GDE1": lo = max(lo, sc_in["NDE1"])
    if param == "GDE2": lo = max(lo, sc_in["NDE2"])
    if param == "NDE1": hi = min(hi, sc_in["GDE1"])
    if param == "NDE2": hi = min(hi, sc_in["GDE2"])

    N = 120
    xs, fs = [], []
    for k in range(N + 1):
        x = lo + (hi - lo) * k / N
        m = metric({param: x})
        if m is not None and math.isfinite(m):
            xs.append(x); fs.append(m - target)
    if len(xs) < 2:
        return {**common, "solution": None, "domain": [lo, hi],
                "reason": "domain produced no valid evaluations"}

    brackets = [(xs[k], xs[k + 1]) for k in range(len(xs) - 1) if fs[k] * fs[k + 1] <= 0]
    if not brackets:
        return {**common, "solution": None, "domain": [lo, hi],
                "achieved_metric_range": [min(f + target for f in fs), max(f + target for f in fs)],
                "reason": "no economically valid solution within domain — the model cannot "
                          "reach the target by moving this input alone"}

    def bisect(a, b):
        fa = metric({param: a}) - target
        for _ in range(200):
            c = 0.5 * (a + b)
            fc = metric({param: c}) - target
            if fc == 0 or (b - a) / 2 < 1e-12:
                return c
            if (fa < 0) == (fc < 0):
                a, fa = c, fc
            else:
                b = c
        return 0.5 * (a + b)

    solutions = sorted((bisect(a, b) for a, b in brackets),
                       key=lambda s: abs(s - (base_value if isinstance(base_value, (int, float)) else 0.0)))
    sol = solutions[0]
    return {**common, "solution": sol, "all_solutions": solutions, "domain": [lo, hi],
            "solved_metric": metric({param: sol}),
            "delta_vs_base": sol - base_value if isinstance(base_value, (int, float)) else None}


# ----------------------------------------------------------------------------
# JS-parity vectors (for the interactive HTML mirror)
# ----------------------------------------------------------------------------

def js_parity_vectors() -> list:
    """Deterministic vectors the JS mirror must reproduce (tol 1e-9)."""
    base = dict(_FINGERPRINT_INPUTS)
    cases = [("base", base, 5.75, None)]
    cases.append(("ke1_eq_g1", {**base, "Ke1": 0.12}, 5.75, None))
    cases.append(("ke2_eq_g2", {**base, "Ke2": 0.15}, 5.75, None))
    cases.append(("zero_fade", {**base, "F": 0}, 5.75, None))
    cases.append(("n1_zero", {**base, "n1": 0}, 5.75, None))
    cases.append(("n2_zero", {**base, "n2": 0}, 5.75, None))
    cases.append(("roe2_zero", {**base, "ROE2": 0.0}, 5.75, None))
    cases.append(("roe1_zero", {**base, "ROE1": 0.0}, None, 100.0))
    cases.append(("neg_roe1", {**base, "ROE1": -0.08}, -2.0, None))
    cases.append(("net_cash", {**base, "NDE1": -0.2, "NDE2": -0.1, "GDE1": 0.1, "GDE2": 0.1}, 5.75, None))
    out = []
    for name, inp, ni0, b0 in cases:
        r = value_scenario(inp, NI0=ni0, Book0=b0, cross_check=False)
        out.append({"name": name, "inputs": inp, "NI0": ni0, "Book0": b0,
                    "expected": {"K3": r.get("K3_trailing_PE"), "K_PB": r.get("K_PB"),
                                 "equity_value": r.get("equity_value"),
                                 "blocks": r.get("blocks"), "pb_blocks": r.get("pb_blocks"),
                                 "funding": {
                                     k: r.get(k) for k in (
                                         "equity_reinvestment_ratio_F1",
                                         "fcfe_distribution_ratio_F1",
                                         "equity_reinvestment_ratio_F2",
                                         "fcfe_distribution_ratio_F2")}}})
    return out


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def _parse_values(spec: str) -> list:
    if ":" in spec:
        lo, hi, n = spec.split(":")
        lo, hi, n = float(lo), float(hi), int(n)
        return [lo + (hi - lo) * k / (n - 1) for k in range(n)]
    return [float(x) for x in spec.split(",")]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Justified P/E V2.2.1 deterministic valuation engine")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("value", help="value all scenarios in a case JSON")
    p_val.add_argument("case"); p_val.add_argument("--out")

    p_sens = sub.add_parser("sens", help="1D/2D sensitivity")
    p_sens.add_argument("case"); p_sens.add_argument("--scenario", default="base")
    p_sens.add_argument("--param", required=True); p_sens.add_argument("--values", required=True)
    p_sens.add_argument("--param2"); p_sens.add_argument("--values2")
    p_sens.add_argument("--out")

    p_imp = sub.add_parser("implied", help="market-implied single-input solve (reverse valuation)")
    p_imp.add_argument("case"); p_imp.add_argument("--scenario", default="base")
    p_imp.add_argument("--param", required=True)
    p_imp.add_argument("--target-price", type=float); p_imp.add_argument("--target-value", type=float)
    p_imp.add_argument("--out")

    sub.add_parser("fingerprint", help="quick base-case anchor check")
    sub.add_parser("selftest", help="run the full V2.2.1 regression suite")
    p_jsv = sub.add_parser("jsvectors", help="emit JS-parity vectors")
    p_jsv.add_argument("--out")

    a = ap.parse_args(argv)

    if a.cmd == "fingerprint":
        ok = fingerprint_ok()
        print(json.dumps({"engine_version": ENGINE_VERSION, "fingerprint_ok": ok}))
        return 0 if ok else 1
    if a.cmd == "selftest":
        from run_regressions import main as reg_main
        return reg_main([])
    if a.cmd == "jsvectors":
        payload = json.dumps(js_parity_vectors(), indent=2)
        if a.out: Path(a.out).write_text(payload)
        else: print(payload)
        return 0

    case = json.load(open(a.case))
    if a.cmd == "value":
        res = value_case(case)
    elif a.cmd == "sens":
        if a.param2:
            res = sensitivity_2d(case, a.scenario, a.param, _parse_values(a.values),
                                 a.param2, _parse_values(a.values2))
        else:
            res = sensitivity_1d(case, a.scenario, a.param, _parse_values(a.values))
    elif a.cmd == "implied":
        res = solve_market_implied(case, a.scenario, a.param,
                                   target_price=a.target_price, target_equity_value=a.target_value)
    payload = json.dumps(res, indent=2, default=str)
    if getattr(a, "out", None):
        Path(a.out).write_text(payload); print(f"written: {a.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
