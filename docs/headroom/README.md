# Headroom research and design docs

The research, design proposals, critiques and PRD produced on 25–26 Sep 2026, before the team's on-site conversations with Base employees. They are supporting material for the project documents, not a competing spec.

| Path | What it is |
|---|---|
| `../reconciliation.md` | Where Hugging Base, this PRD and GridSpine Atlas disagree, and what we chose for each. Read this first. |
| `CONTEXT.md` | The brief every design agent read: event rules, the 100-point rubric, what the team agreed in the room, what a Base engineer told us. |
| `PRD.md` | Headroom PRD v1, merged from five design proposals and two critiques. §7 defines every interface. Published page: https://claude.ai/artifact/1PKt63sT1Jn8NGStMxfv4p |
| `design/round1/` | The five proposals (world-sim, orchestrator, adversary-and-observability, data-ingest, ui-scenario-studio) and two critiques (critique-judge, critique-integration). |
| `research_notes/` | The five source-note files behind the research report, with every citation. |
| `headroom-gridspine-dossier.html` | GridSpine Atlas v0.2: the stretch transmission layer and the CIM vocabulary. A design only, never built (moved here from the repo root on 27 Sep 2026). |
| `../research-report.md` | The research report. The PRD cites it as `reports/Base Power system and ERCOT data.md`. Research brief page: https://claude.ai/artifact/BRaMSHHnktx9U48JvFGnaX |

## Corrections applied on 26 Sep 2026

The judge critique found two errors in the research report, now fixed in `docs/research-report.md`:

- **Transformers:** SMART-DS `kva=` values are already standard 25/50/75 kVA nameplates. The 27.5 and 37.5 figures are the 110% normal and 150% emergency ratings. Do not de-rate.
- **Frequency:** a 1,000-battery hijack moves ERCOT frequency by a 3–17 mHz band (normal wander σ ≈ 13.7 mHz on 25 Sep 2026), not 3–5 mHz.

## Not in the repo

The PRD and critiques cite `evidence/` paths: the raw ERCOT, SMART-DS, weather and Base downloads (about 209 MB) and the analysis scripts behind the Track 1 findings. They live on RZ's machine and can be pushed as small extracts when needed.
