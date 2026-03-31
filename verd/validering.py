"""
Validering — sanity checks for fremregningsresultater.

Funktioner:
    check_sandsynligheder(fordeling) → None
    check_p_alive_monoton(skridt) → None
    kør_alle_checks(police, skridt, marked) → None
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from verd.policy import Policy
    from verd.financial_market import FinancialMarket
    from verd.policy_distribution import PolicyDistribution


def check_sandsynligheder(fordeling: "PolicyDistribution", tolerance: float = 1e-9) -> None:
    """
    Verificér at sandsynlighederne i en PolicyDistribution summer til 1.

    Parameters
    ----------
    fordeling:
        Liste af (Policy, sandsynlighed)-par.
    tolerance:
        Maksimalt tilladt afvigelse fra 1.0. Standard: 1e-9.

    Raises
    ------
    ValueError
        Hvis |sum(sandsynligheder) - 1| > tolerance.
    """
    total = sum(s for _, s in fordeling)
    if abs(total - 1.0) > tolerance:
        raise ValueError(
            f"Sandsynligheder summer ikke til 1: sum = {total:.15f} "
            f"(afvigelse {abs(total - 1.0):.2e}, tolerance {tolerance:.2e})"
        )


def check_p_alive_monoton(skridt: list, tolerance: float = 1e-12) -> None:
    """
    Verificér at overlevelsessandsynligheden p(I_LIVE, t) er aftagende over tid.

    Tillader meget små numeriske stigninger op til ``tolerance``.

    Parameters
    ----------
    skridt:
        Output fra ``fremregn()`` — ``list[FremregningsSkridt]``.
    tolerance:
        Maksimalt tilladt stigning i p_alive mellem på hinanden følgende skridt.
        Standard: 1e-12.

    Raises
    ------
    ValueError
        Hvis p(I_LIVE) stiger med mere end ``tolerance`` i et tidsstep.
    """
    from verd.policy_state import PolicyState

    prev_p: float | None = None
    prev_t: float = 0.0

    for s in skridt:
        il = s.i_live
        p = il.prob if il is not None else 0.0

        if prev_p is not None and p > prev_p + tolerance:
            raise ValueError(
                f"p(I_LIVE) er stigende ved t={s.t:.4f}: "
                f"{prev_p:.10f} → {p:.10f} (stigning {p - prev_p:.2e})"
            )
        prev_p = p
        prev_t = s.t


def kør_alle_checks(
    police: "Policy",
    skridt: list,
    marked: "FinancialMarket",
) -> None:
    """
    Kør alle valideringschecks og kast ``ValueError`` ved første fejl.

    Checks der køres:
    1. Indledende policedistribution summer til 1 (afledt fra police).
    2. p(I_LIVE) er monotont aftagende gennem fremregningen.

    Parameters
    ----------
    police:
        Den fremregnede police (bruges til at konstruere initial fordeling).
    skridt:
        Output fra ``fremregn()`` — ``list[FremregningsSkridt]``.
    marked:
        Det finansielle marked (ikke brugt i nuværende checks; medtaget
        for fremtidig udvidelse).

    Raises
    ------
    ValueError
        Beskrivende fejlbesked fra det første check der fejler.
    """
    from verd.policy_distribution import initial_distribution

    fordeling = initial_distribution(police)
    check_sandsynligheder(fordeling)
    check_p_alive_monoton(skridt)
