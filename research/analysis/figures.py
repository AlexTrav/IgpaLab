"""Рисунки анализа данных: для сайта (ru) и статьи (en)."""

from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D

from . import eda
from .style import DIVERGING, FEATURES, GROUPS, INK, INK_2, LABELS, SEQUENTIAL, SERIES, SURFACE, plt, setup

GAP = {"edgecolor": SURFACE, "linewidth": 2}   # просвет 2 px между соседними заливками
BELOW = {"loc": "upper left", "bbox_to_anchor": (0, -0.22)}   # легенда под осью, не спорит с заголовком


def number(value: float, lang: str, digits: int = 2, sign: bool = False) -> str:
    text = f"{value:+.{digits}f}" if sign else f"{value:.{digits}f}"
    text = text.replace("-", "−")
    return text.replace(".", ",") if lang == "ru" else text


def _decimal_axes(ax, lang: str, x: bool = True, y: bool = True, digits: int = 1):
    if lang != "ru":
        return
    fmt = lambda v, _: number(v, lang, digits)
    if x:
        ax.xaxis.set_major_formatter(fmt)
    if y:
        ax.yaxis.set_major_formatter(fmt)


def _percent_axis(axis):
    axis.set_major_formatter(lambda v, _: f"{v:.0%}")


def all_figures(d: dict, out: Path, lang: str) -> list[Path]:
    setup()
    out.mkdir(parents=True, exist_ok=True)
    L = LABELS[lang]
    figs = {
        "fig1_components": _components(eda.components(d), L, lang),
        "fig2_igpa_rules": _igpa_hist({r: eda.snapshot(d, r) for r in eda.RULES}, L, lang),
        "fig3_asu_visibility": _visibility(eda.completeness(d)["groups_by_year"], L),
        "fig4_igpa_persistence": _persistence(eda.year_panel(d), L, lang),
        "fig5_associations": _associations(eda.associations(d), L, FEATURES[lang], lang),
        "fig6_real_scenario": _real(eda.real_scenario(d), L, GROUPS[lang]),
    }
    paths = []
    for name, fig in figs.items():
        path = out / f"{name}.png"
        fig.savefig(path)
        plt.close(fig)
        paths.append(path)
    return paths


def _components(comp: pd.DataFrame, L, lang) -> plt.Figure:
    true = comp[comp.layer == "true"].set_index("rules").loc[list(eda.RULES)]
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    left = np.zeros(len(true))
    names = [L[f"rule_{r}"] for r in true.index]
    for color, part in zip(SERIES, ("gpa_part", "iros_part", "ssci_part")):
        ax.barh(names, true[part], left=left, color=color, height=0.55, label=L[part], **GAP)
        left += true[part].to_numpy()
    for y, total in enumerate(left):
        ax.text(total + 0.04, y, number(total, lang), va="center", color=INK)
    ax.set_xlim(0, 4)
    ax.invert_yaxis()
    ax.set_xlabel(L["f1_x"])
    ax.set_title(L["f1_title"])
    ax.grid(axis="y", visible=False)
    _decimal_axes(ax, lang, y=False)
    ax.legend(ncol=3, loc="upper left", bbox_to_anchor=(0, -0.32))
    return fig


def _igpa_hist(tables: dict, L, lang) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharex=True, sharey=True)
    bins = np.linspace(0.4, 3.0, 27)
    for ax, (rules, s), color in zip(axes, tables.items(), SERIES):
        ax.hist(s.true_igpa, bins=bins, color=color, edgecolor=SURFACE, linewidth=1)
        mean = s.true_igpa.mean()
        ax.axvline(mean, color=INK, linewidth=1, linestyle="--")
        ax.text(mean + 0.05, ax.get_ylim()[1] * 0.92, "x̄ = " + number(mean, lang), color=INK, fontsize=9)
        ax.set_title(L[f"rule_{rules}"], fontsize=10)
        ax.set_xlabel(L["f2_x"])
        ax.grid(axis="x", visible=False)
        _decimal_axes(ax, lang, y=False)
    axes[0].set_ylabel(L["f2_y"])
    fig.suptitle(L["f2_title"], x=0.01, ha="left", fontweight="bold", fontsize=11)
    fig.tight_layout()
    return fig


def _visibility(by_year: pd.DataFrame, L) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    labels = [f"{y}/{str(y + 1)[2:]}" for y in by_year.index]
    bottom = np.zeros(len(by_year))
    for color, key in zip(SERIES, ("none", "hidden", "part", "full")):
        ax.bar(labels, by_year[key], bottom=bottom, color=color, width=0.6, label=L[f"f3_{key}"], **GAP)
        bottom += by_year[key].to_numpy()
    ax.set_ylim(0, 1)
    _percent_axis(ax.yaxis)
    ax.set_ylabel(L["f3_y"])
    ax.set_title(L["f3_title"])
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=2, fontsize=9, **BELOW)
    return fig


def _persistence(p: pd.DataFrame, L, lang) -> plt.Figure:
    t = p[p.delta_true.notna()]
    fig, ax = plt.subplots(figsize=(5, 4.6))
    cmap = LinearSegmentedColormap.from_list("seq", SEQUENTIAL)
    hb = ax.hexbin(t.true_igpa, t.true_igpa_next, gridsize=40, cmap=cmap, mincnt=1, linewidths=0.2, edgecolors=SURFACE)
    lim = (0.5, 2.6)
    ax.plot(lim, lim, color=INK, linewidth=1)
    ax.plot(lim, (lim[0] - 0.1, lim[1] - 0.1), color=DIVERGING[2], linewidth=1.2, linestyle="--")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel(L["f4_x"])
    ax.set_ylabel(L["f4_y"])
    ax.set_title(L["f4_title"])
    _decimal_axes(ax, lang)
    handles = [Line2D([], [], color=INK, linewidth=1), Line2D([], [], color=DIVERGING[2], linewidth=1.2, linestyle="--")]
    ax.legend(handles, [L["f4_diag"], L["f4_risk"]], loc="upper left", fontsize=9)
    bar = fig.colorbar(hb, ax=ax, shrink=0.8)
    bar.outline.set_visible(False)
    bar.set_label(L["f2_y"], color=INK_2)
    return fig


def _associations(a: pd.DataFrame, L, names, lang) -> plt.Figure:
    a = a.assign(name=a.feature.map(lambda f: names.get(f, f))).sort_values("delta")
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    colors = [DIVERGING[0] if v < 0 else DIVERGING[2] for v in a.delta]
    ax.barh(a.name, a.delta, color=colors, height=0.6, **GAP)
    for y, v in enumerate(a.delta):
        ax.text(v + (0.012 if v >= 0 else -0.012), y, number(v, lang, sign=True), va="center",
                ha="left" if v >= 0 else "right", color=INK_2, fontsize=8)
    ax.axvline(0, color=INK, linewidth=0.8)
    lim = max(0.1, a.delta.abs().max() * 1.3)
    ax.set_xlim(-lim, lim)
    ax.set_xlabel(L["f5_x"])
    ax.set_title(L["f5_title"])
    ax.grid(axis="y", visible=False)
    _decimal_axes(ax, lang, y=False)
    return fig


def _real(r: pd.DataFrame, L, groups) -> plt.Figure:
    order = [g for g in groups if g in r.index]
    r = r.loc[order]
    x = np.arange(len(r))
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for i, (col, color) in enumerate(zip(("main", "real"), SERIES)):
        ax.bar(x + (i - 0.5) * 0.36, r[col], width=0.36, color=color, label=L[f"f6_{col}"], **GAP)
    ax.set_xticks(x, [groups[g].replace(" ", "\n", 1) for g in order], fontsize=9)
    ax.set_ylim(0, 0.6)
    _percent_axis(ax.yaxis)
    ax.set_ylabel(L["f6_y"])
    ax.set_title(L["f6_title"])
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=2, loc="upper left", bbox_to_anchor=(0, -0.28))
    return fig
