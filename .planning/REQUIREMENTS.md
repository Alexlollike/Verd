# Requirements: Verd — Aktuarbibliotek til Enkeltpolicefremregning

**Defined:** 2026-02-28
**Core Value:** Et korrekt og gennemsigtigt beregningskernel, der kan fremregne reserver og cashflows for én police — med fuld matematisk sporbarhed fra Thiele til output.

## v1 Requirements

Requirements for v1.0. Fase 1 er allerede leveret og kravene her er markeret som validerede.

### Datamodel & Antagelser (Fase 1 — leveret)

- [x] **DATA-01**: Koden kan repræsentere en enkeltpolicy med alle relevante felter (depot, alder, løn, indbetalingsprocent, pensionsalder, gruppe_id, m.m.)
- [x] **DATA-02**: PolicyState-enum med I_LIVE og DOED tilstande er implementeret
- [x] **DATA-03**: PolicyDistribution (liste af (Policy, sandsynlighed)-par) er implementeret
- [x] **DATA-04**: BiometricModel (ABC) med GompertzMakeham (µ(x) = alpha + beta * exp(sigma * x)) er implementeret
- [x] **DATA-05**: FinancialMarket (ABC) med DeterministicMarket (fast årlig afkastrate) er implementeret
- [x] **DATA-06**: En eksempelpolicy kan beskrives i kode og printes

### Cashflow-fremregning (Fase 2)

- [ ] **CASH-01**: En funktion accepterer PolicyDistribution + BiometricModel + FinancialMarket og returnerer en tidsserie af cashflows
- [ ] **CASH-02**: Cashflows beregnes med korrekt rækkefølge inden for hvert tidsstep: indbetalinger → afkast → biometri → omkostninger
- [ ] **CASH-03**: Overlevelsessandsynlighed beregnes korrekt via p = exp(-µ * dt) med dt = 1/12
- [ ] **CASH-04**: Sandsynlighedsvægtet fremregning opdaterer PolicyDistribution korrekt over tid
- [ ] **CASH-05**: Cashflow-tabellen kan printes for en eksempelpolicy

### Reserveberegning (Fase 3)

- [ ] **RESV-01**: Cashflows diskonteres til nutidsværdi (reserve) ved hjælp af Thieles differentialligning
- [ ] **RESV-02**: Et enkelt reservetal kan beregnes for en eksempelpolicy
- [ ] **RESV-03**: Reserve beregnes konsistent med det deterministiske finansielle marked

### Validering & Output (Fase 4)

- [ ] **VALD-01**: Sanity checks verificerer matematisk konsistens (f.eks. at sandsynligheder summer til 1, at depoter er ikke-negative)
- [ ] **VALD-02**: Resultater kan eksporteres til CSV
- [ ] **VALD-03**: Cashflow-tabel og reserve er læsbare og troværdige for en aktuar

### Testscripts (Fase 5)

- [ ] **TEST-01**: Testscripts verificerer cashflows mod kendte (håndberegnede) resultater
- [ ] **TEST-02**: Testscripts verificerer reserveberegning mod kendte resultater
- [ ] **TEST-03**: Alle tests består

## v2 Requirements

Deferred til fremtidige versioner.

### Udvidede policetilstande

- **V2-01**: Invalid-tilstand (arbeidsufør)
- **V2-02**: Fripolice-tilstand
- **V2-03**: Genkøbt-tilstand

### Udvidede modeller

- **V2-04**: Stokastiske finansielle scenarier
- **V2-05**: Yderligere dødelighedsmodeller
- **V2-06**: Porteføljeaggregering (fremregning af mange polices)

## Out of Scope

Eksplicit ekskluderet fra v1.0. Dokumenteret for at undgå scope creep.

| Feature | Årsag |
|---------|-------|
| Porteføljeaggregering | Kun enkeltpolicy i v1.0 — arkitektur optimeret herfor |
| Invalid/fripolice/genkøbt tilstande | Udvider Markov-rum — gemmes til v2 |
| Stokastiske scenarier | Deterministisk marked kun — simulering er anderledes paradigme |
| UI og rapportgenerator | Bibliotek, ikke applikation |
| Externe aktuarbiblioteker | Alt implementeres from scratch i v1.0 |
| Simulering (Monte Carlo) | Sandsynlighedsvægtet fremregning kun |

## Traceability

Hvilke faser dækker hvilke krav. Opdateres under roadmap-oprettelse.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| DATA-04 | Phase 1 | Complete |
| DATA-05 | Phase 1 | Complete |
| DATA-06 | Phase 1 | Complete |
| CASH-01 | Phase 2 | Pending |
| CASH-02 | Phase 2 | Pending |
| CASH-03 | Phase 2 | Pending |
| CASH-04 | Phase 2 | Pending |
| CASH-05 | Phase 2 | Pending |
| RESV-01 | Phase 3 | Pending |
| RESV-02 | Phase 3 | Pending |
| RESV-03 | Phase 3 | Pending |
| VALD-01 | Phase 4 | Pending |
| VALD-02 | Phase 4 | Pending |
| VALD-03 | Phase 4 | Pending |
| TEST-01 | Phase 5 | Pending |
| TEST-02 | Phase 5 | Pending |
| TEST-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 after initial definition*
