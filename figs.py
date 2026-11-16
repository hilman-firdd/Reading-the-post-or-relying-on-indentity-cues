#!/usr/bin/env python3
"""Figures for the JSC manuscript (print, 600 dpi). Palette validated with dataviz validate_palette.js."""
import json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

C1, C2 = "#2a78d6", "#eb6834"  # categorical slots 1-2 (validated, light mode)
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3de"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED})
OUT = os.path.join(os.path.dirname(__file__), "fig"); os.makedirs(OUT, exist_ok=True)

def box(ax, x, y, w, h, title, body, fc="#f4f3ef"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.02", fc=fc, ec=MUTED, lw=0.8))
    ax.text(x + w / 2, y + h - 0.035, title, ha="center", va="top", fontsize=8, weight="bold", color=INK)
    ax.text(x + w / 2, y + h - 0.085, body, ha="center", va="top", fontsize=6.6, color=INK, linespacing=1.35)

def arrow(ax, a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=8, lw=0.8, color=MUTED))

def fig1():
    fig, ax = plt.subplots(figsize=(6.7, 3.0)); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    box(ax, 0.01, 0.56, 0.22, 0.40, "Policy (rule)", "what counts as\na violation")
    box(ax, 0.01, 0.06, 0.22, 0.40, "Post (evidence)", "the words in\nthe post;\ngold = annotator\nrationale")
    box(ax, 0.36, 0.30, 0.22, 0.42, "LLM moderator", "verdict:\nviolating /\nnot violating /\ninsufficient\n+ quoted words", fc="#e8f0fb")
    box(ax, 0.36, 0.78, 0.22, 0.20, "Prior", "stereotypes learned\nin training", fc="#fbeee8")
    arrow(ax, (0.23, 0.76), (0.36, 0.58)); arrow(ax, (0.23, 0.26), (0.36, 0.44)); arrow(ax, (0.47, 0.78), (0.47, 0.72))
    box(ax, 0.68, 0.68, 0.31, 0.29, "Policy axis (R)", "delete / narrow / negate policy\n-> verdict must follow the\nnew policy")
    box(ax, 0.68, 0.36, 0.31, 0.29, "Evidence axis (E)", "erase rationale / inject span\n-> verdict must follow the\nchanged evidence")
    box(ax, 0.68, 0.04, 0.31, 0.29, "Invariance (I)", "swap identity group /\nneutral distractor / paraphrase\n-> verdict must NOT change")
    for y in (0.82, 0.50, 0.18): arrow(ax, (0.58, 0.51), (0.68, y))
    ax.text(0.63, 0.60, "tested by", fontsize=6.3, color=MUTED, ha="center")
    fig.savefig(os.path.join(OUT, "fig1_framework.png"), dpi=600, bbox_inches="tight"); plt.close(fig)

def fig2(res):
    # verdict-only pass rates from the revised evaluator
    import json as _j
    rv = _j.load(open(os.path.join(os.path.dirname(__file__), "results/revised_full.json")))["systems"]
    rows = [("E1", "E1 erase evidence"), ("E2", "E2 inject evidence"),
            ("R2c", "R2 narrow: label should change"), ("R2s", "R2 narrow: label should stay"),
            ("R3", "R3 negate (confounded)"), ("R1", "R1 delete (needs insufficient)"),
            ("I1", "I1 swap identity"), ("I2", "I2 add neutral sentence")]
    def val(sys, m):
        v = rv[sys]
        if m == "R2c": return v["policy_axis_split"]["R2_narrow"]["label_changed"][0]
        if m == "R2s": return v["policy_axis_split"]["R2_narrow"]["label_unchanged"][0]
        return v["verdict_only_MR_pass"][m][0]
    mrs = [r[0] for r in rows]; names = dict(rows)
    fig, ax = plt.subplots(figsize=(3.6, 3.2)); ys = list(range(len(mrs)))[::-1]; h = 0.36
    for k, (sys, col, hatch) in enumerate([("word-LR", C1, None), ("char-LR", C2, "////")]):
        vals = [val(sys, m) * 100 for m in mrs]
        ax.barh([y + (h / 2 + 0.02) * (1 if k == 0 else -1) for y in ys], vals, height=h, color=col, hatch=hatch,
                edgecolor="white", lw=0, label=sys)
    ax.set_yticks(ys); ax.set_yticklabels([names[m] for m in mrs], fontsize=7, color=INK)
    ax.set_xlim(0, 100); ax.set_xlabel("Verdict pass rate (%)"); ax.xaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    ax.legend(frameon=False, fontsize=7, loc="lower center", bbox_to_anchor=(0.35, 1.0), ncol=2)
    fig.savefig(os.path.join(OUT, "fig2_mr_pass_baselines.png"), dpi=600, bbox_inches="tight"); plt.close(fig)

def fig3(resid):
    fig, ax = plt.subplots(figsize=(3.2, 2.2)); xs = [0, 1]; w = 0.36
    for k, (sys, col, hatch) in enumerate([("word-LR", C1, None), ("char-LR", C2, "////")]):
        p = resid[sys]["I1_vs_I2_paired"]; vals = [p["flip_I2"] * 100, p["flip_I1"] * 100]
        bars = ax.bar([x + (w / 2 + 0.02) * (-1 if k == 0 else 1) for x in xs], vals, width=w, color=col, hatch=hatch, edgecolor="white", lw=0, label=sys)
        for b, v in zip(bars, vals): ax.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{v:.1f}", ha="center", fontsize=6.5, color=INK)
    ax.set_xticks(xs); ax.set_xticklabels(["neutral distractor (I2)", "identity swap (I1)"], fontsize=7, color=INK)
    ax.set_ylabel("verdict changed (%)"); ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.savefig(os.path.join(OUT, "fig3_identity_vs_distractor.png"), dpi=600, bbox_inches="tight"); plt.close(fig)

if __name__ == "__main__":
    base = os.path.dirname(__file__)
    fig1(); fig2(json.load(open(os.path.join(base, "results/baseline_full.json"))))
    fig3(json.load(open(os.path.join(base, "results/residual_full.json")))); print("figures in", OUT)
