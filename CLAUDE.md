# CLAUDE.md — Universal Redesign Algorithm

## Project Overview

Universal-Redesign-Algorithm is a **bio-inspired framework for redesigning complex systems** — energy grids, supply chains, cities, organizations — using biological principles, fractal geometry, swarm intelligence, and evidence-based engineering. It produces schema-validated, simulation-ready redesign plans through a 7-phase iterative cycle.

This repo acts as the **orchestrator/hub** of a modular ecosystem, pulling shape definitions, sensor data, defense protocols, and audit frameworks from sibling repositories via `.fieldlink.json`.

## Ecosystem Role

```
BioGrid2.0 Atlas → Rosetta Shape Core → Polyhedral Intelligence
                                      → Geometric→Binary Bridge
                         ↓
              Universal Redesign Algorithm  ← orchestrator
                    ↓         ↓         ↓
           Emotions-as-Sensors  Defense  Audit
```

### Key Sibling Repos
- **Rosetta-Shape-Core** — canonical shape ontology, bridges, seed catalog (dot-notation IDs)
- **Polyhedral-Intelligence** — families, principles, atlas entries
- **Emotions-as-Sensors** — emotion sensors as diagnostic signals
- **Symbolic-Defense-Protocol** — defense against coercive alignment
- **ai-human-audit-protocol** — ethics, consent, transparency
- **BioGrid2.0** — upstream atlas & DNA registry

## Directory Structure

```
schema/              — JSON Schema definitions (redesign plan validation)
plans/               — Example redesign plans (schema-validated JSON)
docs/                — Framework documentation, case studies, principles
  architecture-overview.md
  bio-grid-framework.md
  bio-hybrid-equations.md
  biological-principles.md
  energy-architecture.md
  natures-operating-system-executive-summary.md
  stress-points.md
  use-cases.md
  case-microgrids.md
  case-supplychain.md
  case-wastewater.md
  case-agri-logistics.md
scripts/             — Validation utilities (validate.sh)
logs/                — Fieldlink lock files
atlas/remote/        — Staged cross-repo data (fieldlink mounts)
```

## Common Commands

```bash
# Validate plans against schema (requires jq; ajv optional)
./scripts/validate.sh
```

## Key Conventions

### ID Naming (dot-notation, aligned with Rosetta-Shape-Core)
- **Shapes:** `SHAPE.ICOSA`, `SHAPE.DODECA`, `SHAPE.TETRA`, `SHAPE.CUBE`, `SHAPE.OCTA`
- **Sensors:** `EMOTION.FEAR`, `EMOTION.ADMIRATION`, `EMOTION.LONGING`
- **Defenses:** `DEFENSE.URGENCY_GUARD`, `DEFENSE.CONSENSUS_GUARD`
- **Audits:** `AUDIT.PARTNERSHIP_ETHICS_V1`
- **Plans:** `URD.energy_grid_v1`

### Namespace Reference
All namespaces defined in Rosetta-Shape-Core's `ontology/_vocab.json`:
ANIMAL, PLANT, MICROBE, CRYSTAL, GEOM, STRUCT, FIELD, CONST, TEMP, PROTO, CAP, SHAPE, EMOTION, DEFENSE, REGEN

### File Naming
- **Documentation:** lowercase kebab-case (`bio-hybrid-equations.md`, `case-microgrids.md`)
- **JSON data:** kebab-case or snake_case (`energy_grid.example.json`)
- **Schemas:** descriptive with `.schema.json` suffix
- **No spaces in filenames**

### Schema
- All schemas use JSON Schema 2020-12
- Shape IDs match pattern: `^SHAPE\.[A-Z0-9_]+$`
- Sensor IDs match pattern: `^EMOTION\.[A-Z0-9_]+$`
- Defense IDs match pattern: `^DEFENSE\.[A-Z0-9_]+$`

### 7-Phase Redesign Algorithm
1. `bio-analysis` — Extract natural analogs
2. `fractal-optimization` — Golden ratio scaling, self-similar subsystems
3. `scientific-proof` — Modeling, simulation, testing
4. `opposition-mapping` — Political, financial, technical pushback
5. `evidence-rebuttals` — 3+ counter-arguments per objection
6. `risk-mitigation` — Operational, technical, financial safeguards
7. `implementation-roadmap` — Pilot, phased rollout, metrics

## Fieldlink Integration

`.fieldlink.json` orchestrates cross-repo data loading:
- **Merge strategy:** deep-merge in defined order
- **Consent:** all sources include license + share_ok
- **Integrity:** SHA-256 hashing, no missing files allowed
- **Offline:** cached locally in `.fieldcache/`
- **Redaction:** `**/private/**` and `*.secrets.json` excluded

## Architecture Notes

- **Data-first:** JSON schemas define contracts; plans are structured JSON
- **Offline-capable:** all core functionality works without network
- **Consent-first:** every cross-repo link includes licensing
- **Guardrails enforced:** no coercion from fear signals, no idolization, summary-only logging

## Do Not

- Use colon-notation for IDs (use dots: `SHAPE.X` not `SHAPE:X`)
- Break JSON Schema 2020-12 compatibility
- Add files with spaces in names
- Commit secrets or private data
- Remove guardrails from plans
