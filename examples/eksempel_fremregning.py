"""
Eksempel: Thiele-baseret sandsynlighedsvægtet fremregning (Phase 2 done-kriterium).

Demonstrerer:
  - Fremregning via koblede Thiele-ligninger med vilkårligt tilstandsrum
  - 2-tilstands standardmodel (I_LIVE → DOED) via standard_toetilstands_model()
  - Sandsynlighedsvægtet depot (prob_I_LIVE × betinget depot)
  - Cashflow-tabel for en eksempelpolicy over 5 år (60 månedlige skridt)

Kør med:
    python examples/eksempel_fremregning.py
"""

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

# ---------------------------------------------------------------------------
# Modeller
# ---------------------------------------------------------------------------
biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)
marked = DeterministicMarket(r=0.05, enhedspris_0=100.0)

# ---------------------------------------------------------------------------
# Police
# ---------------------------------------------------------------------------
police = Policy.fra_dkk(
    foedselsdato=date(1980, 1, 15),
    tegningsdato=date(2020, 6, 1),
    pensionsalder=67,
    er_under_udbetaling=False,
    gruppe_id="DK_MAND_2023",
    omkostningssats_id="STANDARD",
    loen=600_000.0,              # 600.000 DKK/år
    indbetalingsprocent=0.15,    # 15 % af løn → 90.000 DKK/år
    aldersopsparing=120_000.0,   # DKK
    ratepensionsopsparing=80_000.0,  # DKK
    ratepensionsvarighed=10,
    livrentedepot=50_000.0,      # DKK
    enhedspris=marked.enhedspris(0.0),
    tilstand=PolicyState.I_LIVE,
)

fordeling = initial_distribution(police)

# ---------------------------------------------------------------------------
# Tilstandsmodel — standard to-tilstands (I_LIVE → DOED)
# ---------------------------------------------------------------------------
tilstandsmodel = standard_toetilstands_model(biometri)

# ---------------------------------------------------------------------------
# Fremregning — 5 år (60 månedlige skridt)
# ---------------------------------------------------------------------------
ANTAL_AAR = 5
skridt = fremregn(
    distribution=fordeling,
    antal_skridt=ANTAL_AAR * 12,
    market=marked,
    tilstandsmodel=tilstandsmodel,
    cashflow_funktion=simpel_opsparings_cashflow,
    dt=1 / 12,
    t_0=0.0,
)

# ---------------------------------------------------------------------------
# Udskriv tabel — én linje per år (hvert 12. skridt)
# ---------------------------------------------------------------------------
print("=" * 100)
print("THIELE-BASERET FREMREGNING — BETINGEDE FORVENTEDE DEPOTER")
print("=" * 100)
print(
    f"{'t (år)':>7}  {'Alder':>6}  {'p(I_LIVE)':>10}  "
    f"{'Ald.opsp.':>12}  {'Ratepens.':>12}  {'Livrente':>12}  "
    f"{'Total depot':>13}  {'E[Depot]':>13}  {'Indbetal.':>11}  {'Kurs':>8}"
)
print("-" * 100)

for s in skridt:
    step_nr = round(s.t * 12)
    if step_nr % 12 == 0:
        il = s.i_live
        if il is None:
            continue
        print(
            f"{s.t:>7.2f}  {s.alder:>6.2f}  {il.prob:>10.6f}  "
            f"{il.aldersopsparing_dkk:>12,.0f}  {il.ratepension_dkk:>12,.0f}  "
            f"{il.livrente_dkk:>12,.0f}  "
            f"{il.total_depot_dkk:>13,.0f}  {il.forventet_depot_dkk:>13,.0f}  "
            f"{s.indbetaling_dkk:>11,.0f}  {s.enhedspris:>8.4f}"
        )

print("-" * 100)

# ---------------------------------------------------------------------------
# Detaljeret månedlig tabel (første 6 måneder)
# ---------------------------------------------------------------------------
print()
print("MÅNEDLIG DETALJE — FØRSTE 6 MÅNEDER")
print("-" * 100)
print(
    f"{'t (år)':>7}  {'Alder':>6}  {'p(I_LIVE)':>10}  "
    f"{'Total depot':>13}  {'E[Depot]':>13}  "
    f"{'Indbetal./md':>13}  {'Kurs':>8}"
)
print("-" * 100)
for s in skridt[:7]:
    il = s.i_live
    if il is None:
        continue
    print(
        f"{s.t:>7.4f}  {s.alder:>6.2f}  {il.prob:>10.8f}  "
        f"{il.total_depot_dkk:>13,.2f}  {il.forventet_depot_dkk:>13,.2f}  "
        f"{s.indbetaling_dkk:>13,.2f}  {s.enhedspris:>8.4f}"
    )

print()
print("=" * 100)
print("Phase 2 done-kriterium: Cashflow-tabel printet via Thieles differentialligning ✓")
print("=" * 100)
