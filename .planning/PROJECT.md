# Verd — Aktuarbibliotek til Enkeltpolicefremregning

## What This Is

Python-bibliotek til sandsynlighedsvægtet fremregning af enkeltpolice reserver og cashflows. Målrettet rene markedsrenteprodukter uden garantier (aldersopsparing, ratepension, livrente). Policen modelleres som en flerdimensionel Markov-proces i diskret tid med månedlige tidsskridt.

## Core Value

Et korrekt og gennemsigtigt beregningskernel, der kan fremregne reserver og cashflows for én police — med fuld matematisk sporbarhed fra Thiele til output.

## Requirements

### Validated

- ✓ `Policy`-dataklasse med alle felter (depot, alder, løn, indbetalingsprocent m.m.) — Phase 1
- ✓ `PolicyState`-enum (I_LIVE, DOED) — Phase 1
- ✓ `PolicyDistribution` (list of (Policy, sandsynlighed)-par) — Phase 1
- ✓ `BiometricModel` (ABC) + `GompertzMakeham` implementering — Phase 1
- ✓ `FinancialMarket` (ABC) + `DeterministicMarket` implementering — Phase 1
- ✓ Eksempelpolicy kan beskrives i kode og printes — Phase 1

### Active

- [ ] Cashflow-fremregning: funktion der returnerer tidsserie af cashflows for PolicyDistribution
- [ ] Reserveberegning: diskontering af cashflows til reserve (Thiele-baseret)
- [ ] Sanity checks og læsbart output (CSV/print)
- [ ] Testscripts der verificerer mod kendte (håndberegnede) resultater

### Out of Scope

- Porteføljeaggregering — kun enkeltpolicy i v1.0
- Policetilstande: invalid, fripolice, genkøbt — gemmes til backlog
- Stokastiske scenarier og simulering — deterministisk marked kun i v1.0
- UI og rapportgenerator — bibliotek, ikke applikation
- Eksterne aktuarbiblioteker — alt implementeres from scratch

## Context

Projektet bygger på klassisk aktuarmatematik (Thieles differentialligning, Markov-kæder). Implementationen er i diskret tid (månedlige skridt, dt=1/12) selvom den underliggende matematik er kontinuert. Produktfokus er rene markedsrenteprodukter (unit-link) uden garantier.

Fase 1 er afsluttet og committet til main. Kode ligger i `verd/`-pakken med én fil per klasse/koncept.

**Teknisk stack:** Python 3.11+, dataclasses, enum, numpy, pandas (til tabeller).

**Kodestil:** Dansk variabelnavngivning for domænebegreber, engelsk for generel kode. Type hints og docstrings (med matematiske formler) på alle klasser og offentlige metoder.

## Constraints

- **Scope**: Kun enkeltpolicy — ingen porteføljemekanik i v1.0
- **Matematik**: Kun Gompertz-Makeham dødelighedsmodel i v1.0
- **Marked**: Kun deterministisk (fast afkastrate) i v1.0
- **Tidsenhed**: Diskret tid, dt = 1/12 (månedlige skridt) — fastlagt
- **Dependencies**: Ingen eksterne aktuarbiblioteker

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Diskret tid (dt=1/12) | Passer til policeadministrationssystemets granularitet | — Pending |
| `er_under_udbetaling` som eksplicit felt | Forsikringstager kan udskyde pension — styres ikke automatisk | — Pending |
| `depotværdi` beregnet, ikke gemt | Undgår inkonsistens — altid sum af tre depoter | — Pending |
| `BiometricModel` og `FinancialMarket` uafhængige | Kobles kun i fremregningslaget | — Pending |
| Én klasse per fil | Giver klar arkitektur og nem navigation | ✓ God |

---
*Last updated: 2026-02-28 after initialization*
