#!/usr/bin/env python3
"""Executable V2.2.1 regression suite.

Reproduces references/K3_Regression_Tests_v2.2.1.json IN FULL against the real
engine code (valuation_engine.py + input_validator.py) — every check calls the
engine; nothing is compared documentation-to-documentation. Produces a
PASS/FAIL report per section and a machine-readable JSON on request.

Exit code 0 only when every non-skipped check passes. The skill is not usable
for live valuation work unless this suite is fully PASS.
"""

from __future__ import annotations

import json
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import valuation_engine as ve  # noqa: E402
from input_validator import validate_inputs  # noqa: E402

REF = Path(__file__).resolve().parent.parent / "references" / "K3_Regression_Tests_v2.2.1.json"


class Suite:
    def __init__(self):
        self.sections = {}
        self.current = None

    def section(self, name):
        self.current = name
        self.sections.setdefault(name, [])

    def check(self, name, ok, detail=""):
        self.sections[self.current].append({"name": name, "ok": bool(ok), "detail": detail})

    def close(self, name, got, exp, tol, extra=""):
        """Absolute-tolerance numeric check with a readable diff."""
        if got is None or not math.isfinite(got):
            self.check(name, False, f"got={got!r} exp={exp!r} {extra}")
            return
        diff = abs(got - exp)
        self.check(name, diff <= tol, f"got={got:.15g} exp={exp:.15g} |diff|={diff:.2e} tol={tol:.0e} {extra}")

    def skip(self, name, reason):
        self.sections[self.current].append({"name": name, "ok": True, "skipped": True, "detail": reason})

    def summary(self):
        total = passed = failed = skipped = 0
        for checks in self.sections.values():
            for c in checks:
                total += 1
                if c.get("skipped"):
                    skipped += 1
                elif c["ok"]:
                    passed += 1
                else:
                    failed += 1
        return {"total": total, "passed": passed, "failed": failed, "skipped": skipped,
                "suite": "PASS" if failed == 0 else "FAIL"}

    def report(self, verbose=False):
        lines = []
        for name, checks in self.sections.items():
            f = [c for c in checks if not c["ok"]]
            s = [c for c in checks if c.get("skipped")]
            n_ok = len([c for c in checks if c["ok"] and not c.get("skipped")])
            status = "PASS" if not f else "FAIL"
            extra = f" ({len(s)} skipped)" if s else ""
            lines.append(f"[{status}] {name:52s} {n_ok:3d}/{len(checks) - len(s)} checks{extra}")
            shown = checks if verbose else f
            for c in shown:
                tag = "SKIP" if c.get("skipped") else ("ok  " if c["ok"] else "FAIL")
                lines.append(f"    {tag} {c['name']}: {c['detail']}")
        s = self.summary()
        lines.append("-" * 78)
        lines.append(f"SUITE {s['suite']}: {s['passed']} passed, {s['failed']} failed, "
                     f"{s['skipped']} skipped, {s['total']} total  "
                     f"(formula_version: {ve.ENGINE_VERSION})")
        return "\n".join(lines)


def K3_total(inputs):
    return ve.compute_blocks(inputs)["K3"]


def run(spec_path=REF):
    spec = json.load(open(spec_path))
    S = Suite()
    base = spec["base_case"]["inputs"]
    NI0 = spec["base_case"]["normalization_context"]["NI0"]

    # ------------------------------------------------------------------ 1
    S.section("1. base_case (exact cell-value anchors)")
    tol = spec["base_case"]["tolerance"]
    cb = ve.compute_blocks(base)
    for k, exp in spec["base_case"]["derived"].items():
        S.close(f"derived.{k}", cb["derived"][k if k != "fade_prefix" else "fade_prefix"], exp, 1e-12)
    for k, exp in spec["base_case"]["expected_blocks"].items():
        S.close(f"block.{k}", cb["blocks"][k], exp, tol)
    S.close("K3 total", cb["K3"], spec["base_case"]["expected_total"], tol)
    S.close("workbook cached total", cb["K3"], spec["base_case"]["workbook_cached_total"], 1e-10)
    rec = ve.direct_recurrence_pe(base)
    S.close("direct yearly recurrence total", rec["total"],
            spec["base_case"]["direct_yearly_recurrence_total"], tol)
    nc = spec["base_case"]["normalization_context"]
    r = ve.value_scenario(base, NI0=NI0)
    S.close("equity_value = K3*NI0", r["equity_value"], nc["expected_equity_value"], tol)
    S.close("forward P/E = K3/(1+g1)", r["forward_PE"], nc["expected_forward_PE"], tol)
    S.close("implied Book0", r["implied_Book0"], nc["expected_implied_Book0"], tol)
    S.close("implied P/B0", r["implied_PB0"], nc["expected_implied_PB0"], tol)

    # ------------------------------------------------------------------ 2
    S.section("2. invariants")
    inv = {x["id"]: x for x in spec["invariants"]}
    bc = inv["base_conversion"]
    S.close("base_conversion.equity_value", r["equity_value"], bc["expected"]["equity_value"], bc["tolerance"])
    S.close("base_conversion.forward_PE", r["forward_PE"], bc["expected"]["forward_PE"], bc["tolerance"])
    S.close("base_conversion.implied_Book0", r["implied_Book0"], bc["expected"]["implied_Book0"], bc["tolerance"])
    S.close("base_conversion.implied_PB0", r["implied_PB0"], bc["expected"]["implied_PB0"], bc["tolerance"])

    ner = inv["no_excess_return_limit"]
    rn = ve.value_scenario(ner["inputs"], NI0=1.0, cross_check=True)
    S.close("no_excess_return.trailing_PE", rn["K3_trailing_PE"], ner["expected"]["trailing_PE"], ner["tolerance"])
    S.close("no_excess_return.forward_PE", rn["forward_PE"], ner["expected"]["forward_PE"], ner["tolerance"])
    S.close("no_excess_return.implied_PB0", rn["implied_PB0"], ner["expected"]["implied_PB0"], ner["tolerance"])
    S.close("no_excess_return.Bridge", rn["blocks"]["Bridge"], ner["expected"]["Bridge"], ner["tolerance"])

    cvd = inv["closed_vs_direct_yearly_recurrence"]
    S.close("closed total", cb["K3"], cvd["expected_closed_total"], cvd["tolerance"])
    S.close("direct total", rec["total"], cvd["expected_direct_total"], cvd["tolerance"])
    S.check("closed vs direct max diff",
            abs(cb["K3"] - rec["total"]) <= cvd["tolerance"],
            f"|closed-direct|={abs(cb['K3'] - rec['total']):.2e} <= {cvd['tolerance']:.0e} "
            f"(observed reference {cvd['expected_maximum_absolute_block_or_total_difference']:.2e})")

    # terminal_no_excess_return: structural formula facts
    S.check("terminal.ROE_T == Ke2 (fixed relationship)",
            cb["terminal"]["ROE_T"] == base["Ke2"]
            and abs(cb["fade_path"][-1]["ROE_k"] - base["Ke2"]) < 1e-14,
            f"last fade ROE={cb['fade_path'][-1]['ROE_k']!r} vs Ke2={base['Ke2']!r}")
    S.check("terminal.PB_T == 1 and TV = Book_T",
            cb["terminal"]["PB_T"] == 1.0 and cb["terminal"]["TV_basis"] == "Book_T",
            str(cb["terminal"]))
    S.check("terminal.g_T is finite fade-path endpoint only",
            abs(cb["fade_path"][-1]["g_k"] - base["g_T"]) < 1e-14,
            f"last fade g={cb['fade_path'][-1]['g_k']!r} vs g_T={base['g_T']!r}")

    # ------------------------------------------------------------------ 3
    S.section("3. partial_sensitivities (12 pure partials)")
    base_total = cb["K3"]
    for p in spec["partial_sensitivities"]:
        i2 = dict(base)
        bumped = i2[p["changed_input"]] + p["delta"]
        S.check(f"{p['id']}: bumped input reproduces JSON value",
                abs(bumped - p["bumped_value"]) < 1e-15,
                f"{bumped!r} vs {p['bumped_value']!r}")
        i2[p["changed_input"]] = bumped
        tot = K3_total(i2)
        S.close(f"{p['id']}: total", tot, p["expected_total"], p["tolerance"])
        pct = tot / base_total - 1.0
        S.close(f"{p['id']}: percent change", pct, p["expected_percent_change"], p["tolerance"])

    # ------------------------------------------------------------------ 4
    S.section("4. convexity_grids")
    for grid in spec["convexity_grids"]:
        gid = grid["id"]
        if gid == "gT_sensitivity_by_fade_duration":
            for pt in grid["points"]:
                i2 = dict(base); i2["F"] = pt["F"]
                t0 = K3_total(i2)
                i3 = dict(i2); i3["g_T"] = i3["g_T"] + grid["delta"]
                t1 = K3_total(i3)
                S.close(f"{gid}: F={pt['F']} base", t0, pt["base_total"], grid["tolerance"])
                S.close(f"{gid}: F={pt['F']} bumped", t1, pt["bumped_total"], grid["tolerance"])
                S.close(f"{gid}: F={pt['F']} pct", t1 / t0 - 1.0, pt["expected_percent_change"], grid["tolerance"])
            continue
        vals = []
        for pt in grid["points"]:
            i2 = dict(base); i2[grid["changed_input"]] = pt["input"]
            tot = K3_total(i2)
            vals.append(tot)
            S.close(f"{gid}: {grid['changed_input']}={pt['input']}", tot, pt["expected_total"], grid["tolerance"])
        d1 = [b - a for a, b in zip(vals, vals[1:])]
        d2 = [b - a for a, b in zip(d1, d1[1:])]
        if gid == "g2_convexity_grid":
            S.check(f"{gid}: strictly increasing", all(x > 0 for x in d1), f"d1={['%.4f' % x for x in d1]}")
            S.check(f"{gid}: convex", all(x > 0 for x in d2), f"d2={['%.4f' % x for x in d2]}")
        else:
            S.check(f"{gid}: strictly decreasing", all(x < 0 for x in d1), f"d1={['%.4f' % x for x in d1]}")
            S.check(f"{gid}: nonlinear (convex here)", all(x > 0 for x in d2), f"d2={['%.4f' % x for x in d2]}")

    # ------------------------------------------------------------------ 5
    S.section("5. boundary_tests")
    bt = {x["id"]: x for x in spec["boundary_tests"]}

    b = bt["first_F2_year_belongs_to_F2"]
    i2 = dict(base); i2.update(b["base_case_override"])
    cb2 = ve.compute_blocks(i2); rec2 = ve.direct_recurrence_pe(i2)
    S.close("first_F2_year: closed V_F2", cb2["blocks"]["V_F2"], b["expected_closed_V_F2"], b["tolerance"])
    S.close("first_F2_year: direct first-year PV", rec2["first_f2_year_pv"],
            b["expected_direct_first_year_F2_PV"], b["tolerance"])
    S.check("first_F2_year: closed==direct within tol",
            abs(cb2["blocks"]["V_F2"] - rec2["first_f2_year_pv"]) <= b["tolerance"],
            f"diff={abs(cb2['blocks']['V_F2'] - rec2['first_f2_year_pv']):.2e}")

    b = bt["zero_bridge_condition"]
    i2 = dict(base); i2.update(b["base_case_override"])
    S.close("zero_bridge: Bridge", ve.compute_blocks(i2)["blocks"]["Bridge"], b["expected_Bridge"], b["tolerance"])

    b = bt["zero_fade_condition"]
    i2 = dict(base); i2.update(b["base_case_override"])
    cb2 = ve.compute_blocks(i2)
    S.close("zero_fade: Fade_Dividends", cb2["blocks"]["Fade_Dividends"], b["expected_Fade_Dividends"], b["tolerance"])
    S.close("zero_fade: Terminal_Book_PV", cb2["blocks"]["Terminal_Book_PV"], b["expected_Terminal_Book_PV"], b["tolerance"])
    S.close("zero_fade: V_Fade", cb2["blocks"]["V_Fade"], b["expected_V_Fade"], b["tolerance"])

    b = bt["F1_Ke_equals_g_limit"]
    i2 = dict(base); i2.update(b["base_case_override"])
    cb2 = ve.compute_blocks(i2)
    S.close("F1 limit: V_F1", cb2["blocks"]["V_F1"], b["expected_V_F1"], b["tolerance"])
    S.close("F1 limit: total", cb2["K3"], b["expected_total"], b["tolerance"])
    S.check("F1 limit: exact IF-limit branch used", cb2["branches"]["F1"] == "limit", cb2["branches"]["F1"])

    b = bt["F2_Ke_equals_g_limit"]
    i2 = dict(base); i2.update(b["base_case_override"])
    cb2 = ve.compute_blocks(i2)
    S.close("F2 limit: V_F2", cb2["blocks"]["V_F2"], b["expected_V_F2"], b["tolerance"])
    S.close("F2 limit: total", cb2["K3"], b["expected_total"], b["tolerance"])
    S.check("F2 limit: exact IF-limit branch used", cb2["branches"]["F2"] == "limit", cb2["branches"]["F2"])
    S.check("F2 limit: ROE_T follows Ke2 override",
            abs(cb2["fade_path"][-1]["ROE_k"] - i2["Ke2"]) < 1e-14, "linked_fixed_relationship ROE_T=Ke2")

    S.check("terminal_book_closure: ROE_T=Ke2, PB_T=1, TV=Book_T",
            cb["terminal"] == {"ROE_T": base["Ke2"], "PB_T": 1.0, "TV_basis": "Book_T"}, str(cb["terminal"]))

    # ------------------------------------------------------------------ 6
    S.section("6. input_contract (validator classifications)")
    def status_of(mod, NI0_=None, Book0_=None, expect_invalid=None):
        i2 = dict(base); i2.update(mod)
        return validate_inputs(i2, NI0=NI0_, Book0=Book0_)

    invalid_cases = [
        ("NaN input", {"ROE2": float("nan")}),
        ("negative duration n1", {"n1": -1}),
        ("non-integer n2", {"n2": 2.5}),
        ("Ke1 <= -1", {"Ke1": -1.0}),
        ("Ke2 <= -1", {"Ke2": -1.5}),
        ("g1 <= -1", {"g1": -1.0}),
        ("g2 <= -1", {"g2": -1.2}),
        ("fade g_k <= -1", {"g_T": -2.5}),
        ("NDE2 = -1", {"NDE2": -1.0}),
        ("GDE1 < 0", {"GDE1": -0.1}),
        ("GDE2 < 0", {"GDE2": -0.2}),
        ("GDE1 < NDE1 (negative cash)", {"GDE1": 0.5}),   # NDE1 = 0.6
        ("GDE2 < NDE2 (negative cash)", {"GDE2": 0.1}),   # NDE2 = 0.2
    ]
    for name, mod in invalid_cases:
        rep = status_of(mod)
        engine_res = ve.value_scenario({**base, **mod})
        S.check(f"INVALID: {name}", rep.status == "INVALID" and not rep.is_valid
                and engine_res["computed"] is False,
                f"status={rep.status}; engine computed={engine_res['computed']}; msg={rep.invalid[:1]}")

    boundary_cases = [
        ("n1 = 0", {"n1": 0}, "V_F1 is zero"),
        ("n2 = 0", {"n2": 0}, "V_F2 is zero"),
        ("F = 0", {"F": 0}, "zero-fade branch"),
        ("Ke1 = g1", {"Ke1": base["g1"]}, "Ke1=g1 limit"),
        ("Ke2 = g2", {"Ke2": base["g2"]}, "Ke2=g2 limit"),
        ("ROE1 < 0", {"ROE1": -0.08}, "block signs"),
        ("ROE2 < 0", {"ROE2": -0.05}, "block signs"),
        ("NDE < 0 (net cash)", {"NDE1": -0.2, "GDE1": 0.0}, "distributable cash"),
        ("g > ROE", {"g2": base["ROE2"] + 0.05}, "funding"),
        ("g > Ke finite phase", {"g2": 0.20}, "finite duration"),
    ]
    for name, mod, frag in boundary_cases:
        rep = status_of(mod)
        ok = rep.is_valid and any(frag.lower() in m.lower() for m in rep.boundaries)
        engine_res = ve.value_scenario({**base, **mod})
        S.check(f"SUPPORTED_BOUNDARY: {name}", ok and engine_res["computed"],
                f"status={rep.status}; boundaries={len(rep.boundaries)}; computed={engine_res['computed']}")
    rep = validate_inputs(base, NI0=-2.0)
    S.check("SUPPORTED_BOUNDARY: NI0 < 0", rep.is_valid
            and any("negative P/E" in m for m in rep.boundaries), f"{rep.boundaries}")

    review_cases = [
        ("t > 1", {"t": 1.2}, "tax-rate"),
        ("Kd_F2 < 0", {"Kd_F2": -0.02}, "negative debt cost"),
        ("Ke <= Kd_F2", {"Ke2": 0.10}, "risk conventions"),
        ("cash/equity > 100%", {"GDE2": 1.5}, "cash/equity exceeds"),
        ("ill-conditioned |Ke-g|", {"Ke1": base["g1"] + 1e-9}, "ill-conditioned"),
    ]
    for name, mod, frag in review_cases:
        rep = status_of(mod)
        ok = rep.is_valid and any(frag.lower() in m.lower() for m in rep.review)
        S.check(f"REVIEW (canonical explicit): {name}", ok, f"status={rep.status}; review={rep.review}")

    # Qualitative REVIEW categories carry NO canonical numeric definition:
    # they must remain computable and must NOT be auto-flagged via invented
    # cutoffs (delegated to analyst judgment — implementation patch 1.1.0).
    delegated_cases = [
        ("NDE2 near -1 stays computable, no invented band", {"NDE2": -0.95, "GDE2": 0.0}),
        ("extreme returns stay computable, no invented cutoff", {"ROE2": 0.9}),
        ("extreme growth stays computable, no invented cutoff", {"g2": 0.55, "Ke2": 0.60}),
        ("long durations stay computable, no invented cutoff", {"n2": 35, "F": 32}),
    ]
    for name, mod in delegated_cases:
        rep = status_of(mod)
        engine_res = ve.value_scenario({**base, **mod}, NI0=NI0, cross_check=False)
        auto_flagged = any(("extreme" in m.lower() or "near -1" in m.lower()) for m in rep.review)
        S.check(f"DELEGATED REVIEW: {name}",
                rep.is_valid and engine_res["computed"] and not auto_flagged,
                f"status={rep.status}; review={rep.review}")

    rep = status_of({"ROE1": 0.0})
    S.check("COMPANION: ROE1 = 0", rep.is_valid and rep.status == "SUPPORTED_VIA_COMPANION_IMPLEMENTATION"
            and any("do not evaluate literal K3 first" in m for m in rep.companion), f"{rep.companion}")
    rep = status_of({"ROE2": 0.0})
    S.check("COMPANION: ROE2 = 0", rep.is_valid and any("CANCELLED" in m for m in rep.companion), f"{rep.companion}")
    rep = validate_inputs(base, NI0=0.0, Book0=59.375)
    S.check("COMPANION: NI0 = 0 with Book0", rep.is_valid
            and any("Book0 as valuation scale" in m for m in rep.companion), f"{rep.companion}")
    S.check("identity GDE - NDE = Cash/Equity documented",
            spec["input_contract"]["identity"] == "GDE - NDE = Cash / Equity", spec["input_contract"]["identity"])

    # ------------------------------------------------------------------ 7
    S.section("7. numeric_stability_contract (near Ke=g zone)")
    ns = spec["numeric_stability_contract"]
    ke1_near = base["g1"] + 1e-12
    bin_diff = ke1_near - base["g1"]
    S.close("actual binary |Ke1-g1|", bin_diff, ns["base_case_near_F1_limit"]["actual_binary_difference"], 1e-24)
    i2 = dict(base); i2["Ke1"] = ke1_near
    naive_vf1 = ve.compute_blocks(i2, naive=True)["blocks"]["V_F1"]
    stable_vf1 = ve.compute_blocks(i2)["blocks"]["V_F1"]
    exact_limit = ns["base_case_near_F1_limit"]["exact_limit_V_F1"]
    S.close("naive standard-branch V_F1 (degraded)", naive_vf1,
            ns["base_case_near_F1_limit"]["standard_double_precision_V_F1"], 1e-9,
            extra="[reproduces the documented degradation]")
    S.close("engine V_F1 (stable evaluation)", stable_vf1, exact_limit, 1e-9)
    rel_err = naive_vf1 / exact_limit - 1.0
    exp_rel = ns["base_case_near_F1_limit"]["expected_relative_error"]
    S.check("degradation is detected (naive off by ~1.5e-4; stable is not)",
            abs(rel_err - exp_rel) < abs(exp_rel) * 0.05 and abs(rel_err) > 1e-5
            and abs(stable_vf1 / exact_limit - 1.0) < 1e-9,
            f"naive rel err={rel_err:.6e} (exp {exp_rel:.6e}); stable rel err={stable_vf1 / exact_limit - 1.0:.2e}")
    rep = validate_inputs(i2)
    S.check("REVIEW message emitted in stability zone",
            any(m == ns["review_message"] for m in rep.review), f"{rep.review}")
    hp = ve.phase_annuity_hp(i2["g1"], i2["Ke1"], int(i2["n1"]))
    st = ve.phase_annuity(i2["g1"], i2["Ke1"], int(i2["n1"]))
    S.check("stable branch matches high-precision (Decimal) reference",
            abs(st / hp - 1.0) < 1e-13, f"stable={st!r} hp={hp!r} rel={st / hp - 1.0:.2e}")
    S.check("formula_change_permitted is false (frozen)", ns["formula_change_permitted"] is False, "frozen methodology")

    # ------------------------------------------------------------------ 8
    S.section("8. P/B companion form + equivalence battery")
    pbeq = spec["pb_equivalence_tests"]
    r_base = ve.value_scenario(base, NI0=NI0)
    S.close("base direct K_PB", r_base["K_PB"], pbeq["base_case"]["direct_PB"], pbeq["base_case"]["tolerance"])
    S.close("base K3*ROE1/(1+g1)", cb["K3"] * base["ROE1"] / (1 + base["g1"]),
            pbeq["base_case"]["K3_times_ROE1_div_1_plus_g1"], pbeq["base_case"]["tolerance"])

    named = {
        "base": {},
        "negative_roe1": {"ROE1": -0.08},
        "negative_roe2": {"ROE2": -0.05},
        "both_roes_negative": {"ROE1": -0.08, "ROE2": -0.05},
        "n1_zero": {"n1": 0},
        "n2_zero": {"n2": 0},
        "fade_zero": {"F": 0},
        "ke1_equals_g1": {"Ke1": base["g1"]},
        "ke2_equals_g2": {"Ke2": base["g2"]},
        "negative_g1": {"g1": -0.05},
        "negative_g2": {"g2": -0.04},
        "different_structures": {"NDE1": 0.1, "NDE2": 0.5, "GDE1": 0.3, "GDE2": 0.9},
    }
    rng = random.Random(pbeq["seed"])  # fixed seed 22021 (documented deterministic battery)
    seeded = {}
    while len(seeded) < 12:
        cand = {
            "ROE1": round(rng.uniform(-0.2, 0.5), 6) or 0.11,
            "ROE2": round(rng.uniform(-0.2, 0.6), 6) or 0.21,
            "g1": round(rng.uniform(-0.1, 0.3), 6),
            "g2": round(rng.uniform(-0.1, 0.3), 6),
            "Ke1": round(rng.uniform(0.06, 0.30), 6),
            "Ke2": round(rng.uniform(0.06, 0.30), 6),
            "n1": rng.randint(0, 8), "n2": rng.randint(0, 15), "F": rng.randint(0, 10),
            "NDE1": round(rng.uniform(-0.5, 1.5), 6), "NDE2": round(rng.uniform(-0.5, 1.5), 6),
            "g_T": round(rng.uniform(0.0, 0.06), 6),
            "Kd_F2": round(rng.uniform(0.03, 0.15), 6), "t": round(rng.uniform(0.0, 0.45), 6),
        }
        cand["GDE1"] = round(max(cand["NDE1"], 0.0) + rng.uniform(0.0, 1.0), 6)
        cand["GDE2"] = round(max(cand["NDE2"], 0.0) + rng.uniform(0.0, 1.0), 6)
        i2 = dict(base); i2.update(cand)
        if validate_inputs(i2).is_valid and i2["ROE1"] != 0:
            seeded[f"seeded_{len(seeded) + 1:02d}"] = cand
    max_pb_diff = 0.0
    max_f2_diff = 0.0
    for name, mod in {**named, **seeded}.items():
        i2 = dict(base); i2.update(mod)
        cbx = ve.compute_blocks(i2)
        scale = max(1.0, abs(cbx["K3"] or 0.0), abs(cbx["pb_blocks"]["K_PB"]))
        if i2["ROE1"] != 0:
            diff = abs(cbx["pb_blocks"]["K_PB"] - cbx["K3"] * i2["ROE1"] / (1 + i2["g1"]))
            max_pb_diff = max(max_pb_diff, diff / scale)
            S.check(f"PB equivalence: {name}", diff <= 1e-10 * scale, f"|diff|={diff:.2e} scale={scale:.1f}")
        if i2["ROE1"] != 0 and i2["ROE2"] != 0 and cbx["V_F2_literal"] is not None:
            d2 = abs(cbx["V_F2_literal"] - cbx["blocks"]["V_F2"])
            max_f2_diff = max(max_f2_diff, d2 / scale)
        recpb = ve.direct_recurrence_pb(i2)
        dpb = abs(recpb["total"] - cbx["pb_blocks"]["K_PB"])
        S.check(f"PB direct recurrence: {name}", dpb <= 1e-9 * scale, f"|diff|={dpb:.2e}")
    S.check(f"battery size >= 24 (coverage incl. {len(seeded)} seeded)", len(named) + len(seeded) >= 24,
            f"{len(named)} named + {len(seeded)} seeded")
    S.check("max scaled PB-identity diff", max_pb_diff < 1e-11, f"{max_pb_diff:.2e}")
    S.check("max scaled literal-vs-cancelled V_F2 diff", max_f2_diff < 1e-11, f"{max_f2_diff:.2e}")

    # ------------------------------------------------------------------ 9
    S.section("9. ROE1 = 0 boundary (direct P/B companion)")
    rz0 = spec["roe1_zero_pb_boundary"]
    ov = rz0["base_case_override"]
    i2 = dict(base); i2["ROE1"] = ov["ROE1"]
    res0 = ve.value_scenario(i2, Book0=ov["Book0"])
    for k in ("PB_F1", "PB_F2", "PB_Bridge", "PB_Fade"):
        S.close(f"roe1=0: {k}", res0["pb_blocks"][k], rz0["expected"][k], rz0["tolerance"])
    S.close("roe1=0: K_PB", res0["pb_blocks"]["K_PB"], rz0["expected"]["K_PB"], rz0["tolerance"])
    S.close("roe1=0: Equity Value", res0["equity_value"], rz0["expected"]["Equity_Value"], rz0["tolerance"])
    S.check("roe1=0: prohibited literal path not evaluated",
            res0["K3_trailing_PE"] is None and res0["route"] == "pb_companion",
            f"route={res0['route']}, K3={res0['K3_trailing_PE']}")

    # ------------------------------------------------------------------ 10
    S.section("10. ROE2 = 0 boundary (A2_cancelled)")
    rz2 = spec["roe2_zero_cancelled_boundary"]
    i2 = dict(base); i2.update(rz2["base_case_override"])
    cb2 = ve.compute_blocks(i2)
    exp = rz2["expected"]
    S.close("roe2=0: V_F1", cb2["blocks"]["V_F1"], exp["V_F1"], rz2["tolerance"])
    S.close("roe2=0: V_F2_cancelled", cb2["blocks"]["V_F2"], exp["V_F2_cancelled"], rz2["tolerance"])
    S.close("roe2=0: Bridge", cb2["blocks"]["Bridge"], exp["Bridge"], rz2["tolerance"])
    S.close("roe2=0: Fade_Dividends", cb2["blocks"]["Fade_Dividends"], exp["Fade_Dividends"], rz2["tolerance"])
    S.close("roe2=0: Terminal_Book_PV", cb2["blocks"]["Terminal_Book_PV"], exp["Terminal_Book_PV"], rz2["tolerance"])
    S.close("roe2=0: V_Fade", cb2["blocks"]["V_Fade"], exp["V_Fade"], rz2["tolerance"])
    S.close("roe2=0: K3-equivalent total", cb2["K3"], exp["K3_equivalent_total"], rz2["tolerance"])
    S.check("roe2=0: literal F2 not used (singular)", cb2["V_F2_literal"] is None, "A2_cancelled path")

    # ------------------------------------------------------------------ 11
    S.section("11. n1 = 0 boundary (F1 inputs still scale book)")
    nz = spec["n1_zero_still_scales_book"]
    i2 = dict(base); i2.update(nz["base_case_override"])
    cb2 = ve.compute_blocks(i2)
    S.close("n1=0: V_F1", cb2["blocks"]["V_F1"], nz["expected"]["V_F1"], nz["tolerance"])
    S.close("n1=0: V_F2", cb2["blocks"]["V_F2"], nz["expected"]["V_F2"], nz["tolerance"])
    S.close("n1=0: Bridge", cb2["blocks"]["Bridge"], nz["expected"]["Bridge"], nz["tolerance"])
    S.close("n1=0: V_Fade", cb2["blocks"]["V_Fade"], nz["expected"]["V_Fade"], nz["tolerance"])
    S.close("n1=0: K3", cb2["K3"], nz["expected"]["K3"], nz["tolerance"])
    i3 = dict(i2); i3["ROE1"] = i3["ROE1"] + 0.01
    t3 = K3_total(i3)
    S.close("n1=0: K3 with ROE1+1pp", t3, nz["expected"]["K3_with_ROE1_plus_1pp"], nz["tolerance"])
    S.close("n1=0: ROE1+1pp percent change", t3 / cb2["K3"] - 1.0,
            nz["expected"]["ROE1_plus_1pp_percent_change"], 1e-10)

    prop = spec["n1_zero_g1_proportionality"]
    i4 = dict(i2); i4["g1"] = prop["base_case_test"]["new_g1"]
    t4 = K3_total(i4)
    S.close("n1=0: K3 at g1=0.13", t4, prop["base_case_test"]["new_K3"], 1e-10)
    ratio_change = t4 / cb2["K3"] - 1.0
    exact = (1 + prop["base_case_test"]["new_g1"]) / (1 + prop["base_case_test"]["old_g1"]) - 1.0
    S.check("n1=0: exact (1+g1) proportionality", abs(ratio_change - exact) < prop["tolerance"],
            f"ratio-1={ratio_change:.15g} exact={exact:.15g} |diff|={abs(ratio_change - exact):.2e}")

    # ------------------------------------------------------------------ 12
    S.section("12. n2 = 0 boundary (direct transition to fade)")
    n2z = spec["n2_zero_boundary"]
    i2 = dict(base); i2.update(n2z["base_case_override"])
    cb2 = ve.compute_blocks(i2)
    S.close("n2=0: V_F1", cb2["blocks"]["V_F1"], n2z["expected"]["V_F1"], n2z["tolerance"])
    S.check("n2=0: V_F2 == 0", cb2["blocks"]["V_F2"] == 0.0, f"{cb2['blocks']['V_F2']!r}")
    S.close("n2=0: Bridge", cb2["blocks"]["Bridge"], n2z["expected"]["Bridge"], n2z["tolerance"])
    S.close("n2=0: V_Fade", cb2["blocks"]["V_Fade"], n2z["expected"]["V_Fade"], n2z["tolerance"])
    S.close("n2=0: K3", cb2["K3"], n2z["expected"]["K3"], n2z["tolerance"])

    # ------------------------------------------------------------------ 13
    S.section("13. negative ROE1 / negative NI0 path")
    ng = spec["negative_roe1_equity_value_path"]
    i2 = dict(base); i2["ROE1"] = ng["base_case_override"]["ROE1"]
    res_n = ve.value_scenario(i2, NI0=ng["base_case_override"]["NI0"])
    e = ng["expected"]
    S.close("negROE1: V_F1", res_n["blocks"]["V_F1"], e["V_F1"], ng["tolerance"])
    S.close("negROE1: V_F2", res_n["blocks"]["V_F2"], e["V_F2"], ng["tolerance"])
    S.close("negROE1: Bridge", res_n["blocks"]["Bridge"], e["Bridge"], ng["tolerance"])
    S.close("negROE1: Fade_Dividends", res_n["blocks"]["Fade_Dividends"], e["Fade_Dividends"], ng["tolerance"])
    S.close("negROE1: Terminal_Book_PV", res_n["blocks"]["Terminal_Book_PV"], e["Terminal_Book_PV"], ng["tolerance"])
    S.close("negROE1: V_Fade", res_n["blocks"]["V_Fade"], e["V_Fade"], ng["tolerance"])
    S.close("negROE1: trailing P/E", res_n["K3_trailing_PE"], e["trailing_PE"], ng["tolerance"])
    S.close("negROE1: implied Book0", res_n["implied_Book0"], e["implied_Book0"], ng["tolerance"])
    S.close("negROE1: Equity Value", res_n["equity_value"], e["Equity_Value"], ng["tolerance"])
    S.close("negROE1: implied P/B0", res_n["implied_PB0"], e["implied_PB0"], ng["tolerance"])
    S.check("negROE1: P/E flagged not interpretable; EV positive",
            res_n["pe_interpretable"] is False and res_n["equity_value"] > 0,
            f"pe_interpretable={res_n['pe_interpretable']} EV={res_n['equity_value']:.4f}")

    # ------------------------------------------------------------------ 14
    S.section("14. distress protocol (probability-weighted, outside K3)")
    dz = spec["distress_scenario_protocol"]
    ev_base = r_base["equity_value"]
    for reg in dz["regressions"]:
        if reg["id"] == "survival_probability_one":
            pw = ve.probability_weighted([{"name": "gc", "p": 1.0, "equity_value": ev_base}])
            S.close("p_survival=1 -> EV unchanged", pw["value"],
                    reg["expected_Probability_weighted_Equity_Value"], reg["tolerance"])
        else:
            pw = ve.probability_weighted([
                {"name": "gc", "p": reg["inputs"]["p_survival"], "equity_value": ev_base},
                {"name": "failure", "p": 1 - reg["inputs"]["p_survival"],
                 "equity_value": reg["inputs"]["Equity_Recovery_Value_failure"]},
            ])
            S.close("p=0.60, zero recovery", pw["value"],
                    reg["expected_Probability_weighted_Equity_Value"], reg["tolerance"])
    S.check("blend label is 'Probability-weighted Equity Value' (never K3)",
            pw["label"] == "Probability-weighted Equity Value", pw["label"])
    try:
        ve.probability_weighted([{"name": "a", "p": 0.7, "equity_value": 1.0}])
        S.check("probabilities must sum to 100%", False, "no error raised")
    except ValueError as err:
        S.check("probabilities must sum to 100%", True, str(err))

    # ------------------------------------------------------------------ 15
    S.section("15. fair-value funding equivalence")
    fv = spec["fair_value_funding_equivalence"]
    out = ve.fair_value_issuance(fv["inputs"]["Current_holder_Equity_Value_before_issue"],
                                 fv["inputs"]["Current_shares"],
                                 fv["inputs"]["New_capital_required"])
    S.close("post-money equity value", out["post_money_total_equity_value"],
            fv["expected"]["Post_money_total_equity_value"], fv["tolerance"])
    S.close("old-holder ownership", out["old_holder_ownership"], fv["expected"]["Old_holder_ownership"], fv["tolerance"])
    S.close("old-holder value after issue", out["old_holder_value_after_issue"],
            fv["expected"]["Old_holder_value_after_issue"], fv["tolerance"])
    S.close("value per original share", out["value_per_original_share"],
            fv["expected"]["Value_per_original_share"], fv["tolerance"])
    S.close("new shares at fair value", out["new_shares"], fv["inputs"]["New_shares"], fv["tolerance"])

    # ------------------------------------------------------------------ 16
    S.section("16. output-label contract (hurdle / reverse Ke)")
    hl = spec["hurdle_output_label"]
    S.check("permitted hurdle labels match contract",
            tuple(hl["permitted_labels"]) == ve.PERMITTED_HURDLE_LABELS, str(ve.PERMITTED_HURDLE_LABELS))
    S.check("prohibited labels are not used",
            not any(p in ve.PERMITTED_HURDLE_LABELS for p in hl["prohibited_labels"]),
            str(hl["prohibited_labels"]))
    rh = ve.value_scenario(base, NI0=NI0, label_mode="hurdle", cross_check=False)
    S.check("hurdle run is labelled 'Hurdle-conditioned Equity Value'",
            rh["output_label"] in ve.PERMITTED_HURDLE_LABELS
            and "fair value" not in rh["output_label"].lower(), rh["output_label"])
    S.check("reverse-Ke label avoids automatic 'IRR'",
            "IRR" not in ve.REVERSE_KE_LABEL.split("not")[0], ve.REVERSE_KE_LABEL)
    S.check("country-risk convention preserved in reference JSON",
            spec["country_risk_convention_metadata"]["formula"].startswith("Ke = Default-free"),
            "Ke = rf + bottom-up beta x mature ERP + lambda x CRP")

    # ------------------------------------------------------------------ 17
    S.section("17. JS mirror parity (interactive HTML engine)")
    js_path = Path(__file__).resolve().parent.parent / "assets" / "k3_engine.js"
    node = shutil.which("node")
    if not js_path.exists():
        S.skip("JS parity", "assets/k3_engine.js not present")
    elif not node:
        S.skip("JS parity", "node not available in this environment")
    else:
        vectors = ve.js_parity_vectors()
        proc = subprocess.run([node, str(js_path), "--selftest"], input=json.dumps(vectors),
                              capture_output=True, text=True, timeout=60)
        if proc.returncode != 0 and not proc.stdout.strip():
            S.check("JS parity run", False, proc.stderr[:400])
        else:
            js = json.loads(proc.stdout)
            S.check("JS mirror reproduces engine on all parity vectors",
                    js.get("pass") is True and js.get("failures") == [],
                    f"max_abs_diff={js.get('max_abs_diff'):.2e} over {js.get('checks')} checks")

    # ------------------------------------------------------------------ 18
    # Implementation patch 1.1.0: alpha-adjusted funding metrics + reporting
    # discipline. These tests detect exactly the observed error class where
    # g/ROE and 1-g/ROE were reported as K3 retention/payout despite alpha != 1.
    S.section("18. alpha-adjusted funding metrics (patch 1.1.0)")
    syn = {  # synthetic eval vector: alpha1 = 1-(0.40-0.25) = alpha2 = 1-(0.30-0.15) = 0.85
        "ROE1": 0.14, "g1": 0.09, "Ke1": 0.155, "n1": 3,
        "ROE2": 0.22, "g2": 0.12, "Ke2": 0.14, "n2": 10,
        "NDE1": 0.25, "GDE1": 0.40, "NDE2": 0.15, "GDE2": 0.30,
        "F": 6, "g_T": 0.04, "Kd_F2": 0.09, "t": 0.34,
    }
    rs = ve.value_scenario(syn, NI0=420.0, cross_check=False)
    al1 = rs["derived"]["alpha1"]; al2 = rs["derived"]["alpha2"]
    S.close("alpha1 = 1-(GDE1-NDE1)", al1, 0.85, 1e-12)
    S.close("alpha2 = 1-(GDE2-NDE2)", al2, 0.85, 1e-12)
    S.close("equity_reinvestment_ratio_F1 = alpha1*g1/ROE1",
            rs["equity_reinvestment_ratio_F1"], 0.546428571429, 1e-10)
    S.close("fcfe_distribution_ratio_F1 = 1 - alpha1*g1/ROE1",
            rs["fcfe_distribution_ratio_F1"], 0.453571428571, 1e-10)
    S.close("equity_reinvestment_ratio_F2 = alpha2*g2/ROE2",
            rs["equity_reinvestment_ratio_F2"], 0.463636363636, 1e-10)
    S.close("fcfe_distribution_ratio_F2 = 1 - alpha2*g2/ROE2",
            rs["fcfe_distribution_ratio_F2"], 0.536363636364, 1e-10)
    S.check("engine fields are exactly alpha-adjusted (bit-identical to alpha*g/ROE)",
            rs["equity_reinvestment_ratio_F1"] == al1 * syn["g1"] / syn["ROE1"]
            and rs["equity_reinvestment_ratio_F2"] == al2 * syn["g2"] / syn["ROE2"],
            "recomputed from derived alphas")
    naive_f1 = syn["g1"] / syn["ROE1"]           # 64.29% — the observed reporting error
    naive_f2 = syn["g2"] / syn["ROE2"]           # 54.55%
    S.check("g/ROE is NOT the K3 reinvestment metric when alpha != 1 (error detector)",
            abs(rs["equity_reinvestment_ratio_F1"] - naive_f1) > 1e-3
            and abs(rs["fcfe_distribution_ratio_F1"] - (1 - naive_f1)) > 1e-3
            and abs(rs["equity_reinvestment_ratio_F2"] - naive_f2) > 1e-3,
            f"alpha-adjusted F1 {rs['equity_reinvestment_ratio_F1']:.6f} vs naive g/ROE {naive_f1:.6f}; "
            f"F2 {rs['equity_reinvestment_ratio_F2']:.6f} vs naive {naive_f2:.6f}")

    # Boundary [FF]: g > ROE does NOT imply negative net distribution when alpha < 1.
    gb = dict(base); gb.update({"ROE2": 0.10, "g2": 0.12, "GDE2": 0.75, "NDE2": 0.25})  # alpha2 = 0.50 exact
    rgb = ve.value_scenario(gb, NI0=NI0)
    S.check("boundary setup: g2 > ROE2 with alpha2 = 0.50",
            gb["g2"] > gb["ROE2"] and abs(rgb["derived"]["alpha2"] - 0.5) < 1e-15,
            f"g2={gb['g2']} ROE2={gb['ROE2']} alpha2={rgb['derived']['alpha2']!r}")
    S.close("net FCFE distribution stays POSITIVE: 1-0.50*0.12/0.10 = 40%",
            rgb["fcfe_distribution_ratio_F2"], 0.40, 1e-10)
    S.check("net_distribution_negative_F2 is False despite g > ROE",
            rgb["funding"]["net_distribution_negative_F2"] is False,
            f"dr2={rgb['fcfe_distribution_ratio_F2']:.4f}")
    rec_gb = ve.direct_recurrence_pe(gb)
    S.check("direct recurrence confirms positive first-F2-year FCFE",
            rec_gb["first_f2_year_pv"] > 0, f"PV={rec_gb['first_f2_year_pv']:.6f}")
    S.check("canonical g>ROE boundary message still emitted (review signal, not funding verdict)",
            any("funding" in m for m in rgb["validation"]["boundaries"]),
            str([m for m in rgb["validation"]["boundaries"] if "funding" in m]))
    S.check("no sanity note claims negative distribution for this case",
            not any("NEGATIVE" in n for n in rgb["sanity_notes"]),
            str(rgb["sanity_notes"][:2]))
    S.check("g>ROE note defers to exact alpha-adjusted condition",
            any("does NOT imply negative FCFE" in n and "1 - alpha*g/ROE < 0" in n
                for n in rgb["sanity_notes"]),
            "note must cite the exact condition and engine ratios")

    # Converse: alpha = 1 makes the same g/ROE pair genuinely negative.
    ng = dict(base); ng.update({"ROE2": 0.10, "g2": 0.12, "GDE2": 0.25, "NDE2": 0.25})  # alpha2 = 1
    rng_ = ve.value_scenario(ng, NI0=NI0, cross_check=False)
    S.check("alpha=1: net distribution negative (1-1.2 = -20%) and flagged",
            abs(rng_["fcfe_distribution_ratio_F2"] - (-0.2)) < 1e-12
            and rng_["funding"]["net_distribution_negative_F2"] is True
            and any("NEGATIVE" in n and "external equity" in n for n in rng_["sanity_notes"]),
            f"dr2={rng_['fcfe_distribution_ratio_F2']:.4f}")

    # Fade-path funding ratios follow the same alpha-adjusted definition.
    fp = rs["fade_path"]
    fade_ok = all(
        e["equity_reinvestment_ratio"] == al2 * e["g_k"] / e["ROE_k"]
        and e["fcfe_distribution_ratio"] == 1.0 - al2 * e["g_k"] / e["ROE_k"]
        for e in fp)
    S.check("per-year fade ratios = alpha2*g_k/ROE_k (all years)", fade_ok, f"{len(fp)} fade years checked")
    S.check("final fade year ratio uses ROE_T = Ke2",
            abs(fp[-1]["equity_reinvestment_ratio"] - al2 * syn["g_T"] / syn["Ke2"]) < 1e-15,
            f"k=F ratio {fp[-1]['equity_reinvestment_ratio']:.6f}")

    # Deterministic block shares (reporting must not hand-compute them).
    shares = rs["block_shares_of_K3"]
    S.check("block shares of K3 sum to 100% and equal block/K3",
            abs(sum(shares[k] for k in ("V_F1", "V_F2", "Bridge", "V_Fade")) - 1.0) < 1e-12
            and all(shares[k] == rs["blocks"][k] / rs["K3_trailing_PE"] for k in shares),
            f"sum={sum(shares[k] for k in ('V_F1', 'V_F2', 'Bridge', 'V_Fade')):.15f}")

    # Reporting-layer audit: no resurrected non-canonical thresholds in
    # automatic notes across a stress battery (patch section 2).
    stress = [
        dict(base),                                            # base (structure change, cash)
        {**base, "ROE2": 0.60, "n2": 25},                      # high spread, long duration
        {**base, "Ke2": 0.12},                                 # high implied P/B (~4.9x)
        {**base, "NDE2": -0.8, "GDE2": 0.0},                   # strong rebasing
        {**base, "GDE2": 1.2, "NDE2": 1.1},                    # heavy leverage
        gb, ng,
    ]
    banned = ("CHECK moat evidence", "implied P/B0 =", "exceeds 15%", "15% of total",
              "extreme economic input requires support", "near -1 creates extreme rebasing",
              "no universal cutoff of", "threshold")
    hits = []
    for idx, vec in enumerate(stress):
        rr_ = ve.value_scenario(vec, NI0=NI0, cross_check=False)
        if not rr_["computed"]:
            continue
        all_msgs = list(rr_["sanity_notes"])
        for k in ("review", "boundaries", "companion"):
            all_msgs.extend(rr_["validation"][k])
        for msg in all_msgs:
            for b in banned:
                if b.lower() in msg.lower():
                    hits.append((idx, b, msg[:80]))
    S.check("no non-canonical numeric threshold appears in automatic notes", not hits, str(hits[:3]))
    S.check("implementation version bumped without touching methodology version",
            ve.IMPLEMENTATION_VERSION == "1.1.0" and ve.ENGINE_VERSION.endswith("manual-v2.2.1"),
            f"{ve.ENGINE_VERSION} / impl {ve.IMPLEMENTATION_VERSION}")
    return S


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write machine-readable results to this path")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args(argv)
    S = run()
    print(S.report(verbose=a.verbose))
    if a.json:
        Path(a.json).write_text(json.dumps({"summary": S.summary(), "sections": S.sections}, indent=2))
    return 0 if S.summary()["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
