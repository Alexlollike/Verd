"""
Eksempel: To-faseprojektering — opsparingsfase + udbetalingsfase.

Police med tre produkter:
  - Aldersopsparing: 20.000 DKK ved tegning — ingen løbende indbetalinger
  - Ratepension:     20.000 DKK ved tegning
  - Livrente:        50.000 DKK ved tegning

Opsparingsfase: alder 40 → 67 (≈ 27 år), bidrag 15 % af 600.000 DKK/år
fordeles via PraemieFlow med aldersopsparing_andel=0 (bidrag kun til rate+livrente).
Aldersopsparingen vokser med afkast og udbetales som engangsudbetaling ved pension.
Udbetalingsfase: ratepension over 10 år, livrente livsvarigt (op til 107 år).

Kør med:
    python examples/eksempel_plot.py
"""

import matplotlib
matplotlib.use("Agg")  # Ikke-interaktiv backend (egnet til CI/scripts)

import matplotlib.pyplot as plt
import pandas as pd
from datetime import date

from verd import (
    DeterministicMarket,
    GompertzMakeham,
    Policy,
    PolicyState,
    PraemieFlow,
    eksporter_cashflows_csv,
    fremregn,
    initial_distribution,
    plot_fra_dataframe,
    praemieflow_cashflow_funktion,
    simpel_cashflow_funktion,
    standard_omkostning,
    standard_toetilstands_model,
)

# ---------------------------------------------------------------------------
# Modeller
# ---------------------------------------------------------------------------
biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)
marked = DeterministicMarket(r=0.05, enhedspris_0=100.0)

# ---------------------------------------------------------------------------
# Police — aldersopsparing (ingen indbetalinger) + ratepension + livrente
# ---------------------------------------------------------------------------
police = Policy.fra_dkk(
    foedselsdato=date(1980, 1, 15),
    tegningsdato=date(2020, 6, 1),
    pensionsalder=67,
    er_under_udbetaling=False,
    gruppe_id="DK_MAND_2023",
    omkostningssats_id="STANDARD",
    loen=600_000.0,
    indbetalingsprocent=0.15,        # 90.000 DKK/år — fordeles KUN på rate+livrente
    aldersopsparing=20_000.0,        # DKK — vokser med afkast, ingen løbende bidrag
    ratepensionsopsparing=20_000,    # DKK
    ratepensionsvarighed=10,
    livrentedepot=50_000.0,          # DKK
    enhedspris=marked.enhedspris(0.0),
    tilstand=PolicyState.I_LIVE,
)

alder_ved_tegning = police.alder_ved_tegning()        # ≈ 40,4 år
t_pension = police.pensionsalder - alder_ved_tegning  # ≈ 26,6 år
antal_skridt_op = round(t_pension * 12)

tilstandsmodel = standard_toetilstands_model(biometri)

# Omkostningsmodel: 0% indbetalingsomkostning, 0,5% AUM p.a., 200 DKK/år styk
omk = standard_omkostning(marked, aum_rate=0.005, styk_aar=200.0)


# ---------------------------------------------------------------------------
# Præmieallokering — kun ratepension og livrente modtager løbende indbetalinger.
# Andele sat proportionalt med de initielle depotværdier (ald udeladt):
#   ratepension  : 20.000 / 70.000 ≈ 0,286
#   livrente (rest): 50.000 / 70.000 ≈ 0,714
# ---------------------------------------------------------------------------
praemieallokering = PraemieFlow(
    risiko_bundle=None,
    beloebsgraenser=None,
    ratepension_andel=20_000 / 70_000,
    aldersopsparing_andel=0.0,
)

# ---------------------------------------------------------------------------
# Enkelt fremregning over hele livscyklussen — simpel_cashflow_funktion
# håndterer skiftet fra opsparing til udbetaling automatisk ved t_pension.
# ---------------------------------------------------------------------------
cashflow = simpel_cashflow_funktion(
    biometric=biometri,
    market=marked,
    opsparing_func=praemieflow_cashflow_funktion(praemieallokering),
)

skridt = fremregn(
    distribution=initial_distribution(police),
    antal_skridt=antal_skridt_op + 40 * 12,
    market=marked,
    tilstandsmodel=tilstandsmodel,
    cashflow_funktion=cashflow,
    omkostnings_funktion=omk,
    dt=1 / 12,
    t_0=0.0,
)

# ---------------------------------------------------------------------------
# Udskriv summary
# ---------------------------------------------------------------------------
il_pension = skridt[antal_skridt_op].i_live
assert il_pension is not None, "Ingen I_LIVE-tilstand ved pensionsdato"

aldersopsparing_dkk_ved_pension = il_pension.aldersopsparing_dkk

print("=" * 65)
print("POLICE — ALDERSOPSPARING + RATEPENSION + LIVRENTE")
print("=" * 65)
print(f"  Opsparingsfase   : {antal_skridt_op} skridt ({antal_skridt_op/12:.1f} aar)")
print(f"  Udbetalingsfase  : {40*12} skridt (40,0 aar)")
print(f"  Alder ved start  : {alder_ved_tegning:.1f} aar")
print(f"  Pensionsalder    : {police.pensionsalder} aar  (t ca. {t_pension:.1f} aar)")
print()
print(f"  VED PENSION (t = {t_pension:.1f} aar):")
print(f"    p(I_LIVE)         : {il_pension.prob:.6f}")
print(f"    Aldersopsparing   : {il_pension.aldersopsparing_dkk:>12,.0f} DKK  (engangsudbetaling)")
print(f"    Ratepension       : {il_pension.ratepension_dkk:>12,.0f} DKK")
print(f"    Livrente          : {il_pension.livrente_dkk:>12,.0f} DKK")
print(f"    Total depot       : {il_pension.total_depot_dkk:>12,.0f} DKK")
print(f"    Engangsudbetaling ald.: {aldersopsparing_dkk_ved_pension:>10,.0f} DKK  (ved pension)")
cf_start = skridt[antal_skridt_op + 1].cashflows_i_live if len(skridt) > antal_skridt_op + 1 else None
if cf_start:
    print(f"    Ratepensionsydelse    : {cf_start.b_ratepension:>10,.0f} DKK/aar")
    print(f"    Livrenteydelse        : {cf_start.b_livrente:>10,.0f} DKK/aar")
print("=" * 65)

# ---------------------------------------------------------------------------
# Eksportér til CSV og dan figuren fra CSV-filen
# ---------------------------------------------------------------------------
eksporter_cashflows_csv(skridt, "cashflows.csv")
print()
print("CSV gemt: cashflows.csv")

df = pd.read_csv("cashflows.csv")

fig = plot_fra_dataframe(
    df=df,
    titel="Depotudvikling og ydelser — aldersopsparing + ratepension + livrente",
    pensionsalder_t=t_pension,
    gem_fil="depot_udvikling.png",
    ald_lumpsum_dkk=aldersopsparing_dkk_ved_pension,
)

print("Plot gemt: depot_udvikling.png")
plt.close(fig)
