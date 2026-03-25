"""
Fremregning — sandsynlighedsvægtet fremregning via koblede Thiele-ligninger.

Fremregningen kombinerer to lag for hvert tidsstep:

    1. Betinget depotfremregning (koblede Thiele-ligninger):
       Givet tilstand I_LIVE fremregnes hvert depot via:
           Δn_i = dt · [π_i − b_i − c_i − µ(x+t)·R_i] / P(t)
       Det biometriske led −µ·R_i er altid eksplicit, selv når R_i = 0.

    2. Sandsynlighedsopdatering (Kolmogorov fremadligning):
       Overlevelsessandsynligheden opdateres hvert skridt:
           p(t+dt) = p(t) · exp(−µ(x+t)·dt)

Det forventede depot (sandsynlighedsvægtet) på tidspunkt t er:
    E[V_i(t)] = p_I_LIVE(t) · V_i(t | I_LIVE)

Standardfunktioner:
    ``simpel_opsparings_cashflow`` — indbetaling = loen × indbetalingsprocent,
                                      fordelt proportionalt på depoterne
    ``nul_risikosum``              — R_i = 0 for alle i (rent unit-link)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from verd.biometric_model import BiometricModel
from verd.financial_market import FinancialMarket
from verd.policy import Policy
from verd.policy_distribution import PolicyDistribution
from verd.policy_state import PolicyState
from verd.thiele import CashflowSats, RisikoSummer, thiele_step

# Signaturer for brugerdefinerbare funktioner
CashflowFunktion = Callable[[Policy, float], CashflowSats]
RisikosumFunktion = Callable[[Policy, float], RisikoSummer]


@dataclass
class FremregningsSkridt:
    """
    Resultat af ét tidsstep i den sandsynlighedsvægtede fremregning.

    Attributes
    ----------
    t:
        Tid fra tegningsdato i år.
    alder:
        Forsikringstagers alder på tidspunkt t.
    prob_i_live:
        Sandsynlighed for at policen er I_LIVE på tidspunkt t,
        dvs. p(t) = exp(−∫₀ᵗ µ(x+s) ds).
    aldersopsparing_dkk:
        Betinget forventet aldersopsparing i DKK (givet I_LIVE).
    ratepension_dkk:
        Betinget forventet ratepensionsopsparing i DKK (givet I_LIVE).
    livrente_dkk:
        Betinget forventet livrentedepot i DKK (givet I_LIVE).
    total_depot_dkk:
        Samlet betinget forventet depot i DKK (givet I_LIVE).
    forventet_depot_dkk:
        Sandsynlighedsvægtet forventet depot i DKK = prob_i_live × total_depot_dkk.
    indbetaling_dkk:
        Indbetalt beløb i dette tidsstep (DKK).
    udbetaling_dkk:
        Udbetalt beløb i dette tidsstep (DKK).
    omkostning_dkk:
        Omkostning i dette tidsstep (DKK).
    risikosum_dkk:
        Samlet risikosum R_ald + R_rate + R_liv (DKK) — biometrisk kopplingsled.
    enhedspris:
        Enhedspris P(t) på tidspunkt t (DKK/enhed).
    """

    t: float
    alder: float
    prob_i_live: float
    aldersopsparing_dkk: float
    ratepension_dkk: float
    livrente_dkk: float
    total_depot_dkk: float
    forventet_depot_dkk: float
    indbetaling_dkk: float
    udbetaling_dkk: float
    omkostning_dkk: float
    risikosum_dkk: float
    enhedspris: float


def simpel_opsparings_cashflow(policy: Policy, t: float) -> CashflowSats:
    """
    Standard cashflow-funktion for opsparingsfasen.

    Indbetalingen er ``loen × indbetalingsprocent`` og fordeles proportionalt
    til de tre depoter baseret på deres aktuelle enhedsandele.
    Er alle depoter tomme, fordeles indbetalingen ligeligt (1/3 til hvert depot).

    Udbetalinger og omkostninger er nul i denne simple model
    (omkostningssatser defineres i Phase 2+).

    Parameters
    ----------
    policy:
        Policyen hvis cashflows skal beregnes.
    t:
        Tid fra tegningsdato (år) — ikke brugt i denne simple model.

    Returns
    -------
    CashflowSats
        Cashflow-satser i DKK/år.
    """
    if policy.er_under_udbetaling:
        return CashflowSats()

    indbetaling_aar = policy.loen * policy.indbetalingsprocent

    total_enh = policy.total_enheder()
    if total_enh > 0.0:
        f_ald = policy.aldersopsparing / total_enh
        f_rate = policy.ratepensionsopsparing / total_enh
        f_liv = policy.livrentedepot / total_enh
    else:
        f_ald = f_rate = f_liv = 1.0 / 3.0

    return CashflowSats(
        indbetaling_aldersopsparing=indbetaling_aar * f_ald,
        indbetaling_ratepension=indbetaling_aar * f_rate,
        indbetaling_livrente=indbetaling_aar * f_liv,
    )


def nul_risikosum(policy: Policy, t: float) -> RisikoSummer:
    """
    Standard risikosum-funktion for rent unit-link uden ekstra dødsbenefit.

    Returnerer R_i = 0 for alle depoter, svarende til at dødsbenefit = depot-
    værdi og DOED-reserven er nul:

        R_i = S_i^{dead} + V_i^{DOED} − V_i^{I_LIVE} = V_i − 0 − V_i = 0

    Det biometriske led −µ·R_i bidrager numerisk med nul, men er strukturelt
    til stede i ligningerne (se ``thiele_step``).

    Parameters
    ----------
    policy:
        Ikke brugt — returnerer altid ``RisikoSummer()`` med nulværdier.
    t:
        Ikke brugt.

    Returns
    -------
    RisikoSummer
        Risikosum med R_ald = R_rate = R_liv = 0.
    """
    return RisikoSummer()


def fremregn(
    distribution: PolicyDistribution,
    antal_skridt: int,
    biometric: BiometricModel,
    market: FinancialMarket,
    cashflow_funktion: CashflowFunktion = simpel_opsparings_cashflow,
    risikosum_funktion: RisikosumFunktion = nul_risikosum,
    dt: float = 1.0 / 12.0,
    t_0: float = 0.0,
) -> list[FremregningsSkridt]:
    """
    Sandsynlighedsvægtet fremregning via koblede Thiele-ligninger.

    Kombinerer for hvert tidsstep:
      1. Koblede Thiele-skridt: fremregner det betingede depot givet I_LIVE,
         inkl. det biometriske kopplingsled −µ·R_i for hvert depot.
      2. Biometri-skridt: opdaterer overlevelsessandsynlighed via Kolmogorov.

    Parameters
    ----------
    distribution:
        Initial ``PolicyDistribution``. Typisk fra ``initial_distribution(policy)``.
        Kun I_LIVE-tilstanden fremregnes; DOED-tilstanden er absorberende.
    antal_skridt:
        Antal tidsstep der fremregnes (f.eks. 12 × antal_år).
    biometric:
        Biometrisk model — leverer µ(x+t) til både Thiele-steget og
        sandsynlighedsopdateringen.
    market:
        Finansielt marked — leverer enhedspris P(t).
    cashflow_funktion:
        ``(Policy, t) → CashflowSats`` — cashflows for hvert skridt.
        Standard: ``simpel_opsparings_cashflow``.
    risikosum_funktion:
        ``(Policy, t) → RisikoSummer`` — risikosummer R_i per skridt.
        Standard: ``nul_risikosum`` (rent unit-link, alle R_i = 0).
    dt:
        Tidsstep i år. Standard: 1/12 (månedligt).
    t_0:
        Starttidspunkt i år fra tegningsdato. Standard: 0.0.

    Returns
    -------
    list[FremregningsSkridt]
        Tidsserie af fremregningsresultater. Første element svarer til t_0
        (initial tilstand); hvert efterfølgende element er ét skridt fremme.

    Raises
    ------
    ValueError
        Hvis ``distribution`` ikke indeholder en I_LIVE-tilstand.
    """
    i_live_entries = [
        (p, prob) for p, prob in distribution if p.tilstand == PolicyState.I_LIVE
    ]
    if not i_live_entries:
        raise ValueError("distribution indeholder ingen I_LIVE-tilstand")

    policy, prob_i_live = i_live_entries[0]
    alder_ved_tegning = policy.alder_ved_tegning()
    t = t_0

    # -----------------------------------------------------------------------
    # Initial tilstand (t = t_0)
    # -----------------------------------------------------------------------
    P_t = market.enhedspris(t)
    total_depot_dkk = policy.total_enheder() * P_t

    skridt: list[FremregningsSkridt] = [
        FremregningsSkridt(
            t=t,
            alder=alder_ved_tegning + t,
            prob_i_live=prob_i_live,
            aldersopsparing_dkk=policy.aldersopsparing * P_t,
            ratepension_dkk=policy.ratepensionsopsparing * P_t,
            livrente_dkk=policy.livrentedepot * P_t,
            total_depot_dkk=total_depot_dkk,
            forventet_depot_dkk=prob_i_live * total_depot_dkk,
            indbetaling_dkk=0.0,
            udbetaling_dkk=0.0,
            omkostning_dkk=0.0,
            risikosum_dkk=0.0,
            enhedspris=P_t,
        )
    ]

    # -----------------------------------------------------------------------
    # Fremregningsløkke
    # -----------------------------------------------------------------------
    for _ in range(antal_skridt):
        alder = alder_ved_tegning + t
        cashflows = cashflow_funktion(policy, t)
        risikosum = risikosum_funktion(policy, t)

        # Koblede Thiele-skridt: betinget depotfremregning inkl. −µ·R_i
        policy_ny = thiele_step(policy, t, dt, biometric, market, cashflows, risikosum)

        # Kolmogorov fremadligning: p(t+dt) = p(t) · exp(−µ(x+t)·dt)
        mu = biometric.mortality_intensity(alder)
        prob_i_live_ny = prob_i_live * math.exp(-mu * dt)

        t += dt
        P_t_ny = market.enhedspris(t)
        total_depot_dkk_ny = policy_ny.total_enheder() * P_t_ny

        skridt.append(
            FremregningsSkridt(
                t=t,
                alder=alder_ved_tegning + t,
                prob_i_live=prob_i_live_ny,
                aldersopsparing_dkk=policy_ny.aldersopsparing * P_t_ny,
                ratepension_dkk=policy_ny.ratepensionsopsparing * P_t_ny,
                livrente_dkk=policy_ny.livrentedepot * P_t_ny,
                total_depot_dkk=total_depot_dkk_ny,
                forventet_depot_dkk=prob_i_live_ny * total_depot_dkk_ny,
                indbetaling_dkk=cashflows.total_indbetaling * dt,
                udbetaling_dkk=cashflows.total_udbetaling * dt,
                omkostning_dkk=cashflows.omkostning * dt,
                risikosum_dkk=(
                    risikosum.aldersopsparing
                    + risikosum.ratepension
                    + risikosum.livrente
                ),
                enhedspris=P_t_ny,
            )
        )

        policy = policy_ny
        prob_i_live = prob_i_live_ny

    return skridt
