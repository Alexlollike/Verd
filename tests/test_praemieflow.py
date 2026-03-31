"""
Tests for præmieflow: RisikoBundle, BeloebsgraenserOpslag og PraemieFlow.beregn().
"""

import pytest

from verd import (
    BeloebsgraenserOpslag,
    PraemieFlow,
    PraemieFlowResultat,
    STANDARD_RISIKO_BUNDLE,
    STANDARD_SATSER_FILSTI,
    indlæs_offentlige_satser,
)
from verd.risiko import RisikoDaekning, RisikoBundle


# ---------------------------------------------------------------------------
# RisikoBundle
# ---------------------------------------------------------------------------

class TestRisikoBundle:
    def test_standard_bundle_aarlig_praemie(self):
        assert STANDARD_RISIKO_BUNDLE.aarlig_praemie_dkk == 1500.0

    def test_standard_bundle_maanedlig_praemie(self):
        assert STANDARD_RISIKO_BUNDLE.maanedlig_praemie_dkk == 125.0

    def test_tom_bundle_er_nul(self):
        bundle = RisikoBundle(daekninger=[])
        assert bundle.aarlig_praemie_dkk == 0.0
        assert bundle.maanedlig_praemie_dkk == 0.0

    def test_enkelt_daekning(self):
        bundle = RisikoBundle(daekninger=[RisikoDaekning("Test", 2400.0)])
        assert bundle.aarlig_praemie_dkk == 2400.0
        assert bundle.maanedlig_praemie_dkk == 200.0


# ---------------------------------------------------------------------------
# indlæs_offentlige_satser
# ---------------------------------------------------------------------------

class TestIndlaesOffentligeSatser:
    def test_laes_standard_fil(self):
        satser = indlæs_offentlige_satser(STANDARD_SATSER_FILSTI)
        assert len(satser) > 0

    def test_2026_ratepension(self):
        satser = indlæs_offentlige_satser(STANDARD_SATSER_FILSTI)
        assert satser[("ratepension", 2026, "")] == 68_700.0

    def test_2026_aldersopsparing_normal(self):
        satser = indlæs_offentlige_satser(STANDARD_SATSER_FILSTI)
        assert satser[("aldersopsparing", 2026, "normal")] == 9_900.0

    def test_2026_aldersopsparing_naer_pension(self):
        satser = indlæs_offentlige_satser(STANDARD_SATSER_FILSTI)
        assert satser[("aldersopsparing", 2026, "nær_pension")] == 64_200.0

    def test_2026_livrente_ingen_graense(self):
        satser = indlæs_offentlige_satser(STANDARD_SATSER_FILSTI)
        assert satser[("livrente", 2026, "")] is None


# ---------------------------------------------------------------------------
# BeloebsgraenserOpslag
# ---------------------------------------------------------------------------

class TestBeloebsgraenserOpslag:
    def setup_method(self):
        self.satser = indlæs_offentlige_satser(STANDARD_SATSER_FILSTI)

    def test_normal_niveau_over_7_aar(self):
        opslag = BeloebsgraenserOpslag.fra_satser(self.satser, aar=2026, aar_til_folkepension=10)
        assert opslag.aldersopsparing_max == 9_900.0

    def test_naer_pension_under_eller_lig_7_aar(self):
        opslag = BeloebsgraenserOpslag.fra_satser(self.satser, aar=2026, aar_til_folkepension=7)
        assert opslag.aldersopsparing_max == 64_200.0

    def test_naer_pension_under_7_aar(self):
        opslag = BeloebsgraenserOpslag.fra_satser(self.satser, aar=2026, aar_til_folkepension=3)
        assert opslag.aldersopsparing_max == 64_200.0

    def test_ratepension_max(self):
        opslag = BeloebsgraenserOpslag.fra_satser(self.satser, aar=2026, aar_til_folkepension=20)
        assert opslag.ratepension_max == 68_700.0

    def test_livrente_max_er_none(self):
        opslag = BeloebsgraenserOpslag.fra_satser(self.satser, aar=2026, aar_til_folkepension=20)
        assert opslag.livrente_max is None


# ---------------------------------------------------------------------------
# PraemieFlow.beregn() — konservering
# ---------------------------------------------------------------------------

class TestPraemieFlowKonservering:
    """Invariant: risiko + rate + ald + liv == π_brutto for alle input."""

    def setup_method(self):
        satser = indlæs_offentlige_satser(STANDARD_SATSER_FILSTI)
        graenser = BeloebsgraenserOpslag.fra_satser(satser, aar=2026, aar_til_folkepension=20)
        self.pf = PraemieFlow(
            risiko_bundle=STANDARD_RISIKO_BUNDLE,
            beloebsgraenser=graenser,
            ratepension_andel=0.20,
            aldersopsparing_andel=0.10,
        )

    def _assert_konservering(self, brutto: float):
        r = self.pf.beregn(brutto)
        assert abs(r.total_dkk - brutto) < 1e-9, (
            f"total={r.total_dkk:.6f} ≠ brutto={brutto}"
        )

    def test_normal_indbetaling(self):
        self._assert_konservering(100_000.0)

    def test_stor_indbetaling(self):
        self._assert_konservering(500_000.0)

    def test_lille_indbetaling(self):
        self._assert_konservering(5_000.0)

    def test_nul_indbetaling(self):
        self._assert_konservering(0.0)

    def test_negativt_pi_netto(self):
        # Risikopræmie > brutto: π_netto < 0
        self._assert_konservering(500.0)  # risiko = 1500, brutto = 500


# ---------------------------------------------------------------------------
# PraemieFlow.beregn() — korrekte beløb
# ---------------------------------------------------------------------------

class TestPraemieFlowBeloeb:
    def setup_method(self):
        satser = indlæs_offentlige_satser(STANDARD_SATSER_FILSTI)
        self.graenser = BeloebsgraenserOpslag.fra_satser(satser, aar=2026, aar_til_folkepension=20)

    def test_risikopraemie_fratrukket(self):
        pf = PraemieFlow(
            risiko_bundle=STANDARD_RISIKO_BUNDLE,
            beloebsgraenser=self.graenser,
            ratepension_andel=0.0,
            aldersopsparing_andel=0.0,
        )
        r = pf.beregn(100_000.0)
        assert r.risikopraemie_dkk == 1_500.0
        assert abs(r.livrente_dkk - 98_500.0) < 1e-9

    def test_ingen_risikobundle_giver_nul_risikopraemie(self):
        pf = PraemieFlow(
            risiko_bundle=None,
            beloebsgraenser=self.graenser,
            ratepension_andel=0.0,
            aldersopsparing_andel=0.0,
        )
        r = pf.beregn(100_000.0)
        assert r.risikopraemie_dkk == 0.0

    def test_rate_under_cap_ikke_begraenset(self):
        """100.000 kr brutto: ønsket rate = 20% af π_netto = 19.700 < loft 68.700 → ikke capped."""
        pf = PraemieFlow(
            risiko_bundle=STANDARD_RISIKO_BUNDLE,
            beloebsgraenser=self.graenser,
            ratepension_andel=0.20,
            aldersopsparing_andel=0.0,
        )
        r = pf.beregn(100_000.0)
        pi_netto = 100_000.0 - 1_500.0
        assert abs(r.ratepension_dkk - pi_netto * 0.20) < 1e-9

    def test_rate_cap_rammer_ved_stor_indbetaling(self):
        """400.000 kr: ønsket rate = 20% × 398.500 = 79.700 > loft 68.700."""
        pf = PraemieFlow(
            risiko_bundle=STANDARD_RISIKO_BUNDLE,
            beloebsgraenser=self.graenser,
            ratepension_andel=0.20,
            aldersopsparing_andel=0.0,
        )
        r = pf.beregn(400_000.0)
        assert abs(r.ratepension_dkk - 68_700.0) < 1e-9
        # Overskud (79.700 - 68.700 = 11.000) ender i livrente
        assert r.livrente_dkk > 400_000.0 * 0.20

    def test_ald_cap_normal_niveau(self):
        """Over loft på 9.900 kr (normal-niveau): overflow til livrente."""
        pf = PraemieFlow(
            risiko_bundle=None,
            beloebsgraenser=self.graenser,  # normal: 9.900
            ratepension_andel=0.0,
            aldersopsparing_andel=0.50,
        )
        r = pf.beregn(100_000.0)
        assert abs(r.aldersopsparing_dkk - 9_900.0) < 1e-9

    def test_naer_pension_aldersopsparing_max(self):
        satser = indlæs_offentlige_satser(STANDARD_SATSER_FILSTI)
        graenser_np = BeloebsgraenserOpslag.fra_satser(satser, aar=2026, aar_til_folkepension=5)
        pf = PraemieFlow(
            risiko_bundle=None,
            beloebsgraenser=graenser_np,
            ratepension_andel=0.0,
            aldersopsparing_andel=1.0,
        )
        r = pf.beregn(100_000.0)
        assert abs(r.aldersopsparing_dkk - 64_200.0) < 1e-9

    def test_negativt_pi_netto_giver_negativ_aldersopsparing(self):
        pf = PraemieFlow(
            risiko_bundle=STANDARD_RISIKO_BUNDLE,
            beloebsgraenser=self.graenser,
            ratepension_andel=0.20,
            aldersopsparing_andel=0.10,
        )
        r = pf.beregn(500.0)  # risiko = 1500 > brutto = 500 → π_netto = -1000
        assert r.risikopraemie_dkk == 1_500.0
        assert r.aldersopsparing_dkk == -1_000.0
        assert r.ratepension_dkk == 0.0
        assert r.livrente_dkk == 0.0
        assert abs(r.total_dkk - 500.0) < 1e-9

    def test_ingen_beloebsgraenser_respekterer_andele(self):
        pf = PraemieFlow(
            risiko_bundle=None,
            beloebsgraenser=None,  # ingen lofter
            ratepension_andel=0.30,
            aldersopsparing_andel=0.20,
        )
        r = pf.beregn(100_000.0)
        assert abs(r.ratepension_dkk - 30_000.0) < 1e-9
        assert abs(r.aldersopsparing_dkk - 20_000.0) < 1e-9
        assert abs(r.livrente_dkk - 50_000.0) < 1e-9
