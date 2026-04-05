"""
Overgang — definerer overgange og tilstandsrum i en Markov-model.

Et tilstandsrum er specificeret som en liste af ``Overgang``-objekter.
Hvert ``Overgang`` definerer:
    - En rettet kant i Markov-grafen (fra → til)
    - En overgangsintensitet µ_ij(alder)
    - En funktion der beregner risikosummen R_ij for dette overgang

``Tilstandsmodel`` samler overgangene og leverer hjælpemetoder til
fremregningslaget (hvilke overgange forlader en given tilstand, etc.).

Tilføjelse af en ny tilstand kræver:
    1. En ny værdi i ``PolicyState``-enum'et
    2. Nye ``Overgang``-objekter til/fra den nye tilstand
    3. En cashflow-funktion der håndterer ``policy.tilstand == NY_TILSTAND``
    — ingen ændringer i ``thiele_step`` eller ``fremregn``.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from verd.thiele import RisikoSummer, nul_risikosum

if TYPE_CHECKING:
    from verd.policy import Policy
    from verd.policy_state import PolicyState
    from verd.thiele import RisikosumFunktion


class OvergangsIntensitet(ABC):
    """
    Abstrakt overgangsintensitet µ_ij(alder) for en rettet Markov-overgang.

    Adskiller sig fra ``BiometricModel`` ved at repræsentere én specifik
    overgang (fra én tilstand til en anden), frem for en samlet dødelig-
    hedsmodel. Giver mulighed for at have forskellige intensiteter for
    f.eks. I_LIVE → DOED og INVALID → DOED.
    """

    @abstractmethod
    def intensitet(self, alder: float) -> float:
        """
        Overgangsintensitet µ_ij(alder) i år⁻¹.

        Parameters
        ----------
        alder:
            Forsikringstagers alder i år.

        Returns
        -------
        float
            µ_ij(alder) ≥ 0, målt i år⁻¹.
        """
        ...


@dataclass
class BiometriOvergangsIntensitet(OvergangsIntensitet):
    """
    Wrapper der bruger en ``BiometricModel`` som overgangsintensitet.

    Typisk brug: dødelighedsovergang I_LIVE → DOED med Gompertz-Makeham.

    Parameters
    ----------
    model:
        Biometrisk model — ``mortality_intensity`` bruges som µ_ij.
    """

    model: "BiometricModel"  # noqa: F821

    def intensitet(self, alder: float) -> float:
        """µ_ij(alder) = model.mortality_intensity(alder)."""
        return self.model.mortality_intensity(alder)


@dataclass
class KonstantOvergangsIntensitet(OvergangsIntensitet):
    """
    Konstantovergangsintensitet µ_ij uafhængig af alder.

    Typisk brug: invalidisering, reaktivering eller andre processer
    hvor intensiteten antages at være aldersuafhængig.

    Parameters
    ----------
    mu:
        Fast overgangsintensitet i år⁻¹.
    """

    mu: float

    def intensitet(self, alder: float) -> float:
        """µ_ij(alder) = mu (konstant)."""
        return self.mu


@dataclass
class Overgang:
    """
    En rettet Markov-overgang fra tilstand ``fra`` til tilstand ``til``.

    Indeholder overgangsintensiteten µ_ij og en funktion der beregner
    risikosummen R_ij for overgangen (beløbet der "skifter hænder" når
    overgangen finder sted, minus reserveforskellen).

    Attributes
    ----------
    fra:
        Afgangstilstand.
    til:
        Destinationstilstand.
    intensitet:
        Overgangsintensitet µ_ij(alder).
    risikosum_func:
        Funktion ``(Policy, t) → RisikoSummer`` der beregner R_ij per depot.
        Standard: ``nul_risikosum`` — R_ij = 0 for alle depoter.
    """

    fra: "PolicyState"
    til: "PolicyState"
    intensitet: OvergangsIntensitet
    risikosum_func: "RisikosumFunktion" = field(default=nul_risikosum)


@dataclass
class Tilstandsmodel:
    """
    Komplet beskrivelse af et Markov-tilstandsrum via dets overgange.

    Tilstandsrummet er implicit defineret af de tilstande der optræder
    i ``overgange`` som ``fra``- eller ``til``-tilstand.

    Attributes
    ----------
    overgange:
        Alle rettede overgange i modellen.
    """

    overgange: list[Overgang]

    def ud_overgange(self, fra: "PolicyState") -> list[Overgang]:
        """
        Returner alle udgående overgange fra tilstand ``fra``.

        Parameters
        ----------
        fra:
            Afgangstilstand.

        Returns
        -------
        list[Overgang]
            Liste af overgange med ``overgang.fra == fra``.
            Tom liste for absorberende tilstande.
        """
        return [o for o in self.overgange if o.fra == fra]

    def alle_tilstande(self) -> set["PolicyState"]:
        """
        Alle tilstande der indgår i modellen (fra- og til-tilstande).

        Returns
        -------
        set[PolicyState]
            Foreningsmængden af fra- og til-tilstande på tværs af overgangene.
        """
        tilstande: set["PolicyState"] = set()
        for o in self.overgange:
            tilstande.add(o.fra)
            tilstande.add(o.til)
        return tilstande

    def ikke_absorberende(self) -> set["PolicyState"]:
        """
        Tilstande med mindst én udgående overgang (ikke-absorberende).

        Absorberende tilstande (f.eks. DOED) har ingen udgående overgange
        og fremregnes ikke via Thiele — kun sandsynligheder opdateres.

        Returns
        -------
        set[PolicyState]
            Tilstande der optræder som ``fra``-tilstand i mindst ét overgang.
        """
        return {o.fra for o in self.overgange}

    def valider(self) -> None:
        """
        Validér at tilstandsmodellen er intern konsistent.

        Kontrollerer at der ikke er selvkoblinger (µ_ii). Selvkoblinger
        er matematisk meningsløse i en Markov-model: diagonalleddet i
        intensitetsmatricen er implicit defineret som −Σ_{j≠i} µ_ij og
        er ikke et selvstændigt overgang.

        Raises
        ------
        ValueError
            Hvis mindst ét overgang har identisk ``fra``- og ``til``-tilstand.
        """
        for o in self.overgange:
            if o.fra == o.til:
                raise ValueError(
                    f"Selvkobling ikke tilladt i Tilstandsmodel: "
                    f"{o.fra} → {o.til}. "
                    "Diagonalleddet −Σ_j µ_ij håndteres implicit af "
                    "Kolmogorov-fremadligningen."
                )
