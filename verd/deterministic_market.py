"""
DeterministicMarket — deterministisk finansielt marked med konstant afkastrate.

Enhedsprisen vokser eksponentielt med en fast kontinuert rente r:

    enhedspris(t) = enhedspris_0 · exp(r · t)

Afkastet afspejles udelukkende som en stigning i enhedsprisen — antallet
af enheder i depoterne ændres ikke af afkastet alene.

Valg af kontinuert rente (frem for effektiv rente) er konsistent med
den kontinuerte formulering af Thieles differentialligning.
"""

import math
from dataclasses import dataclass, field

from verd.financial_market import FinancialMarket


@dataclass
class DeterministicMarket(FinancialMarket):
    """
    Deterministisk marked med konstant kontinuert afkastrate.

    Enhedsprisen følger:

        enhedspris(t) = enhedspris_0 · exp(r · t)

    Attributes
    ----------
    r:
        Kontinuert årlig afkastrate (f.eks. 0.05 = 5 % p.a.).
    enhedspris_0:
        Enhedspris ved t=0 (tegningsdato) i DKK/enhed. Standard: 1.0.
    """

    r: float
    enhedspris_0: float = field(default=1.0)

    def enhedspris(self, t: float) -> float:
        """
        Beregn enhedsprisen (NAV) ved tidspunkt t.

            enhedspris(t) = enhedspris_0 · exp(r · t)

        Parameters
        ----------
        t:
            Tid i år fra tegningsdato. t=0 giver ``enhedspris_0``.

        Returns
        -------
        float
            Enhedspris i DKK/enhed ved tidspunkt t.
        """
        return self.enhedspris_0 * math.exp(self.r * t)
