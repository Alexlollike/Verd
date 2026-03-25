"""
Eksempel: Plot af sandsynlighedsvægtede depoter — livrente + ratepension.

Police med kun to produkter:
  - Ratepension:  800 enh. × 100 DKK =  80.000 DKK ved tegning
  - Livrente:     500 enh. × 100 DKK =  50.000 DKK ved tegning
  - Aldersopsparing: 0 (ikke aktiv)

Fremregning: 27 år (fra alder 40 til pensionsalder 67), månedlige skridt.
Bidrag: 15 % af 600.000 DKK/år = 90.000 DKK/år fordelt proportionalt
        på ratepension (800/1300 ≈ 61,5 %) og livrente (500/1300 ≈ 38,5 %).

Kør med:
    python examples/eksempel_plot.py
"""

import matplotlib
matplotlib.use("Agg")  # Ikke-interaktiv backend (egnet til CI/scripts)

import matplotlib.pyplot as plt
from datetime import date

from verd import (
    DeterministicMarket,
    GompertzMakeham,
    Policy,
    PolicyState,
    fremregn,
    initial_distribution,
    simpel_opsparings_cashflow,
    standard_toetilstands_model,
)
from verd.plot import plot_fremregning

# ---------------------------------------------------------------------------
# Modeller
# ---------------------------------------------------------------------------
biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)
marked = DeterministicMarket(r=0.05, enhedspris_0=100.0)

# ---------------------------------------------------------------------------
# Police — kun ratepension + livrente, ingen aldersopsparing
# ---------------------------------------------------------------------------
police = Policy(
    foedselsdato=date(1980, 1, 15),
    tegningsdato=date(2020, 6, 1),
    pensionsalder=67,
    er_under_udbetaling=False,
    gruppe_id="DK_MAND_2023",
    omkostningssats_id="STANDARD",
    loen=600_000.0,
    indbetalingsprocent=0.15,        # 90.000 DKK/år
    aldersopsparing=0.0,             # ikke aktiv
    ratepensionsopsparing=800.0,     # 80.000 DKK
    ratepensionsvarighed=10,
    livrentedepot=500.0,             # 50.000 DKK
    tilstand=PolicyState.I_LIVE,
)

# ---------------------------------------------------------------------------
# Tilstandsmodel og fremregning — 27 år til pension
# ---------------------------------------------------------------------------
alder_ved_tegning = police.alder_ved_tegning()           # ≈ 40,4 år
t_pension = police.pensionsalder - alder_ved_tegning     # ≈ 26,6 år
antal_skridt = round(t_pension * 12)                     # månedlige skridt

tilstandsmodel = standard_toetilstands_model(biometri)

skridt = fremregn(
    distribution=initial_distribution(police),
    antal_skridt=antal_skridt,
    market=marked,
    tilstandsmodel=tilstandsmodel,
    cashflow_funktion=simpel_opsparings_cashflow,
    dt=1 / 12,
)

# ---------------------------------------------------------------------------
# Udskriv summary
# ---------------------------------------------------------------------------
slut = skridt[-1]
il = slut.i_live
print("=" * 65)
print("SIMPEL POLICE — RATEPENSION + LIVRENTE (uden aldersopsparing)")
print("=" * 65)
print(f"  Fremregning      : {len(skridt)-1} skridt ({(len(skridt)-1)/12:.1f} år)")
print(f"  Alder ved start  : {alder_ved_tegning:.1f} år")
print(f"  Pensionsalder    : {police.pensionsalder} år  (t ≈ {t_pension:.1f} år)")
print()
print(f"  {'':25s}  {'Betinget':>12}  {'Sandsynlighed':>14}  {'E[Depot]':>12}")
print(f"  {'':25s}  {'(givet I_LIVE)':>12}  {'p(I_LIVE)':>14}  {'':>12}")
print(f"  {'-'*67}")
if il:
    print(f"  {'Ratepension':25s}  {il.ratepension_dkk:>12,.0f}  {il.prob:>14.6f}  {il.prob*il.ratepension_dkk:>12,.0f}")
    print(f"  {'Livrente':25s}  {il.livrente_dkk:>12,.0f}  {il.prob:>14.6f}  {il.prob*il.livrente_dkk:>12,.0f}")
    print(f"  {'Total':25s}  {il.total_depot_dkk:>12,.0f}  {'':>14}  {il.forventet_depot_dkk:>12,.0f}")
print("=" * 65)

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig = plot_fremregning(
    skridt=skridt,
    titel="Depotudvikling — ratepension + livrente (opsparingsfase, 27 år)",
    pensionsalder_t=t_pension,
    gem_fil="depot_udvikling.png",
)

print()
print("Plot gemt: depot_udvikling.png")
plt.close(fig)
