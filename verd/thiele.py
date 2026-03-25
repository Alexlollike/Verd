"""
Thiele — diskretiseret fremregning via Thieles differentialligning.

Thieles differentialligning for et rent unit-link produkt (to-tilstands Markov-model):

    dV_i(t)/dt = r·V_i(t) + π_i(t) - b_i(t) - c_i(t) - µ(x+t)·[S_i(t) - V_i(t)]

hvor:
    r       = afkastrate (kraftens af rente)
    π_i(t)  = indbetalingssats til depot i (DKK/år)
    b_i(t)  = udbetalingssats fra depot i (DKK/år)
    c_i(t)  = omkostningssats for depot i (DKK/år)
    µ(x+t)  = dødelighedsintensitet ved alder x+t
    S_i(t)  = dødsbenefit fra depot i ved dødsfald

For et rent unit-link produkt uden ekstra dødsbenefit gælder S_i(t) = V_i(t),
og det biometriske led forsvinder fra depotsligningen:

    dV_i/dt = r·V_i(t) + π_i(t) - b_i(t) - c_i(t)

Det finansielle led r·V_i(t) håndteres **automatisk** via enhedsprisens
eksponentielle vækst P(t) = P₀·exp(r·t). Enhedstallet n_i(t) = V_i(t)/P(t)
ændres kun af nettopengestrømmene (Euler fremadskridende):

    Δn_i = dt · (π_i - b_i - c_i) / P(t)

Overlevelsessandsynligheden opdateres **eksternt** i fremregningslaget, ikke her:

    p(t+dt) = p(t) · exp(-µ(x+t)·dt)
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass

from verd.policy import Policy
from verd.policy_state import PolicyState
from verd.financial_market import FinancialMarket


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
) -> Policy:
    """
    Ét diskret Euler-skridt af Thieles differentialligning for de betingede
    forventede depoter givet at policen er i tilstand I_LIVE.

    Thieles ligning reduceret for unit-link uden ekstra dødsbenefit:

        dV_i/dt = r·V_i(t) + π_i(t) - b_i(t) - c_i(t)

    I unit-link-form: enhedsprisen håndterer r·V_i, og kun nettopenge-
    strømmene ændrer enhedsbestanden:

        Δn_i = dt · (π_i - b_i - c_i) / P(t)

    Rækkefølge af operationer inden for tidssteget:
        1. Indbetalinger (π·dt) tilskrives som nye enheder ved P(t)
        2. Finansielt afkast: implicit via P(t) → P(t+dt) = P(t)·exp(r·dt)
        3. Biometri: håndteres eksternt i fremregningslaget
        4. Udbetalinger (b·dt) og omkostninger (c·dt) fratrækkes ved P(t)

    Parameters
    ----------
    policy:
        Policyen i tilstand I_LIVE på tidspunkt t.
        Depotværdier er i enheder (units).
    t:
        Tid i år fra tegningsdato (t=0 svarer til tegningsdato).
    dt:
        Tidsstep i år. Standard: 1/12 (månedligt).
    market:
        Finansielt marked — leverer enhedspris P(t).
    cashflows:
        Cashflow-satser i DKK/år for dette tidsstep.

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

    # Euler-skridt: Δn_i = dt · (π_i - b_i - c_i) / P(t)
    ald_ny = policy.aldersopsparing + dt * (
        cashflows.indbetaling_aldersopsparing
        - cashflows.udbetaling_aldersopsparing
        - omk_ald
    ) / P_t

    rate_ny = policy.ratepensionsopsparing + dt * (
        cashflows.indbetaling_ratepension
        - cashflows.udbetaling_ratepension
        - omk_rate
    ) / P_t

    liv_ny = policy.livrentedepot + dt * (
        cashflows.indbetaling_livrente
        - cashflows.udbetaling_livrente
        - omk_liv
    ) / P_t

    # Depoter kan ikke gå under nul (kortfristet numerisk fejl tillades ikke)
    return dataclasses.replace(
        policy,
        aldersopsparing=max(0.0, ald_ny),
        ratepensionsopsparing=max(0.0, rate_ny),
        livrentedepot=max(0.0, liv_ny),
    )
