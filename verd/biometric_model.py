"""
BiometricModel — abstrakt grundklasse for dødelighedsmodeller.

Leverer dødelighedsintensiteten µ(x) og afledte størrelser
som overlevelsessandsynlighed over et diskret tidsstep.

Diskretisering:
    Overlevelsessandsynlighed over dt år: p = exp(-µ(x) · dt)
    Dødssandsynlighed over dt år:        q = 1 - p
"""

import math
from abc import ABC, abstractmethod


class BiometricModel(ABC):
    """
    Abstrakt grundklasse for biometriske modeller.

    En konkret underklasse skal implementere ``mortality_intensity``,
    som returnerer dødelighedsintensiteten µ(x) ved alder x.

    BiometricModel er fuldstændigt uafhængig af ``FinancialMarket`` —
    de to modeller kobles kun i fremregningslaget.
    """

    @abstractmethod
    def mortality_intensity(self, alder: float) -> float:
        """
        Dødelighedsintensitet (hazard rate) µ(x) ved alder x.

        Parameters
        ----------
        alder:
            Forsikringstagers alder i år (kan være ikke-heltalsværdi).

        Returns
        -------
        float
            µ(x) ≥ 0, målt i år⁻¹.
        """
        ...

    def survival_probability(self, alder: float, dt: float) -> float:
        """
        Diskret overlevelsessandsynlighed over tidsstep dt.

        Beregnes ved at antage konstant intensitet over det korte interval dt:

            p(x, dt) = exp(-µ(x) · dt)

        Parameters
        ----------
        alder:
            Forsikringstagers alder i år ved starten af tidssteget.
        dt:
            Tidsstepstørrelse i år. Standard i fremregningen: dt = 1/12.

        Returns
        -------
        float
            Sandsynlighed for at overleve intervallet [alder, alder + dt].
            Altid i [0, 1].
        """
        return math.exp(-self.mortality_intensity(alder) * dt)

    def death_probability(self, alder: float, dt: float) -> float:
        """
        Diskret dødssandsynlighed over tidsstep dt.

            q(x, dt) = 1 - p(x, dt) = 1 - exp(-µ(x) · dt)

        Parameters
        ----------
        alder:
            Forsikringstagers alder i år ved starten af tidssteget.
        dt:
            Tidsstepstørrelse i år.

        Returns
        -------
        float
            Sandsynlighed for at dø i intervallet [alder, alder + dt].
            Altid i [0, 1].
        """
        return 1.0 - self.survival_probability(alder, dt)
