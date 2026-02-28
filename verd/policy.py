"""
Policy — Markov-tilstandsvektor for en enkeltpolice (unit-link produkt).

Alle depotværdier opbevares som enheder (units) af fonden.
DKK-værdier beregnes ved at gange med den aktuelle enhedspris:
    depotværdi (DKK) = enheder × enhedspris

Indkommende præmier omregnes til enheder:
    enheder = DKK / enhedspris

Udbetalende ydelser omregnes fra enheder:
    DKK = enheder × enhedspris
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from verd.policy_state import PolicyState


@dataclass
class Policy:
    """
    Repræsenterer en enkelt forsikringspolicys tilstand på et givent tidspunkt.

    Bruges som Markov-tilstandsvektor i den sandsynlighedsvægtede fremregning.
    Alle depotbeløb er opgjort i **enheder** (fund units), ikke DKK.

    Attributes
    ----------
    foedselsdato:
        Forsikringstagers fødselsdato.
    tegningsdato:
        Den dato policen er oprettet (tegnet).
    pensionsalder:
        Planlagt pensioneringsalder i hele år. Bemærk: ``er_under_udbetaling``
        styrer den faktiske tilstand — forsikringstager kan vælge at udskyde.
    er_under_udbetaling:
        True hvis policen er i udbetalingsfasen, False hvis i opsparingsfasen.
    gruppe_id:
        Nøgle til dødelighedsintensitets-opslagstabel (defineres i Phase 2+).
    omkostningssats_id:
        Nøgle til omkostningssats-opslagstabel (defineres i Phase 2+).
    loen:
        Forsikringstagers løn i DKK/år (bruges til indbetalingsberegning).
    indbetalingsprocent:
        Andel af løn der indbetales til depot (f.eks. 0.15 = 15 %).
    aldersopsparing:
        Antal enheder (units) i aldersopsparingsdepot.
    ratepensionsopsparing:
        Antal enheder (units) i ratepensionsdepot.
    ratepensionsvarighed:
        Udbetalingsperiode for ratepension i hele år.
    livrentedepot:
        Antal enheder (units) i livrentedepot.
    tilstand:
        Nuværende Markov-tilstand. Standard: ``PolicyState.I_LIVE``.
    """

    foedselsdato: date
    tegningsdato: date
    pensionsalder: int
    er_under_udbetaling: bool
    gruppe_id: str
    omkostningssats_id: str
    loen: float
    indbetalingsprocent: float
    aldersopsparing: float
    ratepensionsopsparing: float
    ratepensionsvarighed: int
    livrentedepot: float
    tilstand: PolicyState = field(default=PolicyState.I_LIVE)

    def total_enheder(self) -> float:
        """
        Samlet antal enheder (units) på tværs af alle tre depoter.

        Returns
        -------
        float
            aldersopsparing + ratepensionsopsparing + livrentedepot
        """
        return self.aldersopsparing + self.ratepensionsopsparing + self.livrentedepot

    def depotvaerdi_dkk(self, enhedspris: float) -> float:
        """
        Beregn depotværdien i DKK ved en given enhedspris.

        Depotværdien er **ikke** et gemt felt — den beregnes altid dynamisk
        som produktet af det samlede antal enheder og den aktuelle enhedspris.

        Parameters
        ----------
        enhedspris:
            Aktuel pris per enhed (DKK/enhed), f.eks. fra ``FinancialMarket.enhedspris(t)``.

        Returns
        -------
        float
            Depotværdi i DKK = total_enheder() × enhedspris
        """
        return self.total_enheder() * enhedspris

    def __str__(self) -> str:
        return (
            f"Policy(\n"
            f"  Tilstand             : {self.tilstand.value}\n"
            f"  Fødselsdato          : {self.foedselsdato}\n"
            f"  Tegningsdato         : {self.tegningsdato}\n"
            f"  Pensionsalder        : {self.pensionsalder} år\n"
            f"  Under udbetaling     : {self.er_under_udbetaling}\n"
            f"  GruppeID             : {self.gruppe_id}\n"
            f"  OmkostningssatsID    : {self.omkostningssats_id}\n"
            f"  Løn                  : {self.loen:,.0f} DKK/år\n"
            f"  Indbetalingsprocent  : {self.indbetalingsprocent:.1%}\n"
            f"  --- Depoter (enheder / units) ---\n"
            f"  Aldersopsparing      : {self.aldersopsparing:,.4f} enh.\n"
            f"  Ratepensionsopsparing: {self.ratepensionsopsparing:,.4f} enh.\n"
            f"  Ratepensionsvarighed : {self.ratepensionsvarighed} år\n"
            f"  Livrentedepot        : {self.livrentedepot:,.4f} enh.\n"
            f"  Total enheder        : {self.total_enheder():,.4f} enh.\n"
            f")"
        )
