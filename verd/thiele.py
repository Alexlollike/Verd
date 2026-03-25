"""
Thiele — koblede differentialligninger for betingede forventede depoter.

De tre depoters udvikling er givet af et system af koblede Thiele-ligninger.
For depot i ∈ {aldersopsparing, ratepension, livrente} i tilstand I_LIVE:

    dV_i/dt = r·V_i(t) + π_i(t) - b_i(t) - c_i(t)  −  µ(x+t)·R_i(t)

hvor:
    r        = afkastrate (kraftens af rente)
    π_i(t)   = indbetalingssats til depot i (DKK/år)
    b_i(t)   = udbetalingssats fra depot i (DKK/år)
    c_i(t)   = omkostningssats for depot i (DKK/år)
    µ(x+t)   = dødelighedsintensitet for overgangen I_LIVE → DOED
    R_i(t)   = risikosum for depot i (DKK):

                R_i(t) = S_i^{dead}(t) + V_i^{DOED}(t) − V_i^{I_LIVE}(t)

                S_i^{dead}(t)  = lumpsum udbetalt fra depot i ved dødsfald
                V_i^{DOED}(t)  = reserve for depot i i DOED-tilstanden (typisk 0)
                V_i^{I_LIVE}(t) = reserve for depot i i I_LIVE-tilstanden

De tre ligninger er koblede: µ(x+t) er fælles, og risikosummerne R_i kan
afhænge af alle depot-værdier (f.eks. ved krydssubsidiering mellem depoter).

For et rent unit-link produkt uden ekstra dødsbenefit gælder:
    S_i^{dead}(t) = V_i^{I_LIVE}(t)  og  V_i^{DOED}(t) = 0
    ⟹  R_i(t) = 0  for alle i

Det biometriske led er **altid til stede** i ligningssystemet — også når
R_i = 0 — fordi det afspejler modellens struktur (eksplicit overgangsled).

I unit-link-form håndteres r·V_i(t) automatisk af enhedsprisens vækst
P(t) = P₀·exp(r·t). Euler-diskretiseringen for enhedstallet n_i = V_i/P:

    Δn_i = dt · [π_i − b_i − c_i − µ(x+t)·R_i] / P(t)

Overlevelsessandsynligheden opdateres separat i fremregningslaget:

    p(t+dt) = p(t) · exp(−µ(x+t)·dt)
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass

from verd.biometric_model import BiometricModel
from verd.financial_market import FinancialMarket
from verd.policy import Policy
from verd.policy_state import PolicyState


@dataclass
class RisikoSummer:
    """
    Risikosummer (DKK) for de tre depoter ved overgangen I_LIVE → DOED.

    Risikosummen for depot i er defineret som:

        R_i(t) = S_i^{dead}(t) + V_i^{DOED}(t) − V_i^{I_LIVE}(t)

    og indgår i Thieles ligning som det biometriske kopplingsled:

        dV_i/dt = ... − µ(x+t) · R_i(t)

    Fortolkning:
    - R_i > 0: selskabet har en nettoudgift ved dødsfald (f.eks. ydelsesgaranti)
    - R_i = 0: rent unit-link, ingen risikopræmie på depot i
    - R_i < 0: selskabet opnår en nettogevinst ved dødsfald (sjældent i praksis)

    Standard er R_i = 0 for alle depoter (rent unit-link uden ekstra dødsbenefit).

    Attributes
    ----------
    aldersopsparing:
        Risikosum for aldersopsparingsdepot (DKK).
    ratepension:
        Risikosum for ratepensionsdepot (DKK).
    livrente:
        Risikosum for livrentedepot (DKK).
    """

    aldersopsparing: float = 0.0
    ratepension: float = 0.0
    livrente: float = 0.0


@dataclass
class CashflowSats:
    """
    Cashflow-satser i DKK/år for ét tidsstep i Thiele-fremregningen.

    Alle satser er årsrater — multiplicer med ``dt`` for beløb i det aktuelle skridt.

    Attributes
    ----------
    indbetaling_aldersopsparing:
        Indbetalingssats til aldersopsparingsdepot (DKK/år).
    indbetaling_ratepension:
        Indbetalingssats til ratepensionsdepot (DKK/år).
    indbetaling_livrente:
        Indbetalingssats til livrentedepot (DKK/år).
    udbetaling_aldersopsparing:
        Udbetalingssats fra aldersopsparingsdepot (DKK/år).
    udbetaling_ratepension:
        Udbetalingssats fra ratepensionsdepot (DKK/år).
    udbetaling_livrente:
        Udbetalingssats fra livrentedepot (DKK/år).
    omkostning:
        Samlet omkostningssats (DKK/år). Fordeles proportionalt på depoterne
        i ``thiele_step`` baseret på depoternes relative størrelse.
    """

    indbetaling_aldersopsparing: float = 0.0
    indbetaling_ratepension: float = 0.0
    indbetaling_livrente: float = 0.0
    udbetaling_aldersopsparing: float = 0.0
    udbetaling_ratepension: float = 0.0
    udbetaling_livrente: float = 0.0
    omkostning: float = 0.0

    @property
    def total_indbetaling(self) -> float:
        """Samlet indbetalingssats på tværs af alle depoter (DKK/år)."""
        return (
            self.indbetaling_aldersopsparing
            + self.indbetaling_ratepension
            + self.indbetaling_livrente
        )

    @property
    def total_udbetaling(self) -> float:
        """Samlet udbetalingssats på tværs af alle depoter (DKK/år)."""
        return (
            self.udbetaling_aldersopsparing
            + self.udbetaling_ratepension
            + self.udbetaling_livrente
        )


def thiele_step(
    policy: Policy,
    t: float,
    dt: float,
    biometric: BiometricModel,
    market: FinancialMarket,
    cashflows: CashflowSats,
    risikosum: RisikoSummer = RisikoSummer(),
) -> Policy:
    """
    Ét diskret Euler-skridt af det koblede Thiele-ligningssystem.

    Fremregner de **betingede forventede depoter** givet tilstand I_LIVE
    over ét tidsstep [t, t+dt]. Alle tre depot-ODE'er inkluderer eksplicit
    det biometriske kopplingsled −µ(x+t)·R_i, selv når R_i = 0.

    Systemet af koblede differentialligninger:

        dV_ald/dt  = r·V_ald  + π_ald  − b_ald  − c_ald   − µ·R_ald
        dV_rate/dt = r·V_rate + π_rate − b_rate − c_rate  − µ·R_rate
        dV_liv/dt  = r·V_liv  + π_liv  − b_liv  − c_liv   − µ·R_liv

    Kobling: µ(x+t) er fælles for alle tre ligninger; R_i kan afhænge af
    samtlige depot-værdier (f.eks. krydssubsidiering).

    I unit-link-form håndteres r·V_i implicit via P(t) → P(t+dt).
    Euler-diskretisering for enhedstallet n_i = V_i / P(t):

        Δn_i = dt · [π_i − b_i − c_i − µ(x+t)·R_i] / P(t)

    Rækkefølge af operationer inden for tidssteget:
        1. Indbetalinger (π_i·dt) tilskrives som nye enheder ved P(t)
        2. Finansielt afkast: implicit via P(t) → P(t+dt) = P(t)·exp(r·dt)
        3. Biometrisk kopplingsled (−µ·R_i·dt) fratrækkes ved P(t)
        4. Udbetalinger (b_i·dt) og omkostninger (c_i·dt) fratrækkes ved P(t)
        (Overlevelsessandsynlighed opdateres eksternt i fremregningslaget)

    Parameters
    ----------
    policy:
        Policyen i tilstand I_LIVE på tidspunkt t.
        Depotværdier er i enheder (units).
    t:
        Tid i år fra tegningsdato (t=0 svarer til tegningsdato).
    dt:
        Tidsstep i år. Standard: 1/12 (månedligt).
    biometric:
        Biometrisk model — leverer µ(x+t) til det biometriske kopplingsled.
    market:
        Finansielt marked — leverer enhedspris P(t).
    cashflows:
        Cashflow-satser π_i, b_i, c_i i DKK/år for dette tidsstep.
    risikosum:
        Risikosummer R_i i DKK for de tre depoter.
        Standard: ``RisikoSummer()`` — alle R_i = 0 (rent unit-link).

    Returns
    -------
    Policy
        Ny policy med opdaterede depotenheder (betinget på overlevelse, I_LIVE).

    Raises
    ------
    ValueError
        Hvis policyen ikke er i tilstand I_LIVE.
    """
    if policy.tilstand != PolicyState.I_LIVE:
        raise ValueError(
            f"thiele_step kræver policy i tilstand I_LIVE, fik {policy.tilstand}"
        )

    alder = policy.alder_ved_tegning() + t
    mu = biometric.mortality_intensity(alder)
    P_t = market.enhedspris(t)

    # Fordel samlet omkostning proportionalt på depoterne efter enhedsantal.
    # Er alle depoter tomme, fordeles omkostningen ligeligt (1/3 hver).
    total_enh = policy.total_enheder()
    if total_enh > 0.0:
        w_ald = policy.aldersopsparing / total_enh
        w_rate = policy.ratepensionsopsparing / total_enh
        w_liv = policy.livrentedepot / total_enh
    else:
        w_ald = w_rate = w_liv = 1.0 / 3.0

    omk_ald = cashflows.omkostning * w_ald
    omk_rate = cashflows.omkostning * w_rate
    omk_liv = cashflows.omkostning * w_liv

    # Koblede Thiele-ligninger — Euler fremadskridende:
    #   Δn_i = dt · [π_i − b_i − c_i − µ·R_i] / P(t)
    #
    # Det biometriske led −µ·R_i er altid eksplicit til stede, selv når R_i = 0.
    ald_ny = policy.aldersopsparing + dt * (
        cashflows.indbetaling_aldersopsparing
        - cashflows.udbetaling_aldersopsparing
        - omk_ald
        - mu * risikosum.aldersopsparing
    ) / P_t

    rate_ny = policy.ratepensionsopsparing + dt * (
        cashflows.indbetaling_ratepension
        - cashflows.udbetaling_ratepension
        - omk_rate
        - mu * risikosum.ratepension
    ) / P_t

    liv_ny = policy.livrentedepot + dt * (
        cashflows.indbetaling_livrente
        - cashflows.udbetaling_livrente
        - omk_liv
        - mu * risikosum.livrente
    ) / P_t

    # Depoter kan ikke gå under nul (kortfristet numerisk fejl tillades ikke)
    return dataclasses.replace(
        policy,
        aldersopsparing=max(0.0, ald_ny),
        ratepensionsopsparing=max(0.0, rate_ny),
        livrentedepot=max(0.0, liv_ny),
    )
