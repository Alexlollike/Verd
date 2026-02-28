# Roadmap: Verd — Aktuarbibliotek til Enkeltpolicefremregning

## Overview

Biblioteket bygges i fem faser, der følger den naturlige matematiske afhængighedskæde i aktuarfremregning: datamodel og antagelser (fase 1, færdig) muliggør cashflow-fremregning (fase 2), som muliggør reserveberegning via Thiele (fase 3), som muliggør validering og læsbart output (fase 4), som til sidst verificeres mod håndberegnede resultater (fase 5). Hver fase leverer en komplet og verificerbar kapabilitet.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data & Antagelser** - Datamodel, enums og biometriske/finansielle modeller (COMPLETE)
- [ ] **Phase 2: Cashflow-fremregning** - Sandsynlighedsvægtet fremregning der producerer cashflow-tidsserie
- [ ] **Phase 3: Reserveberegning** - Thiele-baseret diskontering af cashflows til reserve
- [ ] **Phase 4: Validering & Output** - Sanity checks og læsbart CSV/print output
- [ ] **Phase 5: Testscripts** - Verifikation mod kendte håndberegnede resultater

## Phase Details

### Phase 1: Data & Antagelser
**Goal**: Koden kan repræsentere enhver enkeltpolicy og alle antagelser der kræves til fremregning
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06
**Success Criteria** (what must be TRUE):
  1. En eksempelpolicy med alle felter (depot, alder, løn, indbetalingsprocent, pensionsalder, gruppe_id) kan oprettes og printes i kode
  2. PolicyState-enum med I_LIVE og DOED er tilgængelig og kan bruges til at markere en policys tilstand
  3. PolicyDistribution (liste af (Policy, sandsynlighed)-par) kan oprettes og holde en fordeling over tilstande
  4. GompertzMakeham kan beregne dødelighedsintensitet µ(x) for en given alder
  5. DeterministicMarket kan returnere afkastfaktor for et givet tidsstep
**Plans**: Complete

Plans:
- [x] 01-01: Policy-dataklasse og PolicyState-enum
- [x] 01-02: PolicyDistribution og unit-link regler
- [x] 01-03: BiometricModel (ABC) og GompertzMakeham
- [x] 01-04: FinancialMarket (ABC) og DeterministicMarket

### Phase 2: Cashflow-fremregning
**Goal**: Biblioteket kan fremregne en PolicyDistribution måned for måned og returnere en komplet cashflow-tidsserie
**Depends on**: Phase 1
**Requirements**: CASH-01, CASH-02, CASH-03, CASH-04, CASH-05
**Success Criteria** (what must be TRUE):
  1. Funktionen `fremregn()` accepterer en PolicyDistribution, BiometricModel og FinancialMarket og returnerer en tidsserie af cashflows
  2. Cashflows for hvert tidsstep afspejler korrekt rækkefølge: indbetalinger, derefter afkast, derefter biometrisk transition, derefter omkostninger
  3. Overlevelsessandsynlighed pr. tidsstep beregnes via p = exp(-mu * dt) med dt = 1/12
  4. PolicyDistribution opdateres korrekt over tid — sandsynligheder summerer til 1 i hele fremregningsperioden
  5. En cashflow-tabel for en eksempelpolicy kan printes med tidskolonne, indbetaling, udbetaling og depotudvikling
**Plans**: TBD

Plans:
- [ ] 02-01: Cashflow-fremregningsfunktion og tidsstep-logik
- [ ] 02-02: Sandsynlighedsvægtet PolicyDistribution-opdatering
- [ ] 02-03: Cashflow-tabelprint for eksempelpolicy

### Phase 3: Reserveberegning
**Goal**: Biblioteket kan beregne et korrekt reservetal for en eksempelpolicy via Thieles differentialligning
**Depends on**: Phase 2
**Requirements**: RESV-01, RESV-02, RESV-03
**Success Criteria** (what must be TRUE):
  1. Cashflows diskonteres til nutidsværdi via Thieles differentialligning med det deterministiske finansielle marked
  2. Et enkelt reservetal (kr.) kan beregnes og udskrives for en eksempelpolicy
  3. Reserven er konsistent med det deterministiske finansielle marked — diskonteringsfaktoren bruger samme afkastrate som DeterministicMarket
**Plans**: TBD

Plans:
- [ ] 03-01: Thiele-diskonteringslogik
- [ ] 03-02: Reserve-beregning og output for eksempelpolicy

### Phase 4: Validering & Output
**Goal**: Resultaterne er troværdige og læsbare — en aktuar kan inspekcere og stole på dem
**Depends on**: Phase 3
**Requirements**: VALD-01, VALD-02, VALD-03
**Success Criteria** (what must be TRUE):
  1. Sanity checks fanger matematisk inkonsistens — f.eks. at sandsynligheder ikke summerer til 1, eller at depoter er negative
  2. Cashflow-tabel og reserve kan eksporteres til CSV med korrekte kolonnenavne
  3. Printet output (tabel og reservetal) er læsbart og forståeligt for en aktuar uden yderligere forklaring
**Plans**: TBD

Plans:
- [ ] 04-01: Sanity checks og fejlhåndtering
- [ ] 04-02: CSV-eksport og læsbart print-output

### Phase 5: Testscripts
**Goal**: Alle beregninger er verificeret korrekte mod kendte håndberegnede resultater
**Depends on**: Phase 4
**Requirements**: TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
  1. Testscripts sammenligner cashflows mod håndberegnede resultater og fejler med tydelig besked ved afvigelse
  2. Testscripts sammenligner reserveberegning mod håndberegnede resultater og fejler med tydelig besked ved afvigelse
  3. Alle tests kører grønt uden ændringer i kodebasen
**Plans**: TBD

Plans:
- [ ] 05-01: Cashflow-testscripts mod håndberegnede resultater
- [ ] 05-02: Reserve-testscripts mod håndberegnede resultater

## Progress

**Execution Order:**
Phases execute in numeric order: 1 (complete) → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data & Antagelser | 4/4 | Complete | 2026-02-28 |
| 2. Cashflow-fremregning | 0/3 | Not started | - |
| 3. Reserveberegning | 0/2 | Not started | - |
| 4. Validering & Output | 0/2 | Not started | - |
| 5. Testscripts | 0/2 | Not started | - |
