"""
verd — Aktuarbibliotek til sandsynlighedsvægtet fremregning af enkeltpolice.

Produktfokus: Rene markedsrenteprodukter (unit-link) uden garantier.
Arkitektur: Policen modelleres som en flerdimensionel Markov-proces i diskret tid.
"""

from verd.policy_state import PolicyState
from verd.policy import Policy
from verd.policy_distribution import PolicyDistribution, initial_distribution
from verd.biometric_model import BiometricModel
from verd.gompertz_makeham import GompertzMakeham
from verd.financial_market import FinancialMarket
from verd.deterministic_market import DeterministicMarket
from verd.thiele import CashflowSats, RisikoSummer, thiele_step
from verd.overgang import (
    OvergangsIntensitet,
    BiometriOvergangsIntensitet,
    KonstantOvergangsIntensitet,
    Overgang,
    Tilstandsmodel,
)
from verd.omkostning import OmkostningsFunktion, nul_omkostning, standard_omkostning
from verd.plot import plot_fremregning, plot_fra_dataframe
from verd.eksportering import (
    til_dataframe,
    eksporter_cashflows_csv,
    print_cashflow_tabel,
    print_policeoversigt,
)
from verd.validering import (
    check_sandsynligheder,
    check_p_alive_monoton,
    kør_alle_checks,
)
from verd.udbetaling import (
    livrente_annuitet,
    sikker_annuitet,
    udbetaling_cashflow_funktion,
)
from verd.fremregning import (
    CashflowFunktion,
    RisikosumFunktion,
    TilstandsSkridt,
    FremregningsSkridt,
    simpel_opsparings_cashflow,
    simpel_cashflow_funktion,
    nul_risikosum,
    standard_toetilstands_model,
    fremregn,
    praemieflow_cashflow_funktion,
)
from verd.risiko import RisikoDaekning, RisikoBundle, STANDARD_RISIKO_BUNDLE
from verd.offentlige_satser import (
    indlæs_offentlige_satser,
    BeloebsgraenserOpslag,
    STANDARD_SATSER_FILSTI,
)
from verd.praemieflow import PraemieFlow, PraemieFlowResultat

__all__ = [
    # Grundlæggende dataklasser
    "PolicyState",
    "Policy",
    "PolicyDistribution",
    "initial_distribution",
    # Biometriske modeller
    "BiometricModel",
    "GompertzMakeham",
    # Finansielle markedsmodeller
    "FinancialMarket",
    "DeterministicMarket",
    # Thiele-mekanik
    "CashflowSats",
    "RisikoSummer",
    "thiele_step",
    # Tilstandsrum og overgange
    "OvergangsIntensitet",
    "BiometriOvergangsIntensitet",
    "KonstantOvergangsIntensitet",
    "Overgang",
    "Tilstandsmodel",
    # Omkostningsmodeller
    "OmkostningsFunktion",
    "nul_omkostning",
    "standard_omkostning",
    # Visualisering
    "plot_fremregning",
    "plot_fra_dataframe",
    # Eksportering og output
    "til_dataframe",
    "eksporter_cashflows_csv",
    "print_cashflow_tabel",
    "print_policeoversigt",
    # Validering
    "check_sandsynligheder",
    "check_p_alive_monoton",
    "kør_alle_checks",
    # Udbetalingsfase
    "livrente_annuitet",
    "sikker_annuitet",
    "udbetaling_cashflow_funktion",
    # Fremregning
    "CashflowFunktion",
    "RisikosumFunktion",
    "TilstandsSkridt",
    "FremregningsSkridt",
    "simpel_opsparings_cashflow",
    "simpel_cashflow_funktion",
    "nul_risikosum",
    "standard_toetilstands_model",
    "fremregn",
    "praemieflow_cashflow_funktion",
    # Risikodækninger
    "RisikoDaekning",
    "RisikoBundle",
    "STANDARD_RISIKO_BUNDLE",
    # Offentlige satser og beløbsgrænser
    "indlæs_offentlige_satser",
    "BeloebsgraenserOpslag",
    "STANDARD_SATSER_FILSTI",
    # Præmieflow
    "PraemieFlow",
    "PraemieFlowResultat",
]
