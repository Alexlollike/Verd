"""
Plot — visualisering af sandsynlighedsvægtede tilstandsvise depoter.

Hovedfunktion: ``plot_fremregning()``

Layoutet er tre vertikale paneler:

    ┌─────────────────────────────────────────────────┐
    │ Panel 1 — Betingede depoter (givet I_LIVE)      │
    │   Stacked area per produkt: aldersopsparing,    │
    │   ratepension, livrente                          │
    ├─────────────────────────────────────────────────┤
    │ Panel 2 — Sandsynlighedsvægtede depoter         │
    │   E[V_d(t)] = p_I_LIVE(t) · V_d(t | I_LIVE)    │
    │   Stacked area per produkt                       │
    ├─────────────────────────────────────────────────┤
    │ Panel 3 — Overlevelsessandsynlighed p(I_LIVE)   │
    └─────────────────────────────────────────────────┘

Produkter med nul-initial-depot udelades fra legend og plot.
Pensionsalderen markeres med en lodret stiplet linje på tværs af alle paneler.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import matplotlib.figure

# Farvepalette — konsistent på tværs af paneler
_FARVER = {
    "aldersopsparing": "#4472C4",   # blå
    "ratepension":     "#ED7D31",   # orange
    "livrente":        "#70AD47",   # grøn
    "sandsynlighed":   "#7030A0",   # lilla
}

_LABELS = {
    "aldersopsparing": "Aldersopsparing",
    "ratepension":     "Ratepension",
    "livrente":        "Livrente",
}


def plot_fremregning(
    skridt: list,
    titel: str = "Depotudvikling — sandsynlighedsvægtede depoter",
    pensionsalder_t: float | None = None,
    figsize: tuple[float, float] = (11, 10),
    gem_fil: str | None = None,
) -> "matplotlib.figure.Figure":
    """
    Plot sandsynlighedsvægtede tilstandsvise depoter og del-depoter over tid.

    Tre paneler:
      1. **Betingede depoter** (givet I_LIVE) per produkt — viser hvad depot-
         værdien ville være hvis forsikringstager er i live. Stacked area.
      2. **Sandsynlighedsvægtede depoter** E[V_d(t)] per produkt — viser den
         forventede depotværdi inkl. mortalitetsrisiko. Stacked area.
      3. **Overlevelsessandsynlighed** p(I_LIVE) over tid.

    Produkter med startværdi = 0 udelades fra visualiseringen.

    Parameters
    ----------
    skridt:
        Output fra ``fremregn()`` — ``list[FremregningsSkridt]``.
    titel:
        Overskrift for hele figuren.
    pensionsalder_t:
        Tidspunktet (år fra tegningsdato) for pensionering, vises som
        lodret stiplet linje. ``None`` for ingen markering.
    figsize:
        Figurstørrelse i tommer ``(bredde, højde)``.
    gem_fil:
        Filsti til at gemme figuren (f.eks. ``"depot.png"``).
        ``None`` for ikke at gemme (vis med ``plt.show()``).

    Returns
    -------
    matplotlib.figure.Figure
        Den oprettede figur.
    """
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    t_vals = [s.t for s in skridt]

    # Udtræk I_LIVE-data for hvert tidsstep
    prob_vals = []
    ald_betinget, rate_betinget, liv_betinget = [], [], []
    ald_vaegtet, rate_vaegtet, liv_vaegtet = [], [], []

    for s in skridt:
        il = s.i_live
        if il is not None:
            prob_vals.append(il.prob)
            ald_betinget.append(il.aldersopsparing_dkk)
            rate_betinget.append(il.ratepension_dkk)
            liv_betinget.append(il.livrente_dkk)
            ald_vaegtet.append(il.prob * il.aldersopsparing_dkk)
            rate_vaegtet.append(il.prob * il.ratepension_dkk)
            liv_vaegtet.append(il.prob * il.livrente_dkk)
        else:
            prob_vals.append(0.0)
            ald_betinget.append(0.0); rate_betinget.append(0.0); liv_betinget.append(0.0)
            ald_vaegtet.append(0.0); rate_vaegtet.append(0.0); liv_vaegtet.append(0.0)

    # Afgør hvilke produkter der er aktive (startværdi > 0)
    aktive = {
        "aldersopsparing": ald_betinget[0] > 0.0,
        "ratepension":     rate_betinget[0] > 0.0,
        "livrente":        liv_betinget[0] > 0.0,
    }
    betinget_serier = {
        "aldersopsparing": ald_betinget,
        "ratepension":     rate_betinget,
        "livrente":        liv_betinget,
    }
    vaegtet_serier = {
        "aldersopsparing": ald_vaegtet,
        "ratepension":     rate_vaegtet,
        "livrente":        liv_vaegtet,
    }
    aktive_navne = [navn for navn, aktiv in aktive.items() if aktiv]

    # -----------------------------------------------------------------------
    # Figur og akser
    # -----------------------------------------------------------------------
    fig, akser = plt.subplots(
        3, 1,
        figsize=figsize,
        gridspec_kw={"height_ratios": [3, 3, 1.2]},
        sharex=True,
    )
    ax_betinget, ax_vaegtet, ax_prob = akser

    fig.suptitle(titel, fontsize=13, fontweight="bold", y=0.98)

    # -----------------------------------------------------------------------
    # Hjælpefunktion: stacked area + legend
    # -----------------------------------------------------------------------
    def _stacked_area(ax, serier: dict, y_label: str) -> None:
        ys = [serier[navn] for navn in aktive_navne]
        farver = [_FARVER[navn] for navn in aktive_navne]
        labels = [_LABELS[navn] for navn in aktive_navne]

        ax.stackplot(t_vals, ys, labels=labels, colors=farver, alpha=0.75)
        ax.set_ylabel(y_label, fontsize=10)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: f"{x/1_000:.0f}k")
        )
        ax.legend(loc="upper left", fontsize=9, framealpha=0.7)
        ax.grid(axis="y", linestyle=":", linewidth=0.6, color="grey", alpha=0.5)
        ax.set_axisbelow(True)

    # Panel 1 — betingede depoter
    _stacked_area(ax_betinget, betinget_serier, "DKK (givet I_LIVE)")
    ax_betinget.set_title("Betingede depoter | V_d(t | I_LIVE)", fontsize=10, loc="left")

    # Panel 2 — sandsynlighedsvægtede depoter
    _stacked_area(ax_vaegtet, vaegtet_serier, "DKK (forventet)")
    ax_vaegtet.set_title("Sandsynlighedsvægtede depoter | E[V_d(t)]", fontsize=10, loc="left")

    # Panel 3 — p(I_LIVE)
    ax_prob.plot(t_vals, prob_vals, color=_FARVER["sandsynlighed"], linewidth=1.8)
    ax_prob.set_ylabel("p(I_LIVE)", fontsize=10)
    ax_prob.set_ylim(0, 1.05)
    ax_prob.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
    ax_prob.grid(axis="y", linestyle=":", linewidth=0.6, color="grey", alpha=0.5)
    ax_prob.set_axisbelow(True)
    ax_prob.set_title("Overlevelsessandsynlighed | p(I_LIVE)", fontsize=10, loc="left")

    # X-akse: tid i år
    ax_prob.set_xlabel("Tid fra tegningsdato (år)", fontsize=10)

    # -----------------------------------------------------------------------
    # Pensionsalder-markering
    # -----------------------------------------------------------------------
    if pensionsalder_t is not None:
        for ax in akser:
            ax.axvline(
                pensionsalder_t,
                color="black",
                linestyle="--",
                linewidth=1.0,
                alpha=0.6,
            )
        # Annotation på øverste panel
        y_top = ax_betinget.get_ylim()[1]
        ax_betinget.annotate(
            f"Pension\n(t={pensionsalder_t:.0f} år)",
            xy=(pensionsalder_t, y_top * 0.92),
            fontsize=8,
            ha="center",
            color="black",
            alpha=0.7,
        )

    fig.tight_layout(rect=[0, 0, 1, 0.97])

    if gem_fil is not None:
        fig.savefig(gem_fil, dpi=150, bbox_inches="tight")

    return fig
