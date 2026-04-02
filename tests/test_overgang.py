"""
Tests for overgang — Tilstandsmodel og overgangsintensiteter.

Dækker:
    - Tilstandsmodel: alle_tilstande(), ikke_absorberende(), ud_overgange()
    - BiometriOvergangsIntensitet: delegerer til BiometricModel
    - KonstantOvergangsIntensitet: returnerer konstant uanset alder
"""

import pytest

from verd import (
    BiometriOvergangsIntensitet,
    GompertzMakeham,
    KonstantOvergangsIntensitet,
    Overgang,
    PolicyState,
    Tilstandsmodel,
    nul_risikosum,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def gm() -> GompertzMakeham:
    return GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)


@pytest.fixture
def tilstandsmodel(gm: GompertzMakeham) -> Tilstandsmodel:
    """Standard to-tilstands-model: I_LIVE → DOED."""
    return Tilstandsmodel(
        overgange=[
            Overgang(
                fra=PolicyState.I_LIVE,
                til=PolicyState.DOED,
                intensitet=BiometriOvergangsIntensitet(gm),
                risikosum_func=nul_risikosum,
            )
        ]
    )


# ---------------------------------------------------------------------------
# Tests for Tilstandsmodel
# ---------------------------------------------------------------------------

class TestTilstandsmodel:
    def test_alle_tilstande_returnerer_begge_tilstande(self, tilstandsmodel: Tilstandsmodel):
        tilstande = tilstandsmodel.alle_tilstande()
        assert PolicyState.I_LIVE in tilstande
        assert PolicyState.DOED in tilstande

    def test_alle_tilstande_returnerer_praecis_to(self, tilstandsmodel: Tilstandsmodel):
        assert len(tilstandsmodel.alle_tilstande()) == 2

    def test_ikke_absorberende_indeholder_i_live(self, tilstandsmodel: Tilstandsmodel):
        aktive = tilstandsmodel.ikke_absorberende()
        assert PolicyState.I_LIVE in aktive

    def test_ikke_absorberende_udelader_doed(self, tilstandsmodel: Tilstandsmodel):
        """DOED har ingen udgående overgange → absorberende → ikke i sættet."""
        aktive = tilstandsmodel.ikke_absorberende()
        assert PolicyState.DOED not in aktive

    def test_ikke_absorberende_er_praecis_en(self, tilstandsmodel: Tilstandsmodel):
        assert len(tilstandsmodel.ikke_absorberende()) == 1

    def test_ud_overgange_fra_i_live_returnerer_en(self, tilstandsmodel: Tilstandsmodel):
        overgange = tilstandsmodel.ud_overgange(PolicyState.I_LIVE)
        assert len(overgange) == 1

    def test_ud_overgange_fra_i_live_peger_paa_doed(self, tilstandsmodel: Tilstandsmodel):
        overgang = tilstandsmodel.ud_overgange(PolicyState.I_LIVE)[0]
        assert overgang.fra == PolicyState.I_LIVE
        assert overgang.til == PolicyState.DOED

    def test_ud_overgange_fra_doed_er_tom(self, tilstandsmodel: Tilstandsmodel):
        """DOED er absorberende: ingen udgående overgange."""
        overgange = tilstandsmodel.ud_overgange(PolicyState.DOED)
        assert overgange == []

    def test_tom_model_har_ingen_tilstande(self):
        model = Tilstandsmodel(overgange=[])
        assert model.alle_tilstande() == set()
        assert model.ikke_absorberende() == set()


# ---------------------------------------------------------------------------
# Tests for BiometriOvergangsIntensitet
# ---------------------------------------------------------------------------

class TestBiometriOvergangsIntensitet:
    def test_delegerer_til_biometrisk_model(self, gm: GompertzMakeham):
        """
        BiometriOvergangsIntensitet.intensitet(alder) == gm.mortality_intensity(alder).
        """
        intensitet = BiometriOvergangsIntensitet(gm)
        alder = 45.0
        assert intensitet.intensitet(alder) == pytest.approx(gm.mortality_intensity(alder))

    def test_stiger_med_alder(self, gm: GompertzMakeham):
        """Dødelighedsintensiteten stiger med alderen (Gompertz-Makeham)."""
        intensitet = BiometriOvergangsIntensitet(gm)
        assert intensitet.intensitet(30.0) < intensitet.intensitet(60.0)

    def test_er_positiv(self, gm: GompertzMakeham):
        intensitet = BiometriOvergangsIntensitet(gm)
        for alder in [20.0, 40.0, 60.0, 80.0]:
            assert intensitet.intensitet(alder) > 0.0


# ---------------------------------------------------------------------------
# Tests for KonstantOvergangsIntensitet
# ---------------------------------------------------------------------------

class TestKonstantOvergangsIntensitet:
    def test_returnerer_konstant_uanset_alder(self):
        """
        KonstantOvergangsIntensitet returnerer samme µ ved alle aldre.
        """
        mu = 0.02
        intensitet = KonstantOvergangsIntensitet(mu=mu)
        for alder in [20.0, 40.0, 60.0, 80.0, 100.0]:
            assert intensitet.intensitet(alder) == pytest.approx(mu)

    def test_nul_intensitet(self):
        intensitet = KonstantOvergangsIntensitet(mu=0.0)
        assert intensitet.intensitet(50.0) == pytest.approx(0.0)

    def test_hoj_intensitet(self):
        intensitet = KonstantOvergangsIntensitet(mu=1.0)
        assert intensitet.intensitet(99.0) == pytest.approx(1.0)
