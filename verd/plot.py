"""
Plot — visualisering af sandsynlighedsvægtede tilstandsvise depoter og ydelser.

Offentlige funktioner:
    plot_fremregning(skridt, ...)       — plot direkte fra FremregningsSkridt-liste
    plot_fra_dataframe(df, ...)         — plot fra pandas DataFrame (f.eks. læst fra CSV)

Layoutet er fire vertikale paneler:

    ┌─────────────────────────────────────────────────┐
    │ Panel 1 — Betingede depoter (givet I_LIVE)      │
    │   Stacked area per produkt: aldersopsparing,    │
    │   ratepension, livrente                          │
    ├─────────────────────────────────────────────────┤
    │ Panel 2 — Sandsynlighedsvægtede depoter         │
    │   E[V_d(t)] = p_I_LIVE(t) · V_d(t | I_LIVE)    │
    │   Stacked area per produkt                       │
    ├─────────────────────────────────────────────────┤
    │ Panel 3 — Ydelser (DKK/år)                      │
    │   Udbetalinger per produkt — stacked area.       │
    │   Viser benefit-niveau under udbetalingsfasen.  │
    ├─────────────────────────────────────────────────┤
    │ Panel 4 — Overlevelsessandsynlighed p(I_LIVE)   │
    └─────────────────────────────────────────────────┘

Produkter med nul-initial-depot udelades fra legend og plot.
Pensionsalderen markeres med en lodret stiplet linje på tværs af alle paneler.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import matplotlib.figure
    import pandas as pd

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


def _plot_fra_arrays(
    t_vals: list[float],
    prob_vals: list[float],
    ald_betinget: list[float],
    rate_betinget: list[float],
    liv_betinget: list[float],
    ald_vaegtet: list[float],
    rate_vaegtet: list[float],
    liv_vaegtet: list[float],
    udb_rate_vals: list[float],
    udb_liv_vals: list[float],
    titel: str,
    pensionsalder_t: float | None,
    figsize: tuple[float, float],
    gem_fil: str | None,
) -> "matplotlib.figure.Figure":
    """
    Intern hjælpefunktion — tegner de fire paneler ud fra forudberegnede arrays.

    Kaldes af ``plot_fremregning`` og ``plot_fra_dataframe``.
    """
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    # Afgør hvilke produkter der er aktive i depot-panelerne (startværdi > 0)
    aktive_depot = {
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
    aktive_depot_navne = [navn for navn, aktiv in aktive_depot.items() if aktiv]

    # Afgør hvilke produkter der har ydelser (max > 0)
    ydelse_serier = {
        "ratepension": udb_rate_vals,
        "livrente":    udb_liv_vals,
    }
    aktive_ydelse_navne = [
        navn for navn, vals in ydelse_serier.items() if max(vals) > 0.0
    ]

    # -----------------------------------------------------------------------
    # Figur og akser
    # -----------------------------------------------------------------------
    fig, akser = plt.subplots(
        4, 1,
        figsize=figsize,
        gridspec_kw={"height_ratios": [3, 3, 2, 1.2]},
        sharex=True,
    )
    ax_betinget, ax_vaegtet, ax_ydelser, ax_prob = akser

    fig.suptitle(titel, fontsize=13, fontweight="bold", y=0.99)

    # -----------------------------------------------------------------------
    # Hjælpefunktion: stacked area + legend
    # -----------------------------------------------------------------------
    def _stacked_area(ax, navne: list[str], serier: dict, y_label: str) -> None:
        ys = [serier[navn] for navn in navne]
        farver = [_FARVER[navn] for navn in navne]
        labels = [_LABELS[navn] for navn in navne]

        ax.stackplot(t_vals, ys, labels=labels, colors=farver, alpha=0.75)
        ax.set_ylabel(y_label, fontsize=10)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: f"{x/1_000:.0f}k")
        )
        ax.legend(loc="upper left", fontsize=9, framealpha=0.7)
        ax.grid(axis="y", linestyle=":", linewidth=0.6, color="grey", alpha=0.5)
        ax.set_axisbelow(True)

    # Panel 1 — betingede depoter
    _stacked_area(ax_betinget, aktive_depot_navne, betinget_serier, "DKK (givet I_LIVE)")
    ax_betinget.set_title("Betingede depoter | V_d(t | I_LIVE)", fontsize=10, loc="left")

    # Panel 2 — sandsynlighedsvægtede depoter
    _stacked_area(ax_vaegtet, aktive_depot_navne, vaegtet_serier, "DKK (forventet)")
    ax_vaegtet.set_title("Sandsynlighedsvægtede depoter | E[V_d(t)]", fontsize=10, loc="left")

    # Panel 3 — ydelser
    if aktive_ydelse_navne:
        _stacked_area(ax_ydelser, aktive_ydelse_navne, ydelse_serier, "DKK/år")
    else:
        ax_ydelser.set_ylabel("DKK/år", fontsize=10)
    ax_ydelser.set_title("Ydelser per produkt | b_d(t)", fontsize=10, loc="left")

    # Panel 4 — p(I_LIVE)
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
        y_top = ax_betinget.get_ylim()[1]
        ax_betinget.annotate(
            f"Pension\n(t={pensionsalder_t:.0f} år)",
            xy=(pensionsalder_t, y_top * 0.92),
            fontsize=8,
            ha="center",
            color="black",
            alpha=0.7,
        )

    fig.tight_layout(rect=[0, 0, 1, 0.98])

    if gem_fil is not None:
        fig.savefig(gem_fil, dpi=150, bbox_inches="tight")

    return fig


def plot_fremregning(
    skridt: list,
    titel: str = "Depotudvikling — sandsynlighedsvægtede depoter",
    pensionsalder_t: float | None = None,
    figsize: tuple[float, float] = (11, 13),
    gem_fil: str | None = None,
) -> "matplotlib.figure.Figure":
    """
    Plot sandsynlighedsvægtede tilstandsvise depoter, ydelser og p(I_LIVE) over tid.

    Fire paneler:
      1. **Betingede depoter** (givet I_LIVE) per produkt — depotværdien givet
         at forsikringstager er i live. Stacked area.
      2. **Sandsynlighedsvægtede depoter** E[V_d(t)] per produkt — forventet
         depotværdi inkl. mortalitetsrisiko. Stacked area.
      3. **Ydelser** (DKK/år) per produkt — benefit-udbetalinger i
         udbetalingsfasen. Stacked area.
      4. **Overlevelsessandsynlighed** p(I_LIVE) over tid.

    Produkter med startværdi = 0 udelades fra depot-panelerne.
    Ydelsespanelet viser kun produkter med positive udbetalinger.

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
        ``None`` for ikke at gemme.

    Returns
    -------
    matplotlib.figure.Figure
        Den oprettede figur.
    """
    t_vals = [s.t for s in skridt]

    prob_vals = []
    ald_betinget, rate_betinget, liv_betinget = [], [], []
    ald_vaegtet, rate_vaegtet, liv_vaegtet = [], [], []
    udb_rate_vals, udb_liv_vals = [], []

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
            ald_betinget.append(0.0)
            rate_betinget.append(0.0)
            liv_betinget.append(0.0)
            ald_vaegtet.append(0.0)
            rate_vaegtet.append(0.0)
            liv_vaegtet.append(0.0)

        cf = s.cashflows_i_live
        udb_rate_vals.append(max(cf.b_ratepension, 0.0))
        udb_liv_vals.append(max(cf.b_livrente, 0.0))

    return _plot_fra_arrays(
        t_vals=t_vals,
        prob_vals=prob_vals,
        ald_betinget=ald_betinget,
        rate_betinget=rate_betinget,
        liv_betinget=liv_betinget,
        ald_vaegtet=ald_vaegtet,
        rate_vaegtet=rate_vaegtet,
        liv_vaegtet=liv_vaegtet,
        udb_rate_vals=udb_rate_vals,
        udb_liv_vals=udb_liv_vals,
        titel=titel,
        pensionsalder_t=pensionsalder_t,
        figsize=figsize,
        gem_fil=gem_fil,
    )


def plot_fra_dataframe(
    df: "pd.DataFrame",
    titel: str = "Depotudvikling — sandsynlighedsvægtede depoter",
    pensionsalder_t: float | None = None,
    figsize: tuple[float, float] = (11, 13),
    gem_fil: str | None = None,
) -> "matplotlib.figure.Figure":
    """
    Plot sandsynlighedsvægtede tilstandsvise depoter, ydelser og p(I_LIVE) over tid.

    Identisk layout som ``plot_fremregning``, men læser fra en pandas DataFrame —
    f.eks. indlæst fra en CSV genereret af ``eksporter_cashflows_csv()``.

    Forventede kolonner i ``df`` (alle produceret af ``til_dataframe()``):
        ``t``, ``p_i_live``,
        ``betinget_aldersopsparing_dkk``, ``betinget_ratepension_dkk``, ``betinget_livrente_dkk``,
        ``forventet_aldersopsparing_dkk``, ``forventet_ratepension_dkk``, ``forventet_livrente_dkk``,
        ``b_ratepension``, ``b_livrente``

    Parameters
    ----------
    df:
        DataFrame med fremregningsdata — typisk ``pd.read_csv("fremregning.csv")``.
    titel:
        Overskrift for hele figuren.
    pensionsalder_t:
        Tidspunktet (år fra tegningsdato) for pensionering, vises som
        lodret stiplet linje. ``None`` for ingen markering.
    figsize:
        Figurstørrelse i tommer ``(bredde, højde)``.
    gem_fil:
        Filsti til at gemme figuren (f.eks. ``"depot.png"``).
        ``None`` for ikke at gemme.

    Returns
    -------
    matplotlib.figure.Figure
        Den oprettede figur.
    """
    return _plot_fra_arrays(
        t_vals=df["t"].tolist(),
        prob_vals=df["p_i_live"].tolist(),
        ald_betinget=df["betinget_aldersopsparing_dkk"].tolist(),
        rate_betinget=df["betinget_ratepension_dkk"].tolist(),
        liv_betinget=df["betinget_livrente_dkk"].tolist(),
        ald_vaegtet=df["forventet_aldersopsparing_dkk"].tolist(),
        rate_vaegtet=df["forventet_ratepension_dkk"].tolist(),
        liv_vaegtet=df["forventet_livrente_dkk"].tolist(),
        udb_rate_vals=df["b_ratepension"].clip(lower=0).tolist(),
        udb_liv_vals=df["b_livrente"].clip(lower=0).tolist(),
        titel=titel,
        pensionsalder_t=pensionsalder_t,
        figsize=figsize,
        gem_fil=gem_fil,
    )
