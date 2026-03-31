"""
Offentlige satser — beløbsgrænser for indbetaling til pensionsprodukter.

Satserne er fastsat ved lov og opdateres typisk hvert år (skat.dk).
Filen ``verd/data/offentlige_satser.csv`` indeholder satserne for 2025 og 2026
og kan opdateres uden kodeændringer.

CSV-format:
    produkt,aar,beloebsgraense_dkk,betingelse

    produkt    : aldersopsparing | ratepension | livrente
    aar        : kalenderår satsen gælder
    beloebsgraense_dkk : max indbetaling pr. år (blank = ingen grænse)
    betingelse : normal (>7 år til folkepensionsalder),
                 nær_pension (≤7 år til folkepensionsalder),
                 blank = gælder altid (uanset afstand til pension)

Folkepensionsalderen i Danmark er aktuelt 67 år.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

#: Standardsti til den medfølgende CSV-fil.
STANDARD_SATSER_FILSTI = Path(__file__).parent / "data" / "offentlige_satser.csv"

#: Gyldige produktnavne i CSV-filen.
_GYLDIGE_PRODUKTER = {"aldersopsparing", "ratepension", "livrente"}


def indlæs_offentlige_satser(filsti: Path) -> dict[tuple[str, int, str], float | None]:
    """
    Indlæs beløbsgrænser fra CSV-fil.

    Parameters
    ----------
    filsti:
        Sti til CSV-filen med offentlige satser.

    Returns
    -------
    dict
        Nøgle: ``(produkt, aar, betingelse)`` — alle strenge.
        Værdi: ``float`` (DKK/år) eller ``None`` (ingen grænse).
        ``betingelse`` er ``""`` for satser der gælder altid.

    Raises
    ------
    ValueError
        Hvis CSV-filen mangler påkrævede kolonner eller indeholder et ukendt produktnavn.
    FileNotFoundError
        Hvis filen ikke eksisterer.
    """
    påkrævede_kolonner = {"produkt", "aar", "beloebsgraense_dkk", "betingelse"}

    satser: dict[tuple[str, int, str], float | None] = {}

    with open(filsti, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise ValueError(f"CSV-filen '{filsti}' er tom eller mangler header.")

        manglende = påkrævede_kolonner - set(reader.fieldnames)
        if manglende:
            raise ValueError(
                f"CSV-filen '{filsti}' mangler kolonner: {manglende}"
            )

        for række in reader:
            produkt = række["produkt"].strip()
            if produkt not in _GYLDIGE_PRODUKTER:
                raise ValueError(
                    f"Ukendt produkt '{produkt}' i '{filsti}'. "
                    f"Gyldige værdier: {_GYLDIGE_PRODUKTER}"
                )

            aar = int(række["aar"].strip())
            betingelse = række["betingelse"].strip()
            graense_raw = række["beloebsgraense_dkk"].strip()
            graense: float | None = float(graense_raw) if graense_raw else None

            satser[(produkt, aar, betingelse)] = graense

    return satser


@dataclass
class BeloebsgraenserOpslag:
    """
    Beløbsgrænser for ét konkret policescenarie (år + afstand til folkepension).

    Slår de korrekte beløbsgrænser op ud fra kundens aktuelle situation:
    - Aldersopsparing har to niveauer: ``normal`` (>7 år til pension) og
      ``nær_pension`` (≤7 år til folkepensionsalder).
    - Ratepension har én sats (uafhængig af afstand til pension).
    - Livrente har ingen beløbsgrænse (``livrente_max = None``).

    Folkepensionsalderen i Danmark er 67 år; ``aar_til_folkepension`` beregnes
    typisk som ``67 - nuværende_alder``.

    Attributes
    ----------
    aar:
        Kalenderår satserne gælder for.
    aar_til_folkepension:
        Antal år til forsikringstager når folkepensionsalderen (67 år).
    aldersopsparing_max:
        Maksimal årlig indbetaling til aldersopsparing (DKK).
        Bruger ``nær_pension``-grænsen hvis ``aar_til_folkepension ≤ 7``,
        ellers ``normal``-grænsen.
    ratepension_max:
        Maksimal årlig indbetaling til ratepension (DKK).
    livrente_max:
        ``None`` — livrente har ingen beløbsgrænse.
    """

    aar: int
    aar_til_folkepension: float
    aldersopsparing_max: float
    ratepension_max: float
    livrente_max: float | None

    @classmethod
    def fra_satser(
        cls,
        satser: dict[tuple[str, int, str], float | None],
        aar: int,
        aar_til_folkepension: float,
    ) -> "BeloebsgraenserOpslag":
        """
        Opret ``BeloebsgraenserOpslag`` ud fra en sats-dict og situationsdata.

        Parameters
        ----------
        satser:
            Dict returneret af ``indlæs_offentlige_satser()``.
        aar:
            Kalenderår satserne skal gælde for.
        aar_til_folkepension:
            Antal år til folkepensionsalder — bestemmer aldersopsparing-niveauet.

        Returns
        -------
        BeloebsgraenserOpslag
        """
        ald_betingelse = "nær_pension" if aar_til_folkepension <= 7 else "normal"
        ald_max = satser.get(("aldersopsparing", aar, ald_betingelse))
        if ald_max is None:
            raise KeyError(
                f"Ingen aldersopsparingsgrænse fundet for år={aar}, betingelse='{ald_betingelse}'."
            )

        rate_max = satser.get(("ratepension", aar, ""))
        if rate_max is None:
            raise KeyError(f"Ingen ratepensionsgrænse fundet for år={aar}.")

        livrente_max = satser.get(("livrente", aar, ""), None)

        return cls(
            aar=aar,
            aar_til_folkepension=aar_til_folkepension,
            aldersopsparing_max=ald_max,
            ratepension_max=rate_max,
            livrente_max=livrente_max,
        )
