"""
Fremregning — sandsynlighedsvægtet fremregning via Thieles differentialligning.

Fremregningen kombinerer to uafhængige lag:

    1. Betinget depotfremregning (Thiele):
       Givet at policen er I_LIVE fremregnes hvert depot ét Euler-skridt ad gangen:
           Δn_i = dt · (π_i - b_i - c_i) / P(t)

    2. Sandsynlighedsopdatering (biometri):
       Overlevelsessandsynligheden opdateres hvert skridt:
           p(t+dt) = p(t) · exp(-µ(x+t)·dt)

Det forventede depot (sandsynlighedsvægtet) på tidspunkt t er:
    E[V_i(t)] = p_I_LIVE(t) · V_i(t | I_LIVE)

Standardcashflow-funktionen ``simpel_opsparings_cashflow`` dækker opsparingsfasen:
    - Indbetalinger: loen × indbetalingsprocent, fordelt proportionalt på depoterne
    - Udbetalinger: 0 (ingen udbetalinger i opsparingsfase)
    - Omkostninger: 0 (opslagstabel defineres i Phase 2+)
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
from verd.thiele import CashflowSats, thiele_step

# Signatur for en cashflow-funktion: (policy, t) → CashflowSats
CashflowFunktion = Callable[[Policy, float], CashflowSats]


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
        dvs. p(t) = exp(-∫₀ᵗ µ(x+s) ds).
    aldersopsparing_dkk:
        Betinget forventet aldersopsparing i DKK (givet I_LIVE).
    ratepension_dkk:
        Betinget forventet ratepensionsopsparing i DKK (givet I_LIVE).
    livrente_dkk:
        Betinget forventet livrentedepot i DKK (givet I_LIVE).
    total_depot_dkk:
        Samlet betinget forventet depot i DKK (givet I_LIVE).
    forventet_depot_dkk:
        Sandsynlighedsvægtet forventet depot i DKK:
        = prob_i_live × total_depot_dkk
    indbetaling_dkk:
        Faktisk indbetalt beløb i dette tidsstep (DKK).
    udbetaling_dkk:
        Faktisk udbetalt beløb i dette tidsstep (DKK).
    omkostning_dkk:
        Faktisk omkostning i dette tidsstep (DKK).
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


def fremregn(
    distribution: PolicyDistribution,
    antal_skridt: int,
    biometric: BiometricModel,
    market: FinancialMarket,
    cashflow_funktion: CashflowFunktion = simpel_opsparings_cashflow,
    dt: float = 1.0 / 12.0,
    t_0: float = 0.0,
) -> list[FremregningsSkridt]:
    """
    Sandsynlighedsvægtet fremregning via Thieles differentialligning.

    Kombinerer to lag for hvert tidsstep:
      1. Thiele-skridt: fremregner det betingede depot givet I_LIVE
      2. Biometri-skridt: opdaterer overlevelsessandsynlighed

    Parameters
    ----------
    distribution:
        Initial ``PolicyDistribution``. Typisk fra ``initial_distribution(policy)``.
        Kun I_LIVE-tilstanden fremregnes; DOED-tilstanden er absorberende.
    antal_skridt:
        Antal tidsstep der fremregnes (f.eks. 12 × antal_år).
    biometric:
        Biometrisk model — leverer dødelighedsintensitet µ(x+t).
    market:
        Finansielt marked — leverer enhedspris P(t).
    cashflow_funktion:
        Funktion ``(Policy, t) → CashflowSats`` der beregner cashflows for hvert skridt.
        Standard: ``simpel_opsparings_cashflow``.
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
            enhedspris=P_t,
        )
    ]

    # -----------------------------------------------------------------------
    # Fremregningsløkke
    # -----------------------------------------------------------------------
    for _ in range(antal_skridt):
        alder = alder_ved_tegning + t
        cashflows = cashflow_funktion(policy, t)

        # 1. Indbetalinger + 2. Afkast (implicit) + 4. Udbetalinger/Omkostninger
        #    via Thieles ODE (biometri håndteres separat nedenfor)
        policy_ny = thiele_step(policy, t, dt, market, cashflows)

        # 3. Biometri: p(t+dt) = p(t) · exp(-µ(x+t)·dt)
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
                enhedspris=P_t_ny,
            )
        )

        policy = policy_ny
        prob_i_live = prob_i_live_ny

    return skridt
