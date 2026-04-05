"""
Omkostning — omkostningsmodeller for enkeltpolicer.

Omkostningerne er opdelt i tre typer:

    1. Indbetalingsomkostninger (pct. af indbetaling) — ikke implementeret i v1.0
       (sættes til 0 % per specifikation).

    2. AUM-omkostninger (pct. af depotværdi p.a.):
           c_AUM(t) = aum_rate × V_total(t)   [DKK/år]
       Trækkes løbende og reducerer depotet proportionalt.

    3. Stykomkostninger (fast beløb pr. police pr. år):
           c_styk(t) = styk_aar               [DKK/år]
       Trækkes månedligt (håndteres via dt i fremregningen).

Omkostningerne returneres som en enkelt samlet sats i DKK/år og lægges
oven på den eventuelt eksisterende ``CashflowSats.omkostning`` fra
``cashflow_funktion``. Fordeling på depoter sker i ``thiele_step``
proportionalt med depoternes relative størrelse.

Fabriksfunktionen ``standard_omkostning`` returnerer en
``OmkostningsFunktion`` med signaturen ``(Policy, t) -> float``,
klar til brug som ``omkostnings_funktion``-parameter i ``fremregn()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from verd.financial_market import FinancialMarket

from verd.policy import Policy

# Type-alias for omkostningsfunktioner
OmkostningsFunktion = Callable[[Policy, float], float]
"""Funktion der returnerer samlet omkostningssats i DKK/år for ét tidsstep."""


def nul_omkostning(policy: Policy, t: float) -> float:
    """
    Nul-omkostning — returnerer altid 0,0 DKK/år.

    Bruges som standardværdi når ingen omkostninger er specificeret.

    Parameters
    ----------
    policy:
        Ikke brugt.
    t:
        Ikke brugt.

    Returns
    -------
    float
        0.0 DKK/år.
    """
    return 0.0


def standard_omkostning(
    market: FinancialMarket,
    aum_rate: float = 0.005,
    styk_aar: float = 200.0,
) -> OmkostningsFunktion:
    """
    Fabriksfunktion: standard omkostningsmodel med AUM- og stykomkostninger.

    Returnerer en ``OmkostningsFunktion`` der beregner den samlede
    omkostningssats i DKK/år som:

        c(t) = aum_rate × V_total(t)  +  styk_aar

    hvor ``V_total(t)`` er den samlede betingede depotværdi i DKK:

        V_total(t) = (aldersopsparing + ratepensionsopsparing + livrentedepot)
                     × enhedspris(t)

    Indbetalingsomkostninger er 0 % per v1.0-specifikationen.

    Parameters
    ----------
    market:
        Finansielt marked — leverer enhedspris P(t) til DKK-konvertering.
    aum_rate:
        Årlig AUM-sats (andel af depotværdi). Standard: 0.005 (0,5 % p.a.).
    styk_aar:
        Fast stykomkostning i DKK/år. Standard: 200 DKK/år.

    Returns
    -------
    OmkostningsFunktion
        En funktion ``(Policy, t) -> float`` i DKK/år.
    """

    def _omk(policy: Policy, t: float) -> float:
        P_t = market.enhedspris(t)
        V_total = policy.total_enheder() * P_t
        # AUM-satsen er 0 når V_total = 0 (tomt depot giver ingen AUM-omkostning).
        # styk_aar opkræves derimod altid — uanset depotets størrelse — da
        # selskabets administrative udgifter til policeadministration er
        # uafhængige af depotværdien. Hvis V_total = 0 og styk_aar > 0,
        # vil thiele_step beregne en negativ depotændring, der afskæres til 0
        # med en advarsel. Dette er forventet adfærd for en police med tomt depot.
        return aum_rate * V_total + styk_aar

    return _omk
