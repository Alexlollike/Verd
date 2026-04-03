"""
Præmieflow — risikofradrag og allokering af nettopræmie til depoter.

Bruttopræmien gennemløber to transformationer inden den rammer opsparingsdepotterne:

    π_brutto(t)
      − risikopraemie(t)          ← finansierer dødsfald/TAE/SUL-dækninger
      = π_netto(t)
          → ratepension            ← op til skattemæssig beløbsgrænse
          → aldersopsparing        ← op til skattemæssig beløbsgrænse
          → livrente               ← resterende (ingen beløbsgrænse)

Kundens ønsker (``ratepension_andel``, ``aldersopsparing_andel``) efterleves
så præcist som muligt — beløbsgrænser overholdes ved at sende overskydende beløb
til livrente. Livrente modtager altid det resterende beløb.

Hvis π_netto < 0 (risikopræmien overstiger bruttopræmien), returneres et negativt
beløb i ``aldersopsparing_dkk`` — betalingslaget trækker differencen fra depotet.
"""

from __future__ import annotations

from dataclasses import dataclass

from verd.offentlige_satser import BeloebsgraenserOpslag
from verd.risiko import RisikoBundle


@dataclass
class PraemieFlowResultat:
    """
    Resultat af præmieflow-beregningen for ét år.

    Viser præcist hvordan bruttopræmien fordeles:
        risikopraemie + ratepension + aldersopsparing + livrente = π_brutto

    Attributes
    ----------
    risikopraemie_dkk:
        Beløb til risikodækninger (dødsfald/TAE/SUL) i DKK/år.
        Nul hvis ingen ``RisikoBundle`` er tilknyttet.
    ratepension_dkk:
        Allokeret til ratepensionsdepot i DKK/år.
        Begrænset af ``BeloebsgraenserOpslag.ratepension_max``.
    aldersopsparing_dkk:
        Allokeret til aldersopsparingsdepot i DKK/år.
        Begrænset af ``BeloebsgraenserOpslag.aldersopsparing_max``.
        Kan være negativ hvis π_netto < 0 (risikopræmie > bruttopræmie).
    livrente_dkk:
        Restbeløb til livrentedepot i DKK/år (ingen beløbsgrænse).
        Absorberer alt der ikke kan allokeres til rate eller ald.
    """

    risikopraemie_dkk: float
    ratepension_dkk: float
    aldersopsparing_dkk: float
    livrente_dkk: float

    @property
    def total_dkk(self) -> float:
        """Kontrol: summen skal svare til π_brutto."""
        return (
            self.risikopraemie_dkk
            + self.ratepension_dkk
            + self.aldersopsparing_dkk
            + self.livrente_dkk
        )


@dataclass
class PraemieFlow:
    """
    Præmieflow-konfiguration — skattemæssige beløbsgrænser for allokeringen.

    Indeholder de offentligt fastsatte beløbsgrænser der skal overholdes ved
    fordeling af nettopræmien. Kundens allokeringsønsker (``ratepension_andel``,
    ``aldersopsparing_andel``) og risikodækninger (``risiko_bundle``) er
    police-specifikke og ligger på ``Policy``-objektet.

    Allokeringslogik i ``beregn()``:
        1. Træk risikopræmie fra bruttopræmien: π_netto = π_brutto − risiko
        2. Beregn ønsket allokering proportionalt:
               rate_ønsket = π_netto × ratepension_andel
               ald_ønsket  = π_netto × aldersopsparing_andel
        3. Beskær ved beløbsgrænser (overskydende beløb sendes til livrente):
               rate = min(rate_ønsket, ratepension_max)
               ald  = min(ald_ønsket,  aldersopsparing_max)
        4. Livrente modtager resten:
               liv  = π_netto − rate − ald

    Eksempel (π_brutto = 100.000, risiko = 1.500, 20/10/70 %-fordeling, loft 68.700/9.900):
        π_netto = 98.500
        rate_ønsket = 19.700 → under loft → rate = 19.700
        ald_ønsket  =  9.850 → under loft → ald  =  9.850
        liv = 98.500 − 19.700 − 9.850 = 68.950

    Attributes
    ----------
    beloebsgraenser:
        Skattemæssige beløbsgrænser. ``None`` = ingen lofter (livrente modtager al rest).
    """

    beloebsgraenser: BeloebsgraenserOpslag | None

    def beregn(
        self,
        bruttoindbetalng_aar: float,
        ratepension_andel: float,
        aldersopsparing_andel: float,
        risiko_bundle: RisikoBundle | None,
    ) -> PraemieFlowResultat:
        """
        Beregn præmieflow for ét år.

        Parameters
        ----------
        bruttoindbetalng_aar:
            Bruttopræmie i DKK/år (typisk ``loen × indbetalingsprocent``).
        ratepension_andel:
            Ønsket andel af π_netto til ratepension (0.0–1.0).
            Typisk ``policy.ratepension_andel``.
        aldersopsparing_andel:
            Ønsket andel af π_netto til aldersopsparing (0.0–1.0).
            Summen ``ratepension_andel + aldersopsparing_andel`` bør være ≤ 1.0.
            Typisk ``policy.aldersopsparing_andel``.
        risiko_bundle:
            Risikodækninger der finansieres før opsparingsallokering. ``None`` = ingen risiko.
            Typisk ``policy.risiko_bundle``.

        Returns
        -------
        PraemieFlowResultat
            Fordeling på risiko, ratepension, aldersopsparing og livrente.
            Invariant: ``resultat.total_dkk == bruttoindbetalng_aar``.
        """
        # ---- 1. Risikofradrag -----------------------------------------------
        risikopraemie = (
            risiko_bundle.aarlig_praemie_dkk
            if risiko_bundle is not None
            else 0.0
        )
        pi_netto = bruttoindbetalng_aar - risikopraemie

        # ---- 2. Håndtér π_netto < 0 -----------------------------------------
        # Risikopræmien overstiger bruttopræmien. Differencen trækkes fra
        # aldersopsparingen (negativ allokering returneres).
        if pi_netto < 0.0:
            return PraemieFlowResultat(
                risikopraemie_dkk=risikopraemie,
                ratepension_dkk=0.0,
                aldersopsparing_dkk=pi_netto,  # negativ
                livrente_dkk=0.0,
            )

        # ---- 3. Ønsket allokering -------------------------------------------
        rate_ønsket = pi_netto * ratepension_andel
        ald_ønsket = pi_netto * aldersopsparing_andel

        # ---- 4. Beskær ved beløbsgrænser ------------------------------------
        if self.beloebsgraenser is not None:
            rate = min(rate_ønsket, self.beloebsgraenser.ratepension_max)
            ald = min(ald_ønsket, self.beloebsgraenser.aldersopsparing_max)
        else:
            rate = rate_ønsket
            ald = ald_ønsket

        # ---- 5. Livrente modtager resten ------------------------------------
        liv = pi_netto - rate - ald

        return PraemieFlowResultat(
            risikopraemie_dkk=risikopraemie,
            ratepension_dkk=rate,
            aldersopsparing_dkk=ald,
            livrente_dkk=liv,
        )
