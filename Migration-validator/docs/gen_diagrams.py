"""
Generates professional diagrams (PNG) for the Migration Validator documentation.
Run: python docs/gen_diagrams.py
Output: docs/assets/*.png
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ASSETS = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(ASSETS, exist_ok=True)

# ----- Shared palette -----
PRIMARY = "#1F4E79"
ACCENT = "#2E86C1"
GREEN = "#1E8449"
ORANGE = "#CA6F1E"
PURPLE = "#6C3483"
GREY = "#5D6D7E"
LIGHT = "#EBF5FB"
WHITE = "#FFFFFF"


def _box(ax, x, y, w, h, text, fc, tc=WHITE, fs=11, bold=True):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.5, edgecolor=fc, facecolor=fc, alpha=0.95,
    )
    ax.add_patch(box)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center", color=tc, fontsize=fs,
        fontweight="bold" if bold else "normal", wrap=True,
    )


def _arrow(ax, x1, y1, x2, y2, color=GREY, style="-|>"):
    ar = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style, mutation_scale=18,
        linewidth=1.8, color=color,
    )
    ax.add_patch(ar)


def diagram_pipeline():
    """High-level end-to-end pipeline flow."""
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")

    steps = [
        ("1. Extract\nSchemas", PRIMARY, 0.5),
        ("2. Match\nColumns", ACCENT, 2.8),
        ("3. Assign\nRules", GREEN, 5.1),
        ("4. Generate\nSQL", ORANGE, 7.4),
        ("5. Write\nYAML", PURPLE, 9.7),
    ]
    y = 4.5
    for text, color, x in steps:
        _box(ax, x, y, 1.9, 1.4, text, color, fs=11)
    for i in range(len(steps) - 1):
        x1 = steps[i][2] + 1.9
        x2 = steps[i + 1][2]
        _arrow(ax, x1, y + 0.7, x2, y + 0.7, GREY)

    # Source / Target
    _box(ax, 0.5, 6.6, 4.2, 0.9, "Source DB  (PostgreSQL / MSSQL / Athena)", GREY, fs=10)
    _box(ax, 7.3, 6.6, 4.2, 0.9, "Target  (Snowflake)", ACCENT, fs=10)
    _arrow(ax, 2.6, 6.6, 1.45, 5.9, GREY)
    _arrow(ax, 9.4, 6.6, 10.65, 5.9, ACCENT)

    # Output
    _box(ax, 3.9, 1.3, 4.2, 1.0, "Validation YAML Suites\n(comparable normalized SQL)", PRIMARY, fs=10)
    _arrow(ax, 10.65, 4.5, 6.0, 2.3, PURPLE)

    ax.set_title("Migration Validator — End-to-End Pipeline",
                 fontsize=15, fontweight="bold", color=PRIMARY, pad=14)
    fig.savefig(os.path.join(ASSETS, "pipeline.png"), dpi=160, bbox_inches="tight")
    plt.close(fig)


def diagram_matching():
    """Column matching cascade: exact -> fuzzy -> AI."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")

    _box(ax, 4.3, 6.7, 3.4, 1.0, "Source Column", PRIMARY, fs=12)

    _box(ax, 1.0, 4.6, 3.0, 1.1, "Exact Match\n(normalized names)", GREEN, fs=11)
    _box(ax, 4.5, 4.6, 3.0, 1.1, "Fuzzy Match\n(similarity score)", ORANGE, fs=11)
    _box(ax, 8.0, 4.6, 3.0, 1.1, "AI Match\n(LLM semantic)", PURPLE, fs=11)

    _arrow(ax, 5.4, 6.7, 2.5, 5.7, GREEN)
    _arrow(ax, 6.0, 6.7, 6.0, 5.7, ORANGE)
    _arrow(ax, 6.6, 6.7, 9.5, 5.7, PURPLE)

    ax.text(2.5, 4.2, "highest priority", ha="center", fontsize=9, color=GREEN, style="italic")
    ax.text(6.0, 4.2, "if no exact match", ha="center", fontsize=9, color=ORANGE, style="italic")
    ax.text(9.5, 4.2, "fallback / ambiguous", ha="center", fontsize=9, color=PURPLE, style="italic")

    _box(ax, 3.9, 2.0, 4.2, 1.1, "Matched Column Pair\n+ Confidence Score", ACCENT, fs=11)
    _arrow(ax, 2.5, 4.6, 5.0, 3.1, GREEN)
    _arrow(ax, 6.0, 4.6, 6.0, 3.1, ORANGE)
    _arrow(ax, 9.5, 4.6, 7.0, 3.1, PURPLE)

    ax.set_title("Column Matching Cascade",
                 fontsize=15, fontweight="bold", color=PRIMARY, pad=14)
    fig.savefig(os.path.join(ASSETS, "matching.png"), dpi=160, bbox_inches="tight")
    plt.close(fig)


def diagram_null_sentinel():
    """Explains the NULL sentinel wrapping concept."""
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")

    _box(ax, 0.5, 3.3, 5.0, 1.2, "Source value\nCAST(expr AS TEXT)", PRIMARY, fs=11)
    _box(ax, 6.5, 3.3, 5.0, 1.2, "Target value\nCAST(expr AS TEXT)", ACCENT, fs=11)

    _box(ax, 0.5, 1.3, 5.0, 1.2, "COALESCE(..., '<<NULL>>')", GREEN, fs=11)
    _box(ax, 6.5, 1.3, 5.0, 1.2, "COALESCE(..., '<<NULL>>')", GREEN, fs=11)

    _arrow(ax, 3.0, 3.3, 3.0, 2.5, GREY)
    _arrow(ax, 9.0, 3.3, 9.0, 2.5, GREY)

    ax.text(6.0, 0.6, "Now  NULL == NULL  is comparable across systems",
            ha="center", fontsize=11, color=ORANGE, fontweight="bold")

    ax.set_title("NULL Sentinel Normalization Strategy",
                 fontsize=15, fontweight="bold", color=PRIMARY, pad=14)
    fig.savefig(os.path.join(ASSETS, "null_sentinel.png"), dpi=160, bbox_inches="tight")
    plt.close(fig)


def diagram_batch():
    """Batch mode flow."""
    fig, ax = plt.subplots(figsize=(10, 5.0))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")

    _box(ax, 0.5, 4.3, 3.2, 1.1, "Batch Config\n(table list)", PRIMARY, fs=11)
    _box(ax, 4.4, 4.3, 3.2, 1.1, "Config Parser", ACCENT, fs=11)
    _box(ax, 8.3, 4.3, 3.2, 1.1, "Batch Runner", ORANGE, fs=11)

    _arrow(ax, 3.7, 4.85, 4.4, 4.85, GREY)
    _arrow(ax, 7.6, 4.85, 8.3, 4.85, GREY)

    for i, name in enumerate(["Table A", "Table B", "Table C"]):
        _box(ax, 1.5 + i * 3.3, 2.2, 2.6, 1.0, name, GREEN, fs=11)
        _arrow(ax, 9.9, 4.3, 2.8 + i * 3.3, 3.2, ORANGE)

    _box(ax, 3.9, 0.4, 4.2, 1.0, "Manifest + YAML Suites", PURPLE, fs=11)
    for i in range(3):
        _arrow(ax, 2.8 + i * 3.3, 2.2, 6.0, 1.4, GREEN)

    ax.set_title("Batch Mode — Multiple Tables",
                 fontsize=15, fontweight="bold", color=PRIMARY, pad=14)
    fig.savefig(os.path.join(ASSETS, "batch.png"), dpi=160, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    diagram_pipeline()
    diagram_matching()
    diagram_null_sentinel()
    diagram_batch()
    print("Diagrams generated in:", ASSETS)
    for f in sorted(os.listdir(ASSETS)):
        print(" -", f)
