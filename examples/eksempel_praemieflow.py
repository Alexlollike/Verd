"""
Eksempel: Præmieflow — risikodækninger og allokeringsalgoritme.

Demonstrerer:
  - Risikopræmie fratrækkes bruttopræmien (dødsfald/TAE/SUL)
  - Nettopræmien allokeres efter kundens ønsker, begrænset af beløbsgrænser
  - Forskel på ung forsikringstager (>7 år til pension) og nær-pension (<=7 år)
  - Depotudvikling med vs. uden risikodækninger over 10 år

Kør med:
    python examples/eksempel_praemieflow.py
"""

import math
from datetime import date

from verd import (
    BeloebsgraenserOpslag,
    DeterministicMarket,
    GompertzMakeham,
    Policy,
    PolicyState,
    PraemieFlow,
    PraemieFlowResultat,
    STANDARD_RISIKO_BUNDLE,
    STANDARD_SATSER_FILSTI,
    fremregn,
    initial_distribution,
    indlæs_offentlige_satser,
    praemieflow_cashflow_funktion,
    simpel_opsparings_cashflow,
    standard_toetilstands_model,
)

# ---------------------------------------------------------------------------
# Modeller
# ---------------------------------------------------------------------------
biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)
marked = DeterministicMarket(r=math.log(1.05), enhedspris_0=100.0)
satser = indlæs_offentlige_satser(STANDARD_SATSER_FILSTI)

# ---------------------------------------------------------------------------
# Scenarie 1: Ung forsikringstager — 35 år, >7 år til folkepension (67 år)
# Bruttopræmie: 100.000 kr/år, ønsket fordeling: 20% rate / 10% ald / 70% liv
# ---------------------------------------------------------------------------
print("=" * 65)
print("SCENARIE 1 — 35-årig (>7 år til folkepension)")
print("=" * 65)

BRUTTO_1 = 100_000.0
AAR_TIL_PENSION_1 = 67 - 35  # = 32 år

graenser_1 = BeloebsgraenserOpslag.fra_satser(satser, aar=2026, aar_til_folkepension=AAR_TIL_PENSION_1)
print(f"  Aldersopsparing max : {graenser_1.aldersopsparing_max:>10,.0f} DKK/år  (normal-niveau)")
print(f"  Ratepension max     : {graenser_1.ratepension_max:>10,.0f} DKK/år")
print(f"  Livrente max        : {'ingen':>10}")
print()

praemieflow_1 = PraemieFlow(beloebsgraenser=graenser_1)
resultat_1: PraemieFlowResultat = praemieflow_1.beregn(
    BRUTTO_1,
    ratepension_andel=0.20,
    aldersopsparing_andel=0.10,
    risiko_bundle=STANDARD_RISIKO_BUNDLE,
)

print(f"  Bruttopræmie        : {BRUTTO_1:>10,.0f} DKK/år")
print(f"  - Risikopræmie      : {resultat_1.risikopraemie_dkk:>10,.0f} DKK/år  (dødsfald + TAE + SUL)")
print(f"  = Nettopræmie       : {BRUTTO_1 - resultat_1.risikopraemie_dkk:>10,.0f} DKK/år")
print(f"    -> Ratepension      : {resultat_1.ratepension_dkk:>10,.0f} DKK/år  (ønsket 20 %)")
print(f"    -> Aldersopsparing  : {resultat_1.aldersopsparing_dkk:>10,.0f} DKK/år  (ønsket 10 %)")
print(f"    -> Livrente         : {resultat_1.livrente_dkk:>10,.0f} DKK/år  (rest -> livrente)")
print(f"  Kontrol (sum=brutto): {resultat_1.total_dkk:>10,.0f} DKK/år")

# ---------------------------------------------------------------------------
# Scenarie 2: Nær-pension — 62 år, <=7 år til folkepension
# Højere aldersopsparingsgrænse pga. nær-pension-reglen
# ---------------------------------------------------------------------------
print()
print("=" * 65)
print("SCENARIE 2 — 62-årig (<=7 år til folkepension, nær-pension)")
print("=" * 65)

BRUTTO_2 = 100_000.0
AAR_TIL_PENSION_2 = 67 - 62  # = 5 år

graenser_2 = BeloebsgraenserOpslag.fra_satser(satser, aar=2026, aar_til_folkepension=AAR_TIL_PENSION_2)
print(f"  Aldersopsparing max : {graenser_2.aldersopsparing_max:>10,.0f} DKK/år  (nær-pension-niveau)")
print(f"  Ratepension max     : {graenser_2.ratepension_max:>10,.0f} DKK/år")
print()

praemieflow_2 = PraemieFlow(beloebsgraenser=graenser_2)
resultat_2 = praemieflow_2.beregn(
    BRUTTO_2,
    ratepension_andel=0.20,
    aldersopsparing_andel=0.10,
    risiko_bundle=STANDARD_RISIKO_BUNDLE,
)

print(f"  Bruttopræmie        : {BRUTTO_2:>10,.0f} DKK/år")
print(f"  - Risikopræmie      : {resultat_2.risikopraemie_dkk:>10,.0f} DKK/år")
print(f"  = Nettopræmie       : {BRUTTO_2 - resultat_2.risikopraemie_dkk:>10,.0f} DKK/år")
print(f"    -> Ratepension      : {resultat_2.ratepension_dkk:>10,.0f} DKK/år")
print(f"    -> Aldersopsparing  : {resultat_2.aldersopsparing_dkk:>10,.0f} DKK/år  (nær-pension tillader mere)")
print(f"    -> Livrente         : {resultat_2.livrente_dkk:>10,.0f} DKK/år  (rest)")

# ---------------------------------------------------------------------------
# Scenarie 3: Høj bruttopræmie — cap rammer ratepension
# 400.000 kr/år: ønsket 20% rate = 79.700 > loft 68.700 -> overskud til livrente
# ---------------------------------------------------------------------------
print()
print("=" * 65)
print("SCENARIE 3 — Høj bruttopræmie (cap på ratepension rammer)")
print("=" * 65)

BRUTTO_3 = 400_000.0
resultat_3 = praemieflow_1.beregn(  # genbruger Scenarie 1's beloebsgraenser
    BRUTTO_3,
    ratepension_andel=0.20,
    aldersopsparing_andel=0.10,
    risiko_bundle=STANDARD_RISIKO_BUNDLE,
)

pi_netto_3 = BRUTTO_3 - resultat_3.risikopraemie_dkk
rate_ønsket_3 = pi_netto_3 * 0.20

print(f"  Bruttopræmie        : {BRUTTO_3:>10,.0f} DKK/år")
print(f"  - Risikopræmie      : {resultat_3.risikopraemie_dkk:>10,.0f} DKK/år")
print(f"  = Nettopræmie       : {pi_netto_3:>10,.0f} DKK/år")
print(f"    Ønsket ratepension : {rate_ønsket_3:>10,.0f} DKK/år  (20 % af netto)")
print(f"    Ratepension-loft   : {graenser_1.ratepension_max:>10,.0f} DKK/år")
print(f"    -> Ratepension      : {resultat_3.ratepension_dkk:>10,.0f} DKK/år  (beskåret)")
print(f"    -> Aldersopsparing  : {resultat_3.aldersopsparing_dkk:>10,.0f} DKK/år")
print(f"    -> Livrente         : {resultat_3.livrente_dkk:>10,.0f} DKK/år  (incl. overskud fra cap)")

# ---------------------------------------------------------------------------
# Scenarie 4: Sammenlign depotudvikling med vs. uden risikodækninger — 10 år
# ---------------------------------------------------------------------------
print()
print("=" * 65)
print("SCENARIE 4 — Depotudvikling over 10 år: med vs. uden risiko")
print("=" * 65)

police_base = Policy.fra_dkk(
    foedselsdato=date(1985, 6, 1),
    tegningsdato=date(2020, 1, 1),
    pensionsalder=67,
    er_under_udbetaling=False,
    gruppe_id="DK_MAND_2023",
    omkostningssats_id="STANDARD",
    loen=100_000.0,
    indbetalingsprocent=1.0,  # bruttopræmie = 100.000 kr/år
    aldersopsparing=50_000.0,
    ratepensionsopsparing=0.0,
    ratepensionsvarighed=10,
    livrentedepot=0.0,
    enhedspris=marked.enhedspris(0.0),
    ratepension_andel=0.0,
    aldersopsparing_andel=1.0,  # alt nettopræmie ønskes til aldersopsparing (op til loft)
    risiko_bundle=STANDARD_RISIKO_BUNDLE,
)
tilstandsmodel = standard_toetilstands_model(biometri)
ANTAL_AAR = 10

# Uden risikodækninger — simpel proportionsbaseret allokering
skridt_uden = fremregn(
    distribution=initial_distribution(police_base),
    antal_skridt=ANTAL_AAR * 12,
    market=marked,
    tilstandsmodel=tilstandsmodel,
    cashflow_funktion=simpel_opsparings_cashflow,
)

# Med risikodækninger og beløbsgrænser
graenser_scen4 = BeloebsgraenserOpslag.fra_satser(
    satser, aar=2026, aar_til_folkepension=67 - 35
)
pf_med = PraemieFlow(beloebsgraenser=graenser_scen4)
skridt_med = fremregn(
    distribution=initial_distribution(police_base),
    antal_skridt=ANTAL_AAR * 12,
    market=marked,
    tilstandsmodel=tilstandsmodel,
    cashflow_funktion=praemieflow_cashflow_funktion(pf_med),
)

depot_uden = skridt_uden[-1].forventet_depot_dkk
depot_med = skridt_med[-1].forventet_depot_dkk
forskel = depot_uden - depot_med
risiko_total = STANDARD_RISIKO_BUNDLE.aarlig_praemie_dkk * ANTAL_AAR

print(f"  Bruttopræmie pr. år : {100_000:>10,.0f} DKK")
print(f"  Risikopræmie pr. år : {STANDARD_RISIKO_BUNDLE.aarlig_praemie_dkk:>10,.0f} DKK  (1.500 kr/år)")
print()
print(f"  Depot efter {ANTAL_AAR} år (sandsynlighedsvægtet):")
print(f"    Uden risikodækning : {depot_uden:>12,.0f} DKK")
print(f"    Med risikodækning  : {depot_med:>12,.0f} DKK")
print(f"    Forskel            : {forskel:>12,.0f} DKK  (svarende til ~{risiko_total:,.0f} kr i risikopræmier inkl. afkast)")
