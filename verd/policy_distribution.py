"""
PolicyDistribution — sandsynlighedsvægtet fordeling over policetilstande.

En ``PolicyDistribution`` er en liste af (Policy, sandsynlighed)-par,
ét par per Markov-tilstand. Sandsynlighederne summer til 1.

Bruges som inddata og uddata i den sandsynlighedsvægtede fremregning.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from verd.policy import Policy

PolicyDistribution = list[tuple["Policy", float]]
"""
Liste af (Police, sandsynlighed)-par, én per Markov-tilstand.

Sandsynlighederne repræsenterer den marginale sandsynlighed for at
policen befinder sig i den pågældende tilstand på det givne tidspunkt.
De summer til 1 ved starten af fremregningen.
"""


def initial_distribution(policy: "Policy") -> PolicyDistribution:
    """
    Opret en initial ``PolicyDistribution`` for en ny police.

    Ved start befinder policen sig med sandsynlighed 1 i sin begyndelsestilstand
    (typisk ``PolicyState.I_LIVE``).

    Parameters
    ----------
    policy:
        Den police der skal fremregnes.

    Returns
    -------
    PolicyDistribution
        En liste med ét element: [(policy, 1.0)]
    """
    return [(policy, 1.0)]
