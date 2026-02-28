# Phase 2: Cashflow-fremregning - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Implementér en funktion `fremregn()` der tager en `PolicyDistribution`, en `BiometricModel` og en `FinancialMarket`, og returnerer en komplet cashflow-tidsserie for hele fremregningsperioden (fra nu til pension + evt. udbetalingsperiode). Reserveberegning (diskontering) er Fase 3 — fremregning returnerer kun kasseteorie-flows, ikke nutidsværdier.

</domain>

<decisions>
## Implementation Decisions

### Returtype
- `fremregn()` returnerer en **pandas DataFrame** — én række per tidsstep
- Kolumner dækker alt hvad Fase 3 (diskontering) og Fase 4 (CSV/print) har brug for
- DataFrame er standard i aktuarfaglig Python og giver nem filtrering og debugging

### Cashflow-kolonner
Minimum nødvendige kolonner per tidsstep:
- `t` — tidspunkt i år som float (t=0.0, 1/12, 2/12, ...) — konsistent med matematikken
- `alder` — forsikringstagers alder i år på tidspunktet
- `sandsynlighed_i_live` — marginal sandsynlighed for I_LIVE tilstand
- `enhedspris` — DeterministicMarket.enhedspris(t)
- `depot_total_dkk` — samlet depotværdi i DKK = total_enheder × enhedspris
- `indbetaling_dkk` — bruttoindbetaling i DKK (0 i udbetalingsfasen)
- `risikopraemie_dkk` — dødsfaldsdækning (risikopræmie) i DKK

### Indbetalingsfordeling
- Månedlig indbetaling = `loen × indbetalingsprocent / 12` i DKK
- Indbetalinger fordeles **proportonalt** på alle tre depoter baseret på deres aktuelle enheder-andel
- I udbetalingsfasen (`er_under_udbetaling = True`): ingen indbetalinger — `indbetaling_dkk = 0`
- Indbetalinger konverteres til enheder via enhedspris: `enheder = dkk / enhedspris(t)`

### Tidsskala
- `t` er tid i år som float fra tegningsdato: `t ∈ {0, 1/12, 2/12, ...}`
- Alder beregnes fra `foedselsdato` og nuværende `t`: `alder = alder_ved_tegning + t`
- Fremregning kører fra `t=0` til udløb af udbetalingsperiode eller ved naturlig stop

### Biometrisk transition
- Overlevelsessandsynlighed per skridt: `p = exp(-µ(alder) × dt)` med `dt = 1/12`
- `sandsynlighed_i_live` opdateres multiplikativt: `p_live[t+dt] = p_live[t] × p`
- Rækkefølge inden for tidsstep: **indbetalinger → afkast (enhedsprisvækst) → biometri → omkostninger**
- Afkast afspejles KUN via enhedsprisvækst — enheder i depotet ændres IKKE (unit-link design)

### Fremregningens stop
- Fremregning stopper ved `sandsynlighed_i_live < 1e-6` (praktisk tilgang) eller ved en givet maksalder
- Claude bestemmer fornuftig maksalder (f.eks. 110 år)

### Modulstruktur
- Ny fil: `verd/projection.py` — indeholder `fremregn()` og hjælpefunktioner
- Konsistent med "én klasse / ét koncept per fil"-princippet fra CLAUDE.md

### Claude's Discretion
- Præcis definition af risikopræmie (sum at risk — forskel mellem dækning og depot)
- Håndtering af overgangslogik I_LIVE → DOED i PolicyDistribution
- Eventuelle hjælpefunktioner til aldersberegning

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BiometricModel.survival_probability(alder, dt)` og `death_probability(alder, dt)` — klar til brug i biometrisk transition
- `BiometricModel.mortality_intensity(alder)` — bruges til `p = exp(-µ × dt)`
- `DeterministicMarket.enhedspris(t)` — returnerer enhedspris ved tidspunkt t
- `DeterministicMarket.dkk_til_enheder(dkk, t)` og `enheder_til_dkk(enheder, t)` — konvertering
- `Policy.total_enheder()` — samlet enheder på tværs af depoter
- `Policy.depotvaerdi_dkk(enhedspris)` — depot i DKK
- `initial_distribution(policy)` — starter PolicyDistribution med [(policy, 1.0)]

### Established Patterns
- **Enheder, ikke DKK** — depoter gemmes som enheder; DKK beregnes ved at gange med enhedspris
- **Kontinuert matematik, diskret tid** — intensiteter (µ) er per år; sandsynligheder approximeres via `exp(-µ × dt)` med `dt = 1/12`
- **Dataclasses** til domæneobjekter; **type hints** på alle funktioner; **docstrings med formler**
- **Dansk navngivning** for domænebegreber (sandsynlighed_i_live, indbetaling_dkk, etc.)

### Integration Points
- `fremregn()` modtager `PolicyDistribution` (fra `initial_distribution()`) + `BiometricModel` + `FinancialMarket`
- Fase 3 (Reserveberegning) konsumerer den returnerede DataFrame til diskontering
- Fase 4 (Output) printer og eksporterer DataFramen til CSV

</code_context>

<specifics>
## Specific Ideas

- CLAUDE.md specificerer rækkefølgen eksplicit: *indbetalinger → afkast → biometri → omkostninger* — dette skal dokumenteres tydeligt i koden
- `dt = 1/12` er fastlagt og skal fremgå eksplicit i koden (ikke hardcoded magic number)
- Eksempelpolicen i `examples/eksempel_police.py` bruges som reference for eksempelkørslen

</specifics>

<deferred>
## Deferred Ideas

- Omkostningssatser (OmkostningssatsID) — slås op i separate tabeller; Phase 2 bruger `omkostningssats_id` som nøgle, men selve satserne defineres i Fase 2+ (per CLAUDE.md)
- Udbetalingslogik (annuitet, ratepension udbetaling) — kræver `er_under_udbetaling = True`; Phase 2 kan simplificere og fokusere på opsparingsfasen
- Risikopræmie-beregning (sum at risk) — basisimplementering er tilstrækkelig i Fase 2; præcis aktuarisk definition kan raffineres i Fase 3

</deferred>

---

*Phase: 02-cashflow-fremregning*
*Context gathered: 2026-02-28*
