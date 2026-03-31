"""
Risiko — risikodækninger og risikobundter.

En del af bruttopræmien finansierer rene risikoprodukter (dødsfald, TAE, SUL)
inden nettopræmien allokeres til opsparingsdepotterne.

Betalingsstrømmens struktur:

    π_brutto(t)
      − risikopraemie(t)          ← finansierer dødsfald/TAE/SUL-dækninger
      = π_netto(t)
          → ratepension            ← op til skattemæssig beløbsgrænse
          → aldersopsparing        ← op til skattemæssig beløbsgrænse
          → livrente               ← resterende (ingen beløbsgrænse)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RisikoDaekning:
    """
    Én enkelt risikodækning med tilhørende præmie.

    Attributes
    ----------
    navn:
        Beskrivende navn, fx "Dødsfald", "TAE" eller "SUL".
    aarlig_praemie_dkk:
        Årlig præmie for dækningen i DKK. Trækkes fra bruttopræmien inden
        allokering til opsparingsdepotter.
    """

    navn: str
    aarlig_praemie_dkk: float


@dataclass
class RisikoBundle:
    """
    Samling af risikodækninger knyttet til én police.

    Den samlede risikopræmie fratrækkes bruttopræmien i hvert tidsstep, inden
    nettopræmien allokeres til opsparingsdepotterne via ``PraemieFlow.beregn()``.

    Attributes
    ----------
    daekninger:
        Liste af ``RisikoDaekning``-objekter, ét per produkt.
    """

    daekninger: list[RisikoDaekning] = field(default_factory=list)

    @property
    def aarlig_praemie_dkk(self) -> float:
        """Samlet årlig risikopræmie (DKK/år) — sum over alle dækninger."""
        return sum(d.aarlig_praemie_dkk for d in self.daekninger)

    @property
    def maanedlig_praemie_dkk(self) -> float:
        """Samlet månedlig risikopræmie (DKK/måned) = aarlig_praemie_dkk / 12."""
        return self.aarlig_praemie_dkk / 12.0


#: Standardbundtet med dødsfald-, TAE- og SUL-dækning.
#: Samlet: 1.500 kr/år = 125 kr/måned.
STANDARD_RISIKO_BUNDLE = RisikoBundle(
    daekninger=[
        RisikoDaekning(navn="Dødsfald", aarlig_praemie_dkk=500.0),
        RisikoDaekning(navn="TAE", aarlig_praemie_dkk=700.0),
        RisikoDaekning(navn="SUL", aarlig_praemie_dkk=300.0),
    ]
)
