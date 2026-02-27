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

__all__ = [
    "PolicyState",
    "Policy",
    "PolicyDistribution",
    "initial_distribution",
    "BiometricModel",
    "GompertzMakeham",
    "FinancialMarket",
    "DeterministicMarket",
]
