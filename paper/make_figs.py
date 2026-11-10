"""Data figures for the JSC manuscript. Reads only the audited result files; no numbers are typed by hand.
Usage: python3 make_figs.py <repo_dir> <out_dir>
"""
import json, sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

repo, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

for f in fm.findSystemFonts():
    if "LiberationSerif" in f:
        fm.fontManager.addfont(f)
plt.rcParams.update({
    "font.family": "Liberation Serif", "font.size": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 8, "legend.fontsize": 7.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42,
})
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"   # validated slots 1-4

SYS = ["qwen2.5:7b|direct", "qwen2.5:7b|evidence", "gemma2:9b|direct", "gemma2:9b|evidence",
       "llama3.1:8b|direct", "llama3.1:8b|evidence", "word-LR", "char-LR"]
LAB = {"qwen2.5:7b|direct": "Qwen2.5 direct", "qwen2.5:7b|evidence": "Qwen2.5 evidence",
       "gemma2:9b|direct": "Gemma 2 direct", "gemma2:9b|evidence": "Gemma 2 evidence",
       "llama3.1:8b|direct": "Llama 3.1 direct", "llama3.1:8b|evidence": "Llama 3.1 evidence",
       "word-LR": "word-LR", "char-LR": "char-LR"}

sa = json.load(open(f"{repo}/results/audited/statistical_analysis.json"))
cf = json.load(open(f"{repo}/results/e1_counterfactual/analysis.json"))
rc = json.load(open(f"{repo}/results/audited/response_classification.json"))["summary"]


def save(fig, name):
    kw = dict(bbox_inches="tight", pad_inches=0.03)
    fig.savefig(f"{out}/{name}.png", dpi=600, **kw)
    fig.savefig(f"{out}/{name}.jpg", dpi=600, pil_kwargs={"quality": 95}, **kw)
    fig.savefig(f"{out}/{name}.eps", **kw)
    plt.close(fig)


def style(ax):
    ax.tick_params(length=2.5, colors=INK)
    ax.xaxis.grid(True, color=GRID, lw=0.5)
    ax.set_axisbelow(True)


# ---------- Fig A: response composition ----------
llm = SYS[:6]
fig, ax = plt.subplots(figsize=(3.15, 2.1))
cats = [("VALID_VERDICT", "Valid verdict", C1), ("ABSTENTION", "Abstention", C2),
        ("REFUSAL", "Refusal", C3), ("UNPARSEABLE", "Unparseable", C4)]
for i, s in enumerate(llm):
    y = len(llm) - 1 - i
    tot = sum(rc[s].get(k, 0) for k, _, _ in cats)
    left = 0
    for k, _, col in cats:
        v = rc[s].get(k, 0) / tot * 100
        if v > 0:
            ax.barh(y, v, left=left, height=0.62, color=col, edgecolor="#fcfcfb", linewidth=1.0)
            if v >= 4:
                ax.text(left + v / 2, y, f"{v:.0f}", ha="center", va="center", fontsize=7,
                        color="white" if col in (C1, C3) else INK)
        left += v
ax.set_yticks(range(len(llm)))
ax.set_yticklabels([LAB[s] for s in reversed(llm)])
ax.set_xlim(0, 100)
ax.set_xlabel("Share of the 4,233 items (%)")
style(ax)
ax.yaxis.grid(False)
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in cats]
ax.legend(handles, ["Valid verdict", "Abstention", "Refusal", "Unparseable (<0.4%)"], ncol=2, loc="lower center",
          bbox_to_anchor=(0.4, 1.0), frameon=False, handlelength=1, columnspacing=1.2, handletextpad=0.4)
fig.tight_layout(pad=0.4)
save(fig, "fig_response_categories")

# ---------- Fig B: E1 retention with / without a residual identity term ----------
fig, ax = plt.subplots(figsize=(3.15, 2.9))
R = sa["E1_residual_identity_terms"]["by_system"]
for i, s in enumerate(SYS):
    y = len(SYS) - 1 - i
    a = R[s]["all_answered"]
    for key, off, col, mk in (("flagged_with_identity", 0.17, C1, "o"), ("flagged_without_identity", -0.17, C2, "s")):
        r, k, n, (lo, hi) = a[key]
        ax.plot([lo * 100, hi * 100], [y + off] * 2, color=col, lw=1.1, solid_capstyle="butt")
        ax.plot(r * 100, y + off, mk, color=col, ms=4.2, mec="#fcfcfb", mew=0.6)
    ax.text(102, y, f"OR {a['odds_ratio']:.1f}", va="center", fontsize=7, color=MUTED)
ax.set_yticks(range(len(SYS)))
ax.set_yticklabels([LAB[s] for s in reversed(SYS)])
ax.axhline(1.5, color=MUTED, lw=0.5, ls=(0, (2, 2)))
ax.set_xlim(0, 100)
ax.set_xlabel("Posts still flagged after erasure (%, 95% CI)")
style(ax)
ax.yaxis.grid(False)
ax.legend([plt.Line2D([], [], marker="o", color=C1, lw=1.1, ms=4.2), plt.Line2D([], [], marker="s", color=C2, lw=1.1, ms=4.2)],
          ["Identity term remains", "No identity term"], loc="lower center", bbox_to_anchor=(0.42, 1.0),
          ncol=2, frameon=False, handlelength=1.6)
fig.tight_layout(pad=0.4)
save(fig, "fig_e1_identity")

# ---------- Fig C: counterfactual contrasts ----------
fig, ax = plt.subplots(figsize=(3.15, 2.9))
for i, s in enumerate(SYS):
    y = len(SYS) - 1 - i
    d = cf["systems"][s]
    for key, off, col, mk in (("H1_PLC_minus_NEU", 0.17, C1, "o"), ("S1_PLCDEL_minus_DEL", -0.17, C2, "s")):
        t = d[key]
        lo, hi = t["rd_ci95_post_bootstrap"]
        rd = t["risk_difference"]
        decisive = s.startswith(("qwen", "gemma"))
        ax.plot([lo * 100, hi * 100], [y + off] * 2, color=col, lw=1.1, solid_capstyle="butt", alpha=1 if decisive else 0.55)
        ax.plot(rd * 100, y + off, mk, ms=4.2, mec=col, mew=0.9, color=col if decisive else "#fcfcfb")
ax.axvline(0, color=INK, lw=0.7)
ax.axhline(3.5 + 0.0, color=MUTED, lw=0.5, ls=(0, (2, 2)))
ax.set_yticks(range(len(SYS)))
ax.set_yticklabels([LAB[s] for s in reversed(SYS)])
ax.set_xlim(-50, 65)
ax.set_xlabel("Placebo minus identity change, flag rate (points)")
style(ax)
ax.yaxis.grid(False)
ax.legend([plt.Line2D([], [], marker="o", color=C1, lw=1.1, ms=4.2), plt.Line2D([], [], marker="s", color=C2, lw=1.1, ms=4.2)],
          ["Replacement (H1)", "Deletion (S1)"], loc="lower center", bbox_to_anchor=(0.42, 1.0),
          ncol=2, frameon=False, handlelength=1.6)
fig.tight_layout(pad=0.4)
save(fig, "fig_e1cf")
print("ok")

# ---------- Fig 1: framework (redrawn; neutral wording for the learned prior) ----------
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
fig, ax = plt.subplots(figsize=(6.3, 2.55))
ax.set_xlim(0, 100); ax.set_ylim(0, 43); ax.axis("off")

def box(x, y, w, h, title, lines, fc="#f3f2ee", ec="#8a8984"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=1.2", fc=fc, ec=ec, lw=0.8))
    ax.text(x + w / 2, y + h - 3.0, title, ha="center", va="center", fontsize=8.5, fontweight="bold", color=INK)
    for i, t in enumerate(lines):
        ax.text(x + w / 2, y + h - 7.0 - i * 3.6, t, ha="center", va="center", fontsize=7, color=INK)

def arrow(p, q):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=8, lw=0.9, color=MUTED, shrinkA=0, shrinkB=0))

box(1, 21, 24, 17, "Policy", ["what counts as", "a violation"])
box(1, 1, 24, 17, "Post (evidence)", ["the words in the post;", "gold = annotator", "rationale"])
box(36, 31, 24, 8, "Learned prior", ["learned associations"], fc="#fbeee9")
box(36, 8, 24, 20, "LLM moderator", ["verdict: violating /", "not violating /", "insufficient", "+ quoted words"], fc="#e8f0fb")
box(71, 27, 28, 12, "Policy axis (R)", ["delete / narrow / negate;", "verdict follows policy"])
box(71, 13.5, 28, 12, "Evidence axis (E)", ["erase / insert rationale;", "identity-term replacement"])
box(71, 0.5, 28, 12, "Invariance (I)", ["swap group / add sentence /", "paraphrase: no change"])
arrow((25, 29.5), (36, 21)); arrow((25, 9.5), (36, 15)); arrow((48, 31), (48, 28))
for ty in (33, 19.5, 6.5):
    arrow((60, 18), (71, ty))
ax.text(85, 41.2, "Metamorphic tests", fontsize=8, color=MUTED, ha="center", style="italic")
save(fig, "fig1_framework_v2")
