"""
Udbetaling — cashflow-funktioner for udbetalingsfasen.

Beregner ydelser (benefit payments) for ratepension og livrente i udbetalingsfasen.

Ratepension: niveau-udbetaling over ratepensionsvarighed år (sikker annuitet).
    Ydelsen beregnes som V_rate(t) / ä_sikker(remaining_years) og genberegnes
    hvert skridt — dette sikrer præcis udtømning ved periodens slut.

Livrente: livsvarig niveau-udbetaling.
    Ydelsen beregnes som V_liv(t) / ä_x(alder) og genberegnes hvert skridt,
    hvor ä_x er den sandsynlighedsvægtede diskonterede livsannuitet:

        ä_x = Σ_{k=0}^{K-1} dt · v^k · k_p_x

    k_p_x approximeres via Euler-diskretisering af overlevelsesligningen.

Fabriksfunktionen ``udbetaling_cashflow_funktion`` returnerer en funktion
med signaturen ``(Policy, t) -> CashflowSats``, klar til brug i ``fremregn()``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from verd.biometric_model import BiometricModel
    from verd.financial_market import FinancialMarket

from verd.policy import Policy
from verd.policy_state import PolicyState
from verd.thiele import CashflowSats


def livrente_annuitet(
    alder: float,
    biometric: BiometricModel,
    market: FinancialMarket,
    t0: float,
    dt: float = 1.0 / 12.0,
    max_alder: float = 120.0,
) -> float:
    """
    Beregn livrenteannuiteten ä_x = Σ_{k=0}^{K-1} dt · v^k · k_p_x.

    Summerer fremtidige diskonterede overlevelsessandsynligheder frem til max_alder.
    Diskontfaktoren v^k beregnes generelt som:

        v^k = P(t0) / P(t0 + k·dt)

    Dette er korrekt for alle markedstyper inkl. tidsvarierende renter.
    k_p_x approximeres ved Euler-diskretisering:

        k_p_x ≈ exp(-Σ_{j=0}^{k-1} µ(alder+j·dt) · dt)

    Parameters
    ----------
    alder:
        Nuværende alder i år (udgangspunktet for annuitetberegningen).
    biometric:
        Biometrisk model der leverer dødelighedsintensiteten µ(x).
    market:
        Finansielt marked — leverer enhedspris til beregning af diskontfaktor.
    t0:
        Tidspunktet (år fra tegningsdato) svarende til den givne alder.
    dt:
        Tidsstep i år. Standard: 1/12 (månedligt).
    max_alder:
        Øvre aldersgrænse for summering. Standard: 120 år.

        Begrundelse: Ved standard Gompertz-Makeham-parametre (alpha≈0.0005,
        beta≈0.00004, sigma≈0.09) er µ(120) ≈ 2.0 år⁻¹, svarende til at
        sandsynligheden for at overleve ét år fra alder 120 er under 14 %.
        Hale-bidraget fra alder > 120 er under 0.01 DKK pr. 100.000 DKK
        depot ved r ≥ 0.01. For meget lave mortalitetsintensiteter eller
        renter bør max_alder øges manuelt.

    Returns
    -------
    float
        Livrenteannuiteten ä_x i år.
    """
    K = max(1, round((max_alder - alder) / dt))
    P_t0 = market.enhedspris(t0)

    annuitet = 0.0
    log_kpx = 0.0  # log(k_p_x); starter ved 0 (0_p_x = 1)

    for k in range(K):
        kpx = math.exp(log_kpx)
        # Generel diskontfaktor: v^k = P(t0) / P(t0 + k·dt)
        # Korrekt for alle markedstyper inkl. tidsvarierende renter.
        discount = P_t0 / market.enhedspris(t0 + k * dt)
        annuitet += dt * discount * kpx

        mu = biometric.mortality_intensity(alder + k * dt)
        log_kpx -= mu * dt

    return annuitet


def sikker_annuitet(
    remaining_years: float,
    market: FinancialMarket,
    t0: float,
    dt: float = 1.0 / 12.0,
) -> float:
    """
    Beregn sikker annuitet (certain annuity) ä_n = Σ_{k=0}^{N-1} dt · v^k.

    Bruges til ratepension, der udbetales uanset biometri over en fast periode.
    Diskontfaktoren v^k beregnes generelt som P(t0) / P(t0 + k·dt), korrekt
    for alle markedstyper inkl. tidsvarierende renter.

    Parameters
    ----------
    remaining_years:
        Resterende udbetalingsperiode i år.
    market:
        Finansielt marked — leverer enhedspris til beregning af diskontfaktor.
    t0:
        Aktuelt tidspunkt (år fra tegningsdato).
    dt:
        Tidsstep i år. Standard: 1/12 (månedligt).

    Returns
    -------
    float
        Sikker annuitet ä_n i år.
    """
    N = max(1, round(remaining_years / dt))
    P_t0 = market.enhedspris(t0)
    return sum(dt * P_t0 / market.enhedspris(t0 + k * dt) for k in range(N))


def udbetaling_cashflow_funktion(
    biometric: BiometricModel,
    market: FinancialMarket,
    t_pension: float,
    dt: float = 1.0 / 12.0,
) -> "Callable[[Policy, float], CashflowSats]":  # noqa: F821
    """
    Fabriksfunktion: returnerer cashflow-funktion for udbetalingsfasen.

    Den returnerede funktion beregner ydelser (DKK/år) for alle tre depottyper
    baseret på aktuelt depot og annuitetfaktorer genberegnet hvert skridt:

        b_ald      = V_ald_dkk  / dt          (engangsudbetaling ved pensionering)
        b_rate     = V_rate_dkk / ä_n(remaining_years)
        b_livrente = V_liv_dkk  / ä_x(alder)

    Genberegning hvert skridt sikrer korrekt udtømning under hensyntagen til
    afkast og mortalitet.

    Aldersopsparing udbetales altid som engangsudbetaling i første skridt af
    udbetalingsfasen (``b_ald = V_ald / dt``). Dette tømmer depotet i ét skridt;
    efterfølgende skridt har policy.aldersopsparing ≈ 0, så b_ald ≈ 0 automatisk.

    Parameters
    ----------
    biometric:
        Biometrisk model til beregning af livrenteannuitet ä_x.
    market:
        Finansielt marked til beregning af diskontfaktorer.
    t_pension:
        Tidspunktet for pensionering (år fra tegningsdato).
    dt:
        Tidsstep i år. Standard: 1/12 (månedligt).

    Returns
    -------
    CashflowFunktion
        En funktion ``(Policy, t) -> CashflowSats`` til brug i ``fremregn()``.
    """

    def _cashflow(policy: Policy, t: float) -> CashflowSats:
        if not policy.er_under_udbetaling or policy.tilstand != PolicyState.I_LIVE:
            return CashflowSats()

        P_t = market.enhedspris(t)
        alder = policy.alder_ved_tegning() + t

        # Aldersopsparing: engangsudbetaling — tøm depotet i ét skridt
        b_ald = policy.aldersopsparing * P_t / dt if policy.aldersopsparing > 0.0 else 0.0

        # Ratepension: niveau-udbetaling over resterende ratepensionsperiode.
        # Ved periodens afslutning (remaining_rate_years ≤ dt) udbetales
        # restdepot som engangsudbetaling — analogt med aldersopsparing.
        # Dette sikrer at depotet udtømmes fuldt ud og ikke efterlades som
        # en restbeholdning der kun nedbringes via omkostninger.
        remaining_rate_years = policy.ratepensionsvarighed - (t - t_pension)
        if remaining_rate_years > dt and policy.ratepensionsopsparing > 0.0:
            V_rate = policy.ratepensionsopsparing * P_t
            ann_rate = sikker_annuitet(remaining_rate_years, market, t, dt)
            b_rate = V_rate / ann_rate if ann_rate > 0.0 else 0.0
        elif 0.0 < remaining_rate_years <= dt and policy.ratepensionsopsparing > 0.0:
            # Sidste skridt: engangsudbetaling af restdepot
            b_rate = policy.ratepensionsopsparing * P_t / dt
        else:
            b_rate = 0.0

        # Livrente: livsvarig niveau-udbetaling
        if policy.livrentedepot > 0.0:
            V_liv = policy.livrentedepot * P_t
            ann_liv = livrente_annuitet(alder, biometric, market, t, dt)
            b_livrente = V_liv / ann_liv if ann_liv > 0.0 else 0.0
        else:
            b_livrente = 0.0

        return CashflowSats(
            b_aldersopsparing=b_ald,
            b_ratepension=b_rate,
            b_livrente=b_livrente,
        )

    return _cashflow
