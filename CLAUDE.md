# Aktuarbibliotek — Enkeltpolicefremregning

## Projektbeskrivelse

Python-bibliotek til sandsynlighedsvægtet fremregning af enkeltpolice reserver og cashflows.
Produktfokus: **Rene markedsrenteprodukter uden garantier** (aldersopsparing, ratepension, livrente).
Arkitektur: Policen modelleres som en **flerdimensionel Markov-proces** i diskret tid.

---

## Scope for v1.0 — Overhold dette

- Kun **enkeltpolicy** (ingen porteføljeaggregering)
- Kun **to policetilstande**: I_LIVE og DØD
- Kun **sandsynlighedsvægtet fremregning** (ikke simulering)
- Kun **deterministisk finansielt marked**
- Kun **Gompertz-Makeham** dødelighedsintensitet
- Ingen stokastiske scenarier, ingen UI, ingen rapportgenerator

Øvrige features (invalid, fripolice, genkøbt, simulering, portefølje) gemmes til backlog.

---

## Dansk Terminologi (brug disse præcist i kode og kommentarer)

| Dansk term | Forklaring | Python-navn (forslag) |
|---|---|---|
| Policetilstand | Markov-tilstand for policen | `PolicyState` (enum) |
| I live | Aktiv tilstand | `PolicyState.I_LIVE` |
| Død | Død tilstand | `PolicyState.DOED` |
| Tegningsdato | Dato policen er oprettet | `tegningsdato` |
| Fødselsdato | Forsikringstagers fødselsdato | `foedselsdato` |
| Depotværdi | Sum af alle tre depoter | beregnet: `aldersopsparing + ratepensionsopsparing + livrentedepot` |
| Aldersopsparing | Depot til engangsudbetaling ved pensionering | `aldersopsparing` |
| Ratepensionsopsparing | Depot hørende til ratepension | `ratepensionsopsparing` |
| Ratepensionsvarighed | Udbetalingsperiode for ratepension (år) | `ratepensionsvarighed` |
| Livrentedepot | Depot hørende til livrente | `livrentedepot` |
| Pensionsalder | Alder ved pensionering | `pensionsalder` |
| Løn | Forsikringstagers løn (bruges til indbetalingsberegning) | `loen` |
| Indbetalingsprocent | Procent af løn indbetalt til depot | `indbetalingsprocent` |
| GruppeID | Nøgle til dødelighedsintensitets-opslagstabel | `gruppe_id` |
| OmkostningssatsID | Nøgle til omkostningssats-opslagstabel | `omkostningssats_id` |
| Dødelighedsintensitet | Hazard rate µ(x) for død | `mortality_intensity` |
| Risikopræmie | Præmie til dækning af biometrisk risiko | `risikopraemie` |
| Udbetalingsannuitet | Livsvarig udbetaling ved pensionering | `udbetalingsannuitet` |
| Fremregning | Fremprojektion af police i tid | projection / `fremregn()` |
| Sandsynlighedsvægtet fremregning | Fremregning over middelværdi af Markov-tilstande | `probability_weighted_projection` |
| Policedistribution | Vektor af (Police, sandsynlighed)-par, én per Markov-tilstand | `PolicyDistribution` |
| Thiele | Thieles differentialligning — drives fremregningen | `thiele_step()` |
| Udbetalingsfase | Om policen er under udbetaling (True) eller opsparing (False) | `er_under_udbetaling` |

---

## Arkitektur

### Centrale klasser

```
Policy                  # Markov-tilstandsvektor — alt til fremregning ligger her
PolicyState (enum)      # I_LIVE | DOED  (udvides til INVALID, FRIPOLICE, GENKOBT)
PolicyDistribution      # list[tuple[Policy, float]] — (policy, sandsynlighed) pr. tilstand

BiometricModel (ABC)    # Abstrakt — leverer dødelighedsintensiteter
  └── GompertzMakeham   # µ(x) = alpha + beta * exp(sigma * x)

FinancialMarket (ABC)   # Abstrakt — leverer afkast og diskonteringsfaktorer
  └── DeterministicMarket  # Fast årlig afkastrate
```

### Design-principper

- `BiometricModel` og `FinancialMarket` er **fuldstændigt uafhængige** — de kobles kun i fremregningslaget
- `depotværdi` er **ikke** et felt på `Policy` — beregnes altid som `aldersopsparing + ratepensionsopsparing + livrentedepot`
- `OmkostningssatsID` og `GruppeID` er blot **nøgler** — selve satserne slås op i separate tabeller (defineres i Phase 2+)
- Fremregning sker i **diskret tid** med **månedlige tidsskridt**: `dt = 1/12`
- `er_under_udbetaling: bool` er et felt på `Policy` — styrer om policen er i opsparing (indbetalinger) eller udbetaling i det givne tidsstep

### OBS: Diskret tid vs. kontinuert matematik

Implementationen bruger diskret tid (pga. policeadministrationssystemet), men den underliggende matematik er formuleret i kontinuert tid (Thiele, intensiteter). Vær eksplicit om:
- **Tidsenheden er fastlagt**: `dt = 1/12` (månedlige skridt)
- **Rækkefølgen af operationer** inden for hvert tidsstep (indbetalinger → afkast → biometri → omkostninger — dokumenter dette)
- **Intensitet → sandsynlighed**: brug `p = exp(-µ * dt)` for overlevelsessandsynlighed
- **`er_under_udbetaling`** er et eksplicit felt på `Policy` — det styres ikke automatisk ud fra `pensionsalder`. `pensionsalder` er det *planlagte* pensionstidspunkt, men forsikringstager kan vælge at udskyde udbetalingen, og feltet afspejler den faktiske tilstand

---

## Faseoversigt

| Fase | Indhold | Done-kriterium |
|---|---|---|
| **1 — Data & Antagelser** | `Policy`-dataklasse, `PolicyState` enum, `PolicyDistribution`, `BiometricModel`+`GompertzMakeham`, `FinancialMarket`+`DeterministicMarket` | Kan beskrive en police i kode og printe den |
| **2 — Cashflow-fremregning** | Funktion der tager `PolicyDistribution` + modeller og returnerer tidsserie af cashflows | Kan printe cashflow-tabel for en eksempelpolicy |
| **3 — Reserveberegning** | Diskontering af cashflows til reserve (Thiele-baseret) | Et enkelt reservetal for en eksempelpolicy |
| **4 — Validering & Output** | Sanity checks + CSV/print output | Resultater er læsbare og troværdige |
| **5 — Testscripts** | Kendte svar (håndberegnede) verificeres | Alle tests består |

**Vigtig regel:** Afslut hver fase fuldt ud inden næste påbegyndes. Modstå fristelsen til at tilføje nye features midt i en fase.

---

## Teknisk stack

- Python 3.11+
- `dataclasses` til `Policy`
- `enum` til `PolicyState`
- `numpy` til numerik
- `pandas` til cashflow-tabeller (evt.)
- Ingen eksterne aktuarbiblioteker i v1.0 — alt implementeres from scratch

## Kodestil

- Dansk variabelnavngivning for domænespecifikke begreber (se terminologitabel)
- Engelsk for generel kode (funktionsstruktur, utilities, tests)
- Type hints på alle funktioner
- Docstrings på alle klasser og offentlige metoder — inkluder matematisk formel hvor relevant
- Én klasse / ét koncept per fil

---

## Vedligeholdelsesregel — Backlog-opgaver

Når en opgave fra `backlog.md` gennemføres, **skal** følgende altid opdateres:

1. **`DOKUMENTATION.md`** — afspejl ændringer i API, datastrukturer, matematisk model eller adfærd
2. **`examples/eksempel_police.py`** — opdater eksemplet så det demonstrerer ny/ændret funktionalitet

Dette gælder som det **sidste trin** i gennemførelsen af en backlog-opgave, inden opgaven markeres som færdig.
