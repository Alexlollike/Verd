"""
Eksportering — konvertering af fremregningsresultater til DataFrame og CSV,
samt formateret output til stdout.

Funktioner:
    til_dataframe(skridt) → pandas.DataFrame
    eksporter_cashflows_csv(skridt, filsti) → None
    print_cashflow_tabel(skridt, n_rækker) → None
    print_policeoversigt(police, skridt, marked) → None
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    from verd.policy import Policy
    from verd.financial_market import FinancialMarket


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


def print_cashflow_tabel(skridt: list, n_rækker: int = 5) -> None:
    """
    Print en formateret cashflow-tabel til stdout.

    Viser de første ``n_rækker`` og de sidste ``n_rækker`` tidsstep,
    adskilt af en "..." linje, efterfulgt af totaler (sum over alle skridt).

    Kolonner: t, alder, p(I_LIVE), betinget depot, forventet depot,
    indbetaling, udbetaling, omkostning, enhedspris.

    Parameters
    ----------
    skridt:
        Output fra ``fremregn()`` — ``list[FremregningsSkridt]``.
    n_rækker:
        Antal rækker der vises fra toppen og bunden. Standard: 5.
    """
    HEADER = (
        f"{'t':>7}  {'Alder':>6}  {'p(I_LIVE)':>10}  "
        f"{'Bet. depot':>12}  {'Forv. depot':>12}  "
        f"{'Indbetal.':>11}  {'Udbetal.':>11}  {'Omk.':>9}  {'Kurs':>8}"
    )
    SEP = "-" * len(HEADER)

    def _format_row(s) -> str:
        il = s.i_live
        betinget = il.total_depot_dkk if il else 0.0
        forventet = il.forventet_depot_dkk if il else 0.0
        return (
            f"{s.t:>7.4f}  {s.alder:>6.2f}  "
            f"{(il.prob if il else 0.0):>10.6f}  "
            f"{betinget:>12,.0f}  {forventet:>12,.0f}  "
            f"{s.indbetaling_dkk:>11,.0f}  {s.udbetaling_dkk:>11,.0f}  "
            f"{s.omkostning_dkk:>9,.0f}  {s.enhedspris:>8.4f}"
        )

    print(HEADER)
    print(SEP)

    n = len(skridt)
    if n <= 2 * n_rækker:
        for s in skridt:
            print(_format_row(s))
    else:
        for s in skridt[:n_rækker]:
            print(_format_row(s))
        print(f"{'...':>7}")
        for s in skridt[-n_rækker:]:
            print(_format_row(s))

    # Totaler
    total_indbetaling = sum(s.indbetaling_dkk for s in skridt)
    total_udbetaling = sum(s.udbetaling_dkk for s in skridt)
    total_omkostning = sum(s.omkostning_dkk for s in skridt)
    print(SEP)
    print(
        f"{'TOTAL':>7}  {'':>6}  {'':>10}  "
        f"{'':>12}  {'':>12}  "
        f"{total_indbetaling:>11,.0f}  {total_udbetaling:>11,.0f}  "
        f"{total_omkostning:>9,.0f}  {'':>8}"
    )


def print_policeoversigt(
    police: "Policy",
    skridt: list,
    marked: "FinancialMarket",
) -> None:
    """
    Print en samlet politikrapport til stdout.

    Rapporten indeholder:
    1. Policestamdata (fødselsdato, tegningsdato, pensionsalder, depoter)
    2. Nøgletal (depotværdi ved t=0, sum af indbetalinger, sum af ydelser)
    3. Første og sidste 5 rækker af cashflowtabellen

    Parameters
    ----------
    police:
        Policyen der er fremregnet.
    skridt:
        Output fra ``fremregn()`` — ``list[FremregningsSkridt]``.
    marked:
        Det finansielle marked — bruges til at beregne DKK-værdier.
    """
    W = 70

    print("=" * W)
    print("POLICEOVERSIGT")
    print("=" * W)

    # --- Stamdata ---
    kurs_0 = marked.enhedspris(0.0)
    depot_dkk = police.depotvaerdi_dkk(kurs_0)

    print("STAMDATA")
    print("-" * W)
    print(f"  Fødselsdato             : {police.foedselsdato}")
    print(f"  Tegningsdato            : {police.tegningsdato}")
    print(f"  Pensionsalder           : {police.pensionsalder} år")
    print(f"  Tilstand                : {police.tilstand.value}")
    print(f"  Fase                    : {'Udbetaling' if police.er_under_udbetaling else 'Opsparing'}")
    print(f"  GruppeID                : {police.gruppe_id}")
    print(f"  OmkostningssatsID       : {police.omkostningssats_id}")
    print(f"  Løn                     : {police.loen:>12,.0f} DKK/år")
    print(f"  Indbetalingsprocent     : {police.indbetalingsprocent:.1%}")

    print()
    print("DEPOTER VED t=0  (enhedspris {:.4f} DKK/enhed)".format(kurs_0))
    print("-" * W)
    print(f"  Aldersopsparing         : {police.aldersopsparing * kurs_0:>12,.0f} DKK")
    print(f"  Ratepensionsopsparing   : {police.ratepensionsopsparing * kurs_0:>12,.0f} DKK")
    print(f"  Livrentedepot           : {police.livrentedepot * kurs_0:>12,.0f} DKK")
    print(f"  Depotværdi (total)      : {depot_dkk:>12,.0f} DKK")

    # --- Nøgletal ---
    total_indbetaling = sum(s.indbetaling_dkk for s in skridt)
    total_udbetaling = sum(s.udbetaling_dkk for s in skridt)
    total_omkostning = sum(s.omkostning_dkk for s in skridt)
    slut = skridt[-1]
    il_slut = slut.i_live
    slut_depot = il_slut.forventet_depot_dkk if il_slut else 0.0
    horizon_aar = slut.t

    print()
    print(f"NØGLETAL  (horisont: {horizon_aar:.1f} år, {len(skridt)} tidsstep)")
    print("-" * W)
    print(f"  Depotværdi t=0          : {depot_dkk:>12,.0f} DKK")
    print(f"  Forv. depot ved slutn.  : {slut_depot:>12,.0f} DKK")
    print(f"  Sum af indbetalinger    : {total_indbetaling:>12,.0f} DKK")
    print(f"  Sum af ydelser          : {total_udbetaling:>12,.0f} DKK")
    print(f"  Sum af omkostninger     : {total_omkostning:>12,.0f} DKK")
    print(f"  Slut-p(I_LIVE)          : {(il_slut.prob if il_slut else 0.0):.6f}")

    # --- Cashflow-tabel ---
    print()
    print("CASHFLOW-TABEL (første/sidste 5 rækker)")
    print("-" * W)
    print_cashflow_tabel(skridt, n_rækker=5)
    print("=" * W)
