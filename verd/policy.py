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

import enum
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from verd.risiko import RisikoBundle

from verd.policy_state import PolicyState


class DoedsydelsesType(enum.Enum):
    """
    Valgmulighed for hvad der sker med depot/hensættelse ved forsikringstagers død.

    DEPOT:
        Depotværdien udbetales ved død (depotsikring).
        Matematisk: b^{01}(t) = depot(t), V^{DOED}(t) = 0
        → risikosum R = b^{01} + V^{DOED} − V^{I_LIVE} = depot − depot = 0.
        Ingen dødelighedsgevinster opstår.
        Kun gyldigt i opsparingsfasen (er_under_udbetaling=False).

    INGEN:
        Ingen ydelse ved død.
        Matematisk: b^{01}(t) = 0, V^{DOED}(t) = 0
        → risikosum R = 0 + 0 − V^{I_LIVE}(t) = −depot(t) < 0.
        Dødelighedsgevinster tilfalder overlevende forsikringstagere og øger
        den forventede livrente-ydelse. Gyldigt i både opsparing og udbetaling.
    """

    DEPOT = "depot"
    INGEN = "ingen"


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
    ratepension_andel:
        Ønsket andel af nettopræmien der allokeres til ratepension (0.0–1.0).
        Bruges af ``praemieflow_cashflow_funktion``. Standard: 0.0.
    aldersopsparing_andel:
        Ønsket andel af nettopræmien der allokeres til aldersopsparing (0.0–1.0).
        Bruges af ``praemieflow_cashflow_funktion``. Standard: 0.0.
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
    ratepension_andel: float = field(default=0.0)
    aldersopsparing_andel: float = field(default=0.0)
    tilstand: PolicyState = field(default=PolicyState.I_LIVE)
    doedsydelses_type: DoedsydelsesType = field(default=DoedsydelsesType.INGEN)
    risiko_bundle: RisikoBundle | None = field(default=None)

    @classmethod
    def fra_dkk(
        cls,
        foedselsdato: date,
        tegningsdato: date,
        pensionsalder: int,
        er_under_udbetaling: bool,
        gruppe_id: str,
        omkostningssats_id: str,
        loen: float,
        indbetalingsprocent: float,
        aldersopsparing: float,
        ratepensionsopsparing: float,
        ratepensionsvarighed: int,
        livrentedepot: float,
        enhedspris: float,
        ratepension_andel: float = 0.0,
        aldersopsparing_andel: float = 0.0,
        tilstand: PolicyState = PolicyState.I_LIVE,
        doedsydelses_type: DoedsydelsesType = DoedsydelsesType.INGEN,
        risiko_bundle: "RisikoBundle | None" = None,
    ) -> "Policy":
        """
        Opret en Policy med depotværdier angivet i DKK.

        Konverterer automatisk DKK til enheder (units) ved hjælp af enhedsprisen
        på oprettelsestidspunktet:

            enheder = DKK / enhedspris

        Internt lagres depoterne altid i enheder, men dette er den anbefalede
        måde at oprette en ny police på.

        Parameters
        ----------
        aldersopsparing:
            Aldersopsparing i DKK.
        ratepensionsopsparing:
            Ratepensionsopsparing i DKK.
        livrentedepot:
            Livrentedepot i DKK.
        enhedspris:
            Enhedspris på oprettelsestidspunktet (DKK/enhed).
            Brug typisk ``market.enhedspris(0.0)`` fra ``DeterministicMarket``.
        """
        return cls(
            foedselsdato=foedselsdato,
            tegningsdato=tegningsdato,
            pensionsalder=pensionsalder,
            er_under_udbetaling=er_under_udbetaling,
            gruppe_id=gruppe_id,
            omkostningssats_id=omkostningssats_id,
            loen=loen,
            indbetalingsprocent=indbetalingsprocent,
            aldersopsparing=aldersopsparing / enhedspris,
            ratepensionsopsparing=ratepensionsopsparing / enhedspris,
            ratepensionsvarighed=ratepensionsvarighed,
            livrentedepot=livrentedepot / enhedspris,
            ratepension_andel=ratepension_andel,
            aldersopsparing_andel=aldersopsparing_andel,
            tilstand=tilstand,
            doedsydelses_type=doedsydelses_type,
            risiko_bundle=risiko_bundle,
        )

    def alder_ved_tegning(self) -> float:
        """
        Forsikringstagers alder i år ved tegningsdato.

        Bruges til at beregne alderen på et vilkårligt fremtidigt tidspunkt t:
            alder(t) = alder_ved_tegning() + t

        Returns
        -------
        float
            Alder i år (kan have decimaler).
        """
        return (self.tegningsdato - self.foedselsdato).days / 365.25

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
            f"  Dødelsydelse         : {self.doedsydelses_type.value}\n"
            f"  GruppeID             : {self.gruppe_id}\n"
            f"  OmkostningssatsID    : {self.omkostningssats_id}\n"
            f"  Løn                  : {self.loen:,.0f} DKK/år\n"
            f"  Indbetalingsprocent  : {self.indbetalingsprocent:.1%}\n"
            f"  Ratepension andel    : {self.ratepension_andel:.1%}\n"
            f"  Aldersopsparing andel: {self.aldersopsparing_andel:.1%}\n"
            f"  --- Depoter (enheder / units) ---\n"
            f"  Aldersopsparing      : {self.aldersopsparing:,.4f} enh.\n"
            f"  Ratepensionsopsparing: {self.ratepensionsopsparing:,.4f} enh.\n"
            f"  Ratepensionsvarighed : {self.ratepensionsvarighed} år\n"
            f"  Livrentedepot        : {self.livrentedepot:,.4f} enh.\n"
            f"  Total enheder        : {self.total_enheder():,.4f} enh.\n"
            f")"
        )
