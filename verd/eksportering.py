"""
Eksportering — konvertering af fremregningsresultater til DataFrame og CSV.

Funktioner:
    til_dataframe(skridt) → pandas.DataFrame
    eksporter_cashflows_csv(skridt, filsti) → None
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def til_dataframe(skridt: list) -> "pd.DataFrame":
    """
    Konvertér en liste af ``FremregningsSkridt`` til en pandas DataFrame.

    Én række per tidsstep. Kolonner:

    Tid og alder:
        ``t``                           — tid i år fra tegningsdato
        ``alder``                       — forsikringstagers alder på tidspunkt t

    Sandsynlighed:
        ``p_i_live``                    — overlevelsessandsynlighed p(I_LIVE, t)

    Aggregerede beløb (DKK per tidsstep):
        ``indbetaling_dkk``             — indbetaling i dette tidsstep
        ``udbetaling_dkk``              — udbetaling i dette tidsstep
        ``omkostning_dkk``              — omkostning i dette tidsstep

    Enhedspris:
        ``enhedspris``                  — enhedspris P(t) i DKK/enhed

    Betingede depoter — V_d(t | I_LIVE) (givet at forsikringstager er i live):
        ``betinget_aldersopsparing_dkk``
        ``betinget_ratepension_dkk``
        ``betinget_livrente_dkk``
        ``betinget_depot_dkk``          — sum af de tre betingede depoter

    Sandsynlighedsvægtede depoter — E[V_d(t)] = p(t) × V_d(t | I_LIVE):
        ``forventet_aldersopsparing_dkk``
        ``forventet_ratepension_dkk``
        ``forventet_livrente_dkk``
        ``forventet_depot_dkk``

    Cashflow-rater (DKK/år, fra CashflowSats for I_LIVE):
        ``b_aldersopsparing``           — betalingsrate aldersopsparing
        ``b_ratepension``               — betalingsrate ratepension
        ``b_livrente``                  — betalingsrate livrente
        ``b_omkostning``                — omkostningsrate

    Parameters
    ----------
    skridt:
        Output fra ``fremregn()`` — ``list[FremregningsSkridt]``.

    Returns
    -------
    pandas.DataFrame
        DataFrame med én række per tidsstep og kolonnerne beskrevet ovenfor.
    """
    import pandas as pd

    rækker = []
    for s in skridt:
        il = s.i_live
        if il is not None:
            p = il.prob
            betinget_ald = il.aldersopsparing_dkk
            betinget_rate = il.ratepension_dkk
            betinget_liv = il.livrente_dkk
            betinget_depot = il.total_depot_dkk
            forventet_ald = p * betinget_ald
            forventet_rate = p * betinget_rate
            forventet_liv = p * betinget_liv
            forventet_depot = il.forventet_depot_dkk
        else:
            p = 0.0
            betinget_ald = betinget_rate = betinget_liv = betinget_depot = 0.0
            forventet_ald = forventet_rate = forventet_liv = forventet_depot = 0.0

        cf = s.cashflows_i_live

        rækker.append({
            "t":                              s.t,
            "alder":                          s.alder,
            "p_i_live":                       p,
            "indbetaling_dkk":                s.indbetaling_dkk,
            "udbetaling_dkk":                 s.udbetaling_dkk,
            "omkostning_dkk":                 s.omkostning_dkk,
            "enhedspris":                     s.enhedspris,
            "betinget_aldersopsparing_dkk":   betinget_ald,
            "betinget_ratepension_dkk":       betinget_rate,
            "betinget_livrente_dkk":          betinget_liv,
            "betinget_depot_dkk":             betinget_depot,
            "forventet_aldersopsparing_dkk":  forventet_ald,
            "forventet_ratepension_dkk":      forventet_rate,
            "forventet_livrente_dkk":         forventet_liv,
            "forventet_depot_dkk":            forventet_depot,
            "b_aldersopsparing":              cf.b_aldersopsparing,
            "b_ratepension":                  cf.b_ratepension,
            "b_livrente":                     cf.b_livrente,
            "b_omkostning":                   cf.omkostning,
        })

    return pd.DataFrame(rækker)


def eksporter_cashflows_csv(skridt: list, filsti: str) -> None:
    """
    Eksportér fremregningsresultater til en CSV-fil.

    Kalder ``til_dataframe(skridt)`` og gemmer resultatet med
    ``DataFrame.to_csv(filsti, index=False)``.

    Parameters
    ----------
    skridt:
        Output fra ``fremregn()`` — ``list[FremregningsSkridt]``.
    filsti:
        Sti til CSV-filen der skal oprettes (f.eks. ``"fremregning.csv"``).
        Eksisterende fil overskrives.
    """
    df = til_dataframe(skridt)
    df.to_csv(filsti, index=False)
