"""
Eksempel: Depotsikring i opsparingsfasen.

Sammenligner to identiske policer der kun adskiller sig på doedsydelses_type:
  - INGEN:  ingen dødelsydelse — dødelighedsgevinster tilfalder de overlevende
  - DEPOT:  depotværdi udbetales ved død — risikosum ≈ 0, ingen dødelighedsgevinster

Forventet resultat:
  - Samlet forventet udbetaling er HØJERE uden depotsikring (INGEN) fordi
    dødelighedsgevinster øger det forventede depot løbende.
  - Reserve-forløbet er ens frem til pensionering (begge er rent unit-link).

Kør med:
    python examples/eksempel_depotsikring.py
"""

import math
from datetime import date

from verd import (
    DeterministicMarket,
    DoedsydelsesType,
    GompertzMakeham,
    Policy,
    PolicyState,
    beregn_risikosum_funktion,
    fremregn,
    initial_distribution,
    simpel_opsparings_cashflow,
    standard_toetilstands_model,
)
from verd.overgang import BiometriOvergangsIntensitet, Overgang, Tilstandsmodel

# ---------------------------------------------------------------------------
# Modeller
# ---------------------------------------------------------------------------
biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)
marked = DeterministicMarket(r=math.log(1.05), enhedspris_0=100.0)

risikosum_func = beregn_risikosum_funktion(marked)

tilstandsmodel = Tilstandsmodel(
    overgange=[
        Overgang(
            fra=PolicyState.I_LIVE,
            til=PolicyState.DOED,
            intensitet=BiometriOvergangsIntensitet(biometri),
            risikosum_func=risikosum_func,
        )
    ]
)

# ---------------------------------------------------------------------------
# To policer — identiske bortset fra doedsydelses_type
# ---------------------------------------------------------------------------
FAELLES_KWARGS = dict(
    foedselsdato=date(1980, 1, 15),
    tegningsdato=date(2020, 6, 1),
    pensionsalder=67,
    er_under_udbetaling=False,
    gruppe_id="DK_MAND_2023",
    omkostningssats_id="STANDARD",
    loen=600_000.0,
    indbetalingsprocent=0.15,
    aldersopsparing=120_000.0,
    ratepensionsopsparing=80_000.0,
    ratepensionsvarighed=10,
    livrentedepot=50_000.0,
    enhedspris=marked.enhedspris(0.0),
    tilstand=PolicyState.I_LIVE,
)

police_ingen = Policy.fra_dkk(**FAELLES_KWARGS, doedsydelses_type=DoedsydelsesType.INGEN)
police_depot = Policy.fra_dkk(**FAELLES_KWARGS, doedsydelses_type=DoedsydelsesType.DEPOT)

# ---------------------------------------------------------------------------
# Fremregning — kun opsparingsfasen (27 år til pensionering ved 67)
# ---------------------------------------------------------------------------
ANTAL_AAR = 27
ANTAL_SKRIDT = ANTAL_AAR * 12

skridt_ingen = fremregn(
    distribution=initial_distribution(police_ingen),
    antal_skridt=ANTAL_SKRIDT,
    market=marked,
    tilstandsmodel=tilstandsmodel,
    cashflow_funktion=simpel_opsparings_cashflow,
    dt=1 / 12,
)

skridt_depot = fremregn(
    distribution=initial_distribution(police_depot),
    antal_skridt=ANTAL_SKRIDT,
    market=marked,
    tilstandsmodel=tilstandsmodel,
    cashflow_funktion=simpel_opsparings_cashflow,
    dt=1 / 12,
)

# ---------------------------------------------------------------------------
# Sammenlign forventet depot ved pensionering
# ---------------------------------------------------------------------------
slut_ingen = skridt_ingen[-1]
slut_depot = skridt_depot[-1]

depot_ingen = slut_ingen.forventet_depot_dkk
depot_depot = slut_depot.forventet_depot_dkk

print("=" * 60)
print("Depotsikring — sammenligning ved pensionering (alder 67)")
print("=" * 60)
print(f"{'':30s}  {'INGEN':>12s}  {'DEPOT':>12s}")
print("-" * 60)
print(f"{'Forventet depot (DKK)':30s}  {depot_ingen:>12,.0f}  {depot_depot:>12,.0f}")
print(f"{'Forskel (INGEN - DEPOT) DKK':30s}  {depot_ingen - depot_depot:>12,.0f}")
print(f"{'Forskel (%)':30s}  {(depot_ingen / depot_depot - 1) * 100:>11.2f}%")
print()
print("Konklusion:")
if depot_ingen > depot_depot:
    print("  INGEN > DEPOT: dødelighedsgevinster øger det forventede depot")
    print("  som forventet — overlevende nyder godt af de afdødes frigivne reserver.")
else:
    print("  Uventet resultat — kontrollér input.")
