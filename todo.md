# TODO — Verd Aktuarbibliotek

Arbejdsliste for v1.0. Afslut hver fase fuldt ud inden næste påbegyndes.
Brug `[x]` når en opgave er færdig.

---

## Fase 1 — Data & Antagelser ✓

- [x] `PolicyState` enum (`I_LIVE`, `DOED`)
- [x] `Policy` dataclass — depoter i **enheder** (unit-link)
- [x] `Policy.depotvaerdi_dkk(enhedspris)` — beregnet, ikke gemt felt
- [x] `Policy.total_enheder()` — sum af alle tre depoter
- [x] `PolicyDistribution` typealias + `initial_distribution()`
- [x] `BiometricModel` ABC — `mortality_intensity()`, `survival_probability()`, `death_probability()`
- [x] `GompertzMakeham` — µ(x) = alpha + beta·exp(sigma·x)
- [x] `FinancialMarket` ABC — `enhedspris(t)`, `dkk_til_enheder()`, `enheder_til_dkk()`
- [x] `DeterministicMarket` — enhedspris(t) = P₀·exp(r·t)
- [x] `examples/eksempel_police.py` — done-kriterium opfyldt
- [x] `pyproject.toml`, `.gitignore`

---

## Fase 1b — Test-infrastruktur og referenceberegninger

### Opsætning
- [ ] Tilføj `pytest` til `pyproject.toml` under `[project.optional-dependencies] dev`
- [ ] Opret `tests/` mappe med `tests/__init__.py`
- [ ] Opret `tests/conftest.py` med delte fixtures:
  - `standard_biometri` — `GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)`
  - `standard_marked` — `DeterministicMarket(r=0.05, enhedspris_0=100.0)`
  - `standard_police` — se referenceberegninger nedenfor

### Referenceberegninger (håndberegnede facit)

Parametre for alle tests: `alpha=0.0005`, `beta=0.00004`, `sigma=0.09`, `r=0.05`, `P₀=100.0`

| Beregning | Formel | Facit |
|---|---|---|
| µ(40) | 0.0005 + 0.00004·exp(0.09·40) | **0.00196393 år⁻¹** |
| µ(50) | 0.0005 + 0.00004·exp(0.09·50) | **0.00410068 år⁻¹** |
| µ(60) | 0.0005 + 0.00004·exp(0.09·60) | **0.00935625 år⁻¹** |
| p(40, 1/12) | exp(−0.00196393/12) | **0.99983637** |
| q(40, 1/12) | 1 − p | **0.00016363** |
| enhedspris(1) | 100·exp(0.05) | **105.12710964 DKK/enh.** |
| depotværdi | 2500 enh. × 100 DKK/enh. | **250.000,00 DKK** |
| DKK→enh. | 10.000 DKK / 100 DKK/enh. | **100,0000 enh.** |
| Månedlig præmie | 600.000 × 0,15 / 12 | **7.500,00 DKK/md.** |
| Præmie i enh. (t=0) | 7.500 / 100 | **75,0000 enh./md.** |

- [ ] Opret `docs/referenceberegninger.md` med ovenstående tabel og mellemregninger

### Unit tests — Fase 1 klasser

- [ ] `tests/test_policy_state.py`
  - [ ] `PolicyState` har præcis `I_LIVE` og `DOED`
  - [ ] Enum-værdier er strings (`"I_LIVE"`, `"DOED"`)

- [ ] `tests/test_policy.py`
  - [ ] `total_enheder()` returnerer sum af de tre depoter
  - [ ] `depotvaerdi_dkk(100.0)` = `total_enheder()` × 100
  - [ ] `depotvaerdi_dkk` er ikke et gemt felt (verificer med `dataclasses.fields()`)
  - [ ] `tilstand` defaulter til `PolicyState.I_LIVE`
  - [ ] `depotvaerdi_dkk(0.0)` = 0.0 (zero-enhedspris edge case)

- [ ] `tests/test_policy_distribution.py`
  - [ ] `initial_distribution(police)` returnerer liste med præcis ét element
  - [ ] Sandsynlighed i initial distribution = 1.0
  - [ ] Sandsynligheder summer til 1.0

- [ ] `tests/test_gompertz_makeham.py`
  - [ ] `mortality_intensity(40)` matcher facit 0.00196393 (tolerance 1e-8)
  - [ ] `mortality_intensity(50)` matcher facit 0.00410068 (tolerance 1e-8)
  - [ ] `mortality_intensity(60)` matcher facit 0.00935625 (tolerance 1e-8)
  - [ ] `mortality_intensity(x) >= 0` for x ∈ {0, 20, 40, 60, 80, 100}
  - [ ] `mortality_intensity` er monotont stigende (intensitet ved 50 > intensitet ved 40)
  - [ ] `survival_probability(40, 1/12)` matcher facit 0.99983637 (tolerance 1e-8)
  - [ ] `death_probability(40, 1/12)` matcher facit 0.00016363 (tolerance 1e-8)
  - [ ] `survival_probability + death_probability = 1.0` præcist

- [ ] `tests/test_deterministic_market.py`
  - [ ] `enhedspris(0)` = `enhedspris_0` (100.0)
  - [ ] `enhedspris(1)` matcher facit 105.12710964 (tolerance 1e-6)
  - [ ] `enhedspris(t) > enhedspris(0)` for t > 0 og r > 0
  - [ ] Round-trip: `dkk_til_enheder(X, t) × enhedspris(t)` = X (tolerance 1e-10)
  - [ ] Round-trip: `enheder_til_dkk(dkk_til_enheder(X, t), t)` = X (tolerance 1e-10)
  - [ ] `dkk_til_enheder(10000, 0)` = 100.0 (matcher facit)

---

## Fase 2 — Cashflow-fremregning

### Datastruktur
- [ ] Opret `verd/cashflow.py` med `CashflowRaekke` dataklasse:
  - `t: float` — tidspunkt (år fra tegningsdato)
  - `alder: float` — forsikringstagers alder på tidspunkt t
  - `p_alive: float` — sandsynlighed for at være i live
  - `enhedspris: float` — fondens kurs på tidspunkt t
  - `indbetaling_dkk: float` — bruttopræmie (0 i udbetalingsfase)
  - `indbetaling_enheder: float` — præmie omregnet til enheder
  - `udbetaling_dkk: float` — ydelse udbetalt (0 i opsparingsfase)
  - `udbetaling_enheder: float` — ydelse omregnet til enheder
  - `risikopraemie_enheder: float` — biometrisk risikopræmie trukket fra depot
  - `depot_enheder_efter: float` — samlet depotenhed efter dette trin

### Præmieberegning (opsparingsfase)
- [ ] Implementer `beregn_maanedlig_praemie_dkk(police)` → `loen × indbetalingsprocent / 12`
- [ ] Implementer `praemie_til_enheder(praemie_dkk, marked, t)` → `dkk_til_enheder(praemie_dkk, t)`

### Risikopræmie
- [ ] Definer hvad der sker ved død: depot udbetales til begunstiget (sum at risk = depotværdi)
- [ ] Implementer `beregn_risikopraemie_enheder(police, biometri, alder, dt)`:
  - `q = death_probability(alder, dt)`
  - Risikopræmien er den forventede omkostning ved dødsfald i perioden: `depot_enheder × q`
  - (Simpel model: ingen overkrydsende dækning i v1.0)

### Ét tidsstep
- [ ] Implementer `fremregn_et_trin(police, p_alive, biometri, marked, t, dt)` → `CashflowRaekke`:
  - Rækkefølge: **indbetaling → afkast (via enhedspris) → biometri → omkostninger**
  - Beregn alder på tidspunkt t
  - Tilskriv indbetaling i enheder (hvis opsparingsfase)
  - Afkast afspejles automatisk via `enhedspris(t+dt)` (enheder ændres ikke)
  - Træk risikopræmie i enheder fra depot
  - Opdater `p_alive` med overlevelsessandsynlighed

### Fuld fremregning
- [ ] Implementer `fremregn(police, biometri, marked, dt=1/12, max_alder=110)` → `list[CashflowRaekke]`
- [ ] Stopkriterium: `p_alive < 1e-6` eller alder ≥ `max_alder`
- [ ] Håndter overgang til udbetalingsfase når `er_under_udbetaling = True`
- [ ] Implementer aldersopsparing-udbetaling: engangsudbetaling ved første trin i udbetalingsfase
- [ ] Implementer ratepension-udbetaling: månedlig udbetaling = depot / (resterende måneder), over `ratepensionsvarighed` år
- [ ] Implementer livrente-udbetaling: beregn månedlig ydelse fra livrentedepot (aktuariel annuitet — simpel version: `depot / forventet_restlevetid`)

### Output
- [ ] Implementer `til_dataframe(cashflows)` → `pandas.DataFrame` med formaterede kolonner
- [ ] Implementer `print_cashflow_tabel(cashflows, marked)` — printer de første/sidste rækker med totaler
- [ ] Opdater `examples/eksempel_police.py` med cashflow-tabel-udskrift (done-kriterium fase 2)

### Tests — Fase 2
- [ ] `tests/test_cashflow.py`
  - [ ] Månedlig præmie = 600.000 × 0,15 / 12 = 7.500,00 DKK (matcher facit)
  - [ ] Præmie i enheder (t=0, P₀=100) = 75,0 enh. (matcher facit)
  - [ ] `p_alive` starter på 1.0 og er strengt aftagende
  - [ ] `p_alive` er altid ∈ [0, 1]
  - [ ] Sandsynlighedsvægtede cashflows ≤ uvægtede cashflows
  - [ ] Cashflow-liste er ikke tom
  - [ ] Første CashflowRaekke: `t ≈ 0`, `p_alive = 1.0`
  - [ ] Verificer første 3 måneders `indbetaling_enheder` mod håndberegnet facit
  - [ ] Ved opsparingsfase: `udbetaling_dkk = 0` på alle rækker

---

## Fase 3 — Reserveberegning

### Thiele — baglæns rekursion
- [ ] Opret `verd/reserve.py`
- [ ] Implementer `thiele_trin(V_naeste, cashflow, enhedspris_t, enhedspris_naeste)` — ét baglæns trin:
  - `V(t) = [V(t+dt) - indbetaling_enheder + udbetaling_enheder + risikopraemie_enheder] × (enhedspris_naeste / enhedspris_t)⁻¹`
  - (Diskontering sker via forholdet mellem enhedspriser)
- [ ] Implementer `beregn_reserve(cashflows, marked)` → `list[float]`:
  - Baglæns iteration over cashflow-listen
  - Terminalvilkår: `V(T) = depot_enheder_efter × enhedspris(T)` (depotværdi ved ophør)
- [ ] Verificer terminalvilkår: reserve ved ophør = resterende depotværdi i DKK

### Diskontering
- [ ] Implementer `diskonteringsfaktor(marked, t, dt)` = `enhedspris(t) / enhedspris(t + dt)`
- [ ] Verificer: `V(0)` ≈ `depotvaerdi_dkk(enhedspris(0))` for police uden risikopræmie og ingen cashflows (nulpolicen)

### Output
- [ ] Implementer `reserve_tabel(cashflows, reserver, marked)` → `pandas.DataFrame` (t, alder, p_alive, reserve_dkk)
- [ ] Implementer `print_reserve_tabel(...)` — printer tidsserie af reserve
- [ ] Opdater `examples/eksempel_police.py` med reservetal (done-kriterium fase 3)

### Tests — Fase 3
- [ ] `tests/test_reserve.py`
  - [ ] Terminalreserve = depotværdi ved terminalvilkår (tolerance 1e-6)
  - [ ] `V(0) ≥ 0` — reserve er ikke-negativ
  - [ ] Reserve er aftagende over tid for nulindbetalingspolicen (ren opsparing)
  - [ ] **Nulcashflow-test**: police med `indbetalingsprocent=0`, ingen ydelser, ingen risikopræmie → `V(0)` = `depotvaerdi_dkk(enhedspris(0))` (tolerance 1e-4)
  - [ ] Verificer `V(0)` for simpel 3-måneders police mod håndberegnet facit

---

## Fase 4 — Validering & Output

### Sanity checks
- [ ] Opret `verd/validering.py`
- [ ] Implementer `check_sandsynligheder(fordeling)` — summer til 1.0 (tolerance 1e-9)
- [ ] Implementer `check_p_alive_monoton(cashflows)` — `p_alive` er aftagende
- [ ] Implementer `check_reserve_ikke_negativ(reserver)` — alle reserver ≥ 0
- [ ] Implementer `check_reserve_mod_depot(V0, police, marked)` — V(0) ≈ depotværdi (tolerance-baseret)
- [ ] Implementer `kør_alle_checks(police, cashflows, reserver, marked)` — kalder alle checks, kaster `ValueError` ved fejl

### CSV-eksport
- [ ] Implementer `eksporter_cashflows_csv(cashflows, marked, filsti)` — skriver cashflow DataFrame til CSV
- [ ] Implementer `eksporter_reserve_csv(cashflows, reserver, marked, filsti)` — skriver reserve DataFrame til CSV

### Formateret output
- [ ] Implementer `print_policeoversigt(police, cashflows, reserver, marked)` — samlet rapport til stdout:
  - Policestamdata
  - Nøgletal (depotværdi, V(0), sum af indbetalinger, sum af ydelser)
  - Første og sidste 5 rækker af cashflow- og reservetabel
- [ ] Opdater `examples/eksempel_police.py` til komplet end-to-end eksempel (done-kriterium fase 4)

### Tests — Fase 4
- [ ] `tests/test_validering.py`
  - [ ] `check_sandsynligheder` kaster `ValueError` hvis sum ≠ 1.0
  - [ ] `check_reserve_ikke_negativ` kaster `ValueError` ved negativ reserve
  - [ ] `check_p_alive_monoton` kaster `ValueError` ved stigende p_alive
  - [ ] CSV-eksport producerer velformet fil med korrekte kolonnenavne
  - [ ] End-to-end: `standard_police` → cashflows → reserver → alle checks → ingen undtagelser

---

## Fase 5 — Testscripts med kendte svar

### Håndberegnet faciteksempel
- [ ] Opret `docs/facit_eksempel.md` — komplet håndberegnet eksempel:
  - 3-årig ren aldersopsparing (ingen ratepension, ingen livrente)
  - Starttilstand: 1.000 enh. × 100 DKK/enh. = 100.000 DKK
  - Parametre: r=0.05, alpha=0.0005, beta=0.00004, sigma=0.09, alder=40, dt=1/12
  - Beregn eksplicit: måned 1 indbetaling, risikopræmie, ny enhedspris, ny depotværdi
  - Beregn reserve ved t=0 baglæns fra terminalvilkår
  - Alle mellemresultater til 8 decimaler

- [ ] `tests/test_facit.py` — verificer alle nøgletal fra `facit_eksempel.md`:
  - [ ] µ(40) = 0.00196393 (tolerance 1e-8)
  - [ ] µ(50) = 0.00410068 (tolerance 1e-8)
  - [ ] µ(60) = 0.00935625 (tolerance 1e-8)
  - [ ] p(40, 1/12) = 0.99983637 (tolerance 1e-8)
  - [ ] enhedspris(1) = 105.12710964 (tolerance 1e-6)
  - [ ] Månedlig præmie for standardpolicen = 7.500,00 DKK (eksakt)
  - [ ] `V(0)` for nulcashflow-policen = `depotvaerdi_dkk` (tolerance 1e-4)
  - [ ] Første måneds `indbetaling_enheder` = håndberegnet facit (tolerance 1e-8)
  - [ ] Første måneds `risikopraemie_enheder` = håndberegnet facit (tolerance 1e-8)

### Edge cases
- [ ] Test: police med alle depoter = 0.0 → `depotvaerdi_dkk` = 0.0, reserve = 0.0
- [ ] Test: police med `er_under_udbetaling = True` fra starten → ingen indbetalinger
- [ ] Test: `ratepensionsvarighed = 0` → ingen ratepensionsydelser
- [ ] Test: meget høj dødelighedsintensitet (alpha=1.0) → `p_alive` falder hurtigt, fremregning stopper tidligt
- [ ] Test: `r = 0.0` → `enhedspris(t) = enhedspris_0` for alle t (flad kurve)

### Regression
- [ ] Kør samtlige tests med `pytest -v` og verificer at **alle tests består**
- [ ] Kør `examples/eksempel_police.py` og verificer output mod forventet format

### Valgfrit CI
- [ ] Opret `.github/workflows/test.yml` der kører `pytest` på push til `main`
