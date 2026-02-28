# Phase 2: Cashflow-fremregning - Context

**Gathered:** 2026-02-28 (revideret efter teorigennemgang)
**Status:** Ready for planning

<domain>
## Phase Boundary

Implementér en funktion `fremregn()` der tager en `PolicyDistribution`, en `BiometricModel` og
en `FinancialMarket`, og returnerer en komplet cashflow-tidsserie for fremregningsperioden.

Reserveberegning (diskontering via Thieles differentialligning) er Fase 3.
`fremregn()` returnerer kun forventede cashflows — ikke nutidsværdier.

</domain>

<decisions>
## Implementation Decisions

### Matematisk fundament — betalingsprocesser

Produkter defineres via **betalingsprocessen** `B(t)` (jf. LivStok kap. 14–16):

```
dB(t) = b^{Z(t)}(t) dt  +  Σ_k b^{Z(t-)k}(t) dN^k(t)
```

- `b^j(t)` — kontinuert betalingsrate i tilstand j (positiv = ydelse til forsikringstager,
  negativ = præmie fra forsikringstager)
- `b^{jk}(t)` — engangsbetaling ved overgang fra tilstand j til k

For vores to-tilstandsmodel (J = {0=I_LIVE, 1=DOED}) er betalingsprocessen:

```
b^0(t) = -π(t) × 1_{NOT er_under_udbetaling}        # præmierate (negativ = indbetaling)
b^{01}(t) = sum_at_risk(t)                            # dødsfaldsdækning ved overgang I_LIVE→DOED
b^1(t) = 0                                            # ingen betalinger i DOED (absorberende tilstand)
```

Bemærk: I fase 2 fokuserer vi på opsparingsfasen. Udbetalingsfasen (pension annuitet som
positiv `b^0(t)`) er udskudt til Phase 2+.

### Overgangsintensitet og Kolmogorov

Overgangssandsynligheder styres af Kolmogorovs fremadrettede ligning.
For to-tilstandsmodellen:

```
d/dt p_{00}(0, t) = -p_{00}(0, t) × μ^{01}(alder(t))
```

Diskret approksimation (dt = 1/12 år):

```
p_{00}(0, t+dt) = p_{00}(0, t) × exp(-μ(alder(t)) × dt)
```

Dette er `sandsynlighed_i_live` i DataFramen — beregnet via
`BiometricModel.survival_probability(alder, dt)` = `exp(-μ(alder) × dt)`.

### Forventet cashflow per tidsstep

Den forventede cashflow (betingede på Z(0) = I_LIVE) er (jf. Buchardt & Møller 2015,
Proposition 3):

```
dA_0(0, s) = p_{00}(0, s) × (b^0(s) + μ^{01}(s) × b^{01}(s)) × ds
```

Dvs.:

```
forventet_indbetaling(s) = p_live(s) × π(s) × dt
forventet_risikopraemie(s) = p_live(s) × μ(alder(s)) × sum_at_risk(s) × dt
```

`fremregn()` returnerer en DataFrame der per tidsstep (dt = 1/12) eksponerer disse
komponenter, så Fase 3 kan diskontere dem via Thieles ligning.

### Betalingsprocessernes konkrete definition

**Præmie (b^0):**
```
π(t) = loen × indbetalingsprocent / 12   # DKK per måned
```
Indbetaling sker kun i opsparingsfasen (`er_under_udbetaling = False`).
Konverteres til enheder: `enheder = π(t) / enhedspris(t)`.

**Dødsfaldsdækning (b^{01}) — sum at risk:**
For unit-link uden ekstern dødsfaldsdækning: `b^{01}(t) = 0` og `risikopraemie = 0`.
Implementationsvalg (Claude's discretion): Fase 2 antager ingen ekstern dødsfaldsdækning
ud over depotværdien, dvs. `sum_at_risk = 0`. Risikopræmie-kolonnen indgår i DataFramen
men er 0 i baseline. Kan raffineres i Fase 3 hvis konkret doedssum tilføjes til Policy.

**Rationale:** For rene unit-link produkter uden garantier = dødsfaldsdækning er depotværdien,
sum at risk = depot_dkk - depot_dkk = 0.

### Indbetalingsfordeling på depoter

Indbetaling fordeles **proportionalt** på de tre depoter (aldersopsparing,
ratepensionsopsparing, livrentedepot) baseret på aktuelle enheder-andele:

```
andel_j = depot_j_enheder / total_enheder
enheder_til_depot_j = (π(t) / enhedspris(t)) × andel_j
```

Hvis `total_enheder = 0`: fordeles ligeligt (1/3 til hvert depot).

### Returtype

`fremregn()` returnerer en **pandas DataFrame** — én række per tidsstep.
Alle beløb i DKK. Alle sandsynligheder som float [0, 1].

### Cashflow-kolonner

Minimum nødvendige kolonner per tidsstep:

| Kolonne | Type | Forklaring |
|---|---|---|
| `t` | float | Tid i år fra tegningsdato (0.0, 1/12, 2/12, ...) |
| `alder` | float | Forsikringstagers alder i år |
| `sandsynlighed_i_live` | float | p_{00}(0,t) — Kolmogorov-sandsynlighed |
| `enhedspris` | float | DeterministicMarket.enhedspris(t) |
| `depot_enheder` | float | Samlet enheder (total_enheder) |
| `depot_dkk` | float | depot_enheder × enhedspris |
| `indbetaling_dkk` | float | π(t) × dt (0 i udbetalingsfasen) — råværdi, ikke p-vægtet |
| `risikopraemie_dkk` | float | μ(alder) × sum_at_risk × dt (0 i baseline) |

Bemærk: `indbetaling_dkk` og `risikopraemie_dkk` er **ikke** sandsynlighedsvægtede i
selve kolonnen — `sandsynlighed_i_live`-kolonnen bruges til vægtning i Fase 3.
Denne adskillelse giver fuld sporbarhed og nem debugging.

### Rækkefølge af operationer inden for tidsstep

Som specificeret i CLAUDE.md, i denne orden:
1. **Indbetaling** — præmie konverteres til enheder og lægges til depoterne
2. **Afkast** — ingen enheds-ændring; enhedspris vokser automatisk via DeterministicMarket
3. **Biometri** — `p_live *= exp(-μ(alder) × dt)` via BiometricModel.survival_probability
4. **Omkostninger** — udskudt til Phase 2+ (OmkostningssatsID kun nøgle i v1.0)

dt = 1/12 er fastlåst og fremgår eksplicit som navngiven konstant i koden.

### Tidsskala

- `t` i år som float fra tegningsdato: `t ∈ {0, 1/12, 2/12, ...}`
- Alder: `alder(t) = alder_ved_tegning + t`
- Fremregning kører fra `t=0` til `sandsynlighed_i_live < 1e-6` eller max-alder = 110 år

### Modulstruktur

- Ny fil: `verd/projection.py` — indeholder `fremregn()` og evt. hjælpefunktioner
- Konsistent med "én klasse / ét koncept per fil"-princippet fra CLAUDE.md

### Forbindelse til Fase 3 (Thiele)

`fremregn()` returnerer den cashflow-tidsserie som Fase 3 skal diskontere.
Thieles differentialligning (Theorem 16.2 i LivStok):

```
dV^0/dt = r(t)V^0(t) - b^0(t) - μ^{01}(t)(b^{01}(t) + V^1(t) - V^0(t))
```

Med V^1(t) = 0 (DOED er absorberende, ingen fremtidige betalinger):

```
dV^0/dt = r(t)V^0(t) - b^0(t) - μ(t)(sum_at_risk(t) - V^0(t))
        = (r(t) + μ(t))V^0(t) - b^0(t) - μ(t) × sum_at_risk(t)
```

Dette er Fase 3's ansvarsområde — Fase 2 leverer kun b^0(t), μ(t), p_{00}(0,t) og
depot_dkk(t) per tidsstep.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BiometricModel.survival_probability(alder, dt)` — `exp(-μ(alder) × dt)` klar til brug
- `BiometricModel.mortality_intensity(alder)` — μ(x) til risikopræmie-beregning
- `DeterministicMarket.enhedspris(t)` — enhedspris ved tidspunkt t
- `DeterministicMarket.dkk_til_enheder(dkk, t)` og `enheder_til_dkk(enheder, t)`
- `Policy.total_enheder()` — Σ(aldersopsparing + ratepensionsopsparing + livrentedepot)
- `Policy.depotvaerdi_dkk(enhedspris)` — depot i DKK
- `initial_distribution(policy)` — starter PolicyDistribution med [(policy, 1.0)]

### Established Patterns
- **Enheder, ikke DKK** — depoter i enheder; DKK = enheder × enhedspris
- **Kontinuert matematik, diskret tid** — µ er per år; sandsynligheder via exp(-µ×dt)
- **Dataclasses** til domæneobjekter; **type hints**; **docstrings med formler**
- **Dansk navngivning** for domænebegreber

### Integration Points
- `fremregn()` modtager `PolicyDistribution` (fra `initial_distribution()`) + modeller
- Fase 3 konsumerer DataFrame til diskontering via Thiele
- Fase 4 printer og eksporterer DataFramen

</code_context>

<specifics>
## Specific Ideas

- Betalingsprocessernes definition (b^j, b^{jk}) skal fremgå eksplicit i docstrings
- `dt = 1/12` defineres som navngiven konstant (ikke magic number)
- Rækkefølgen indbetalinger → afkast → biometri → omkostninger dokumenteres som kommentar
  i fremregningsloopet
- Eksempelpolicen i `examples/eksempel_police.py` bruges til CASH-05 (printbart output)
- Matematisk reference til Kolmogorov fremadrettet ligning i kodekommentar

</specifics>

<deferred>
## Deferred Ideas

- **Udbetalingslogik** — `b^0(t) > 0` som pensionsannuitet i udbetalingsfasen (er_under_udbetaling=True)
  udskudt til Phase 2+
- **Ekstern dødsfaldsdækning** — sum_at_risk > 0 kræver `doedssum` felt på Policy; gemmes til Phase 3+
- **Omkostninger** — OmkostningssatsID-opslag defineres i Phase 2+
- **Sandsynlighedsvægtede cashflows** som separate kolonner — Fase 3 håndterer dette ved
  at multiplicere med sandsynlighed_i_live

</deferred>

---

*Phase: 02-cashflow-fremregning*
*Context gathered: 2026-02-28 (revideret med teorigrundlag fra LivStok.pdf og Buchardt & Møller 2015)*
