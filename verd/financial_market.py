"""
FinancialMarket — abstrakt grundklasse for finansielle markedsmodeller (unit-link).

I et unit-link produkt afspejles afkastet som en stigning i enhedsprisen (NAV).
Alle DKK/enheder-konverteringer sker via ``enhedspris(t)``.

Konverteringsrelationer:
    enheder = DKK / enhedspris(t)   (præmie indbetales → køber enheder)
    DKK     = enheder × enhedspris(t) (ydelse udbetales → sælger enheder)

FinancialMarket er fuldstændigt uafhængig af ``BiometricModel`` —
de to modeller kobles kun i fremregningslaget.
"""

from abc import ABC, abstractmethod


class FinancialMarket(ABC):
    """
    Abstrakt grundklasse for det finansielle marked i et unit-link produkt.

    En konkret underklasse skal implementere ``enhedspris``,
    som returnerer fondens NAV (kurs) per enhed til tidspunkt t.

    Alle cashflow-konverteringer (DKK ↔ enheder) sker via enhedsprisen.
    """

    @abstractmethod
    def enhedspris(self, t: float) -> float:
        """
        Fondens enhedspris (NAV) ved tidspunkt t.

        Parameters
        ----------
        t:
            Tid i år målt fra tegningsdato (t=0 svarer til tegningsdato).

        Returns
        -------
        float
            Pris per enhed i DKK. Altid > 0.
        """
        ...

    def dkk_til_enheder(self, dkk: float, t: float) -> float:
        """
        Konverter et DKK-beløb til enheder ved tidspunkt t.

            enheder = DKK / enhedspris(t)

        Bruges f.eks. når en præmie indbetales og skal tilskrives depotet.

        Parameters
        ----------
        dkk:
            Beløb i DKK der skal konverteres.
        t:
            Tidspunkt for konverteringen (år fra tegningsdato).

        Returns
        -------
        float
            Antal enheder svarende til det indbetalte beløb.
        """
        return dkk / self.enhedspris(t)

    def enheder_til_dkk(self, enheder: float, t: float) -> float:
        """
        Konverter et antal enheder til DKK ved tidspunkt t.

            DKK = enheder × enhedspris(t)

        Bruges f.eks. når en ydelse udbetales og trækkes fra depotet.

        Parameters
        ----------
        enheder:
            Antal enheder der skal konverteres.
        t:
            Tidspunkt for konverteringen (år fra tegningsdato).

        Returns
        -------
        float
            DKK-værdien af det angivne antal enheder.
        """
        return enheder * self.enhedspris(t)
