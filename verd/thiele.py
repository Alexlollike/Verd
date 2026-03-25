"""
Thiele — koblede differentialligninger for betingede forventede depoter.

De tre depoters udvikling er givet af et system af koblede Thiele-ligninger.
For depot d ∈ {aldersopsparing, ratepension, livrente} i tilstand i:

    dV_d/dt = r·V_d(t) + π_d(t) − b_d(t) − c_d(t)  −  Σ_j µ_ij(x+t)·R_ij_d(t)

hvor:
    r          = afkastrate (kraftens af rente)
    π_d(t)     = indbetalingssats til depot d (DKK/år)
    b_d(t)     = udbetalingssats fra depot d (DKK/år)
    c_d(t)     = omkostningssats for depot d (DKK/år)
    µ_ij(x+t)  = overgangsintensitet fra tilstand i til tilstand j
    R_ij_d(t)  = risikosum for depot d ved overgang i → j (DKK):
                     R_ij_d = S_ij_d + V_j_d − V_i_d

Summen løber over alle udgående overgange j ≠ i.

Det finansielle led r·V_d(t) håndteres automatisk via enhedsprisens vækst
P(t) = P₀·exp(r·t). Enhedstallet n_d = V_d/P ændres kun af nettopenge-
strømmene. Euler-diskretiseringen for depot d (Euler fremadskridende):

    Δn_d = dt · [π_d − b_d − c_d − Σ_j µ_ij·R_ij_d] / P(t)

Overlevelsessandsynligheder opdateres via Kolmogorov fremadligning i
fremregningslaget (ikke her).

``thiele_step`` er et rent matematisk Euler-skridt — den kalder ingen
modeller selv. Kaldende kode (``fremregn``) forudberegner µ_ij og R_ij_d
og sender dem som en liste af ``(µ_ij, R_ij)``-par.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from verd.financial_market import FinancialMarket
from verd.policy import Policy
from verd.policy_state import PolicyState


@dataclass
class RisikoSummer:
    """
    Risikosummer (DKK) for de tre depoter ved én Markov-overgang i → j.

    Risikosummen for depot d er defineret som:

        R_ij_d(t) = S_ij_d(t) + V_j_d(t) − V_i_d(t)

    og indgår i Thieles ligning som det biometriske kopplingsled:

        dV_d/dt = ... − µ_ij(x+t) · R_ij_d(t)

    Fortolkning:
    - R_ij_d > 0: nettoudgift ved overgangen (f.eks. ydelsesgaranti)
    - R_ij_d = 0: rent unit-link, ingen risikopræmie på depot d
    - R_ij_d < 0: nettogevinst ved overgangen (sjældent i praksis)

    Standard er R_ij_d = 0 for alle depoter (rent unit-link).

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


# Type-alias for risikosum-funktion — importeres af fremregning og overgang
RisikosumFunktion = "Callable[[Policy, float], RisikoSummer]"


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
    market: FinancialMarket,
    cashflows: CashflowSats,
    overgangs_led: list[tuple[float, RisikoSummer]],
) -> Policy:
    """
    Ét diskret Euler-skridt af det koblede Thiele-ligningssystem.

    Fremregner de **betingede forventede depoter** givet en aktiv tilstand
    over ét tidsstep [t, t+dt]. Alle tre depot-ODE'er inkluderer eksplicit
    det biometriske kopplingsled −µ_ij·R_ij_d for hvert udgående overgang,
    selv når R_ij_d = 0.

    Systemet af koblede differentialligninger for depot d:

        dV_d/dt = r·V_d + π_d − b_d − c_d  −  Σ_j µ_ij·R_ij_d

    I unit-link-form håndteres r·V_d implicit via P(t) → P(t+dt).
    Euler-diskretisering for enhedstallet n_d = V_d / P(t):

        Δn_d = dt · [π_d − b_d − c_d − Σ_j µ_ij·R_ij_d] / P(t)

    Rækkefølge af operationer inden for tidssteget:
        1. Indbetalinger (π_d·dt) tilskrives som nye enheder ved P(t)
        2. Finansielt afkast: implicit via P(t) → P(t+dt) = P(t)·exp(r·dt)
        3. Biometriske kopplingsled (−Σ_j µ_ij·R_ij_d·dt) fratrækkes ved P(t)
        4. Udbetalinger (b_d·dt) og omkostninger (c_d·dt) fratrækkes ved P(t)
        (Tilstandssandsynligheder opdateres eksternt via Kolmogorov)

    Parameters
    ----------
    policy:
        Policyen i en aktiv tilstand på tidspunkt t.
        Depotværdier er i enheder (units).
    t:
        Tid i år fra tegningsdato (t=0 svarer til tegningsdato).
    dt:
        Tidsstep i år. Standard: 1/12 (månedligt).
    market:
        Finansielt marked — leverer enhedspris P(t).
    cashflows:
        Cashflow-satser π_d, b_d, c_d i DKK/år for dette tidsstep.
    overgangs_led:
        Liste af ``(µ_ij, R_ij)``-par, ét per udgående overgang fra
        ``policy.tilstand``. µ_ij er intensitetsværdien (float, år⁻¹)
        forudberegnet af kaldende kode. Tom liste for absorberende tilstande.

    Returns
    -------
    Policy
        Ny policy med opdaterede depotenheder (betinget på aktiv tilstand).

    Raises
    ------
    ValueError
        Hvis policyen er i en absorberende tilstand og ``overgangs_led``
        er ikke-tom (inkonsistent input).
    """
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

    # Summér biometriske kopplingsled over alle udgående overgange:
    #   Σ_j µ_ij · R_ij_d   for depot d ∈ {ald, rate, liv}
    sum_bio_ald = sum(mu_ij * r.aldersopsparing for mu_ij, r in overgangs_led)
    sum_bio_rate = sum(mu_ij * r.ratepension for mu_ij, r in overgangs_led)
    sum_bio_liv = sum(mu_ij * r.livrente for mu_ij, r in overgangs_led)

    # Koblede Thiele-ligninger — Euler fremadskridende:
    #   Δn_d = dt · [π_d − b_d − c_d − Σ_j µ_ij·R_ij_d] / P(t)
    #
    # Det biometriske led er altid eksplicit til stede, selv når R_ij_d = 0.
    ald_ny = policy.aldersopsparing + dt * (
        cashflows.indbetaling_aldersopsparing
        - cashflows.udbetaling_aldersopsparing
        - omk_ald
        - sum_bio_ald
    ) / P_t

    rate_ny = policy.ratepensionsopsparing + dt * (
        cashflows.indbetaling_ratepension
        - cashflows.udbetaling_ratepension
        - omk_rate
        - sum_bio_rate
    ) / P_t

    liv_ny = policy.livrentedepot + dt * (
        cashflows.indbetaling_livrente
        - cashflows.udbetaling_livrente
        - omk_liv
        - sum_bio_liv
    ) / P_t

    # Depoter kan ikke gå under nul (kortfristet numerisk fejl tillades ikke)
    return dataclasses.replace(
        policy,
        aldersopsparing=max(0.0, ald_ny),
        ratepensionsopsparing=max(0.0, rate_ny),
        livrentedepot=max(0.0, liv_ny),
    )
