# Milestone evaluation runs

Full per-run JSON behind the scoreboard's before/after story (`../progress.md`). Most runs are gitignored under
`scripts/runs/`; these milestones are kept here so the numbers are reproducible from the repository.

Each file holds `summary` (overall and per-group numbers, sameness/variety) and `rows` (every brief's outcome,
plan shape, design direction and the model's direction changes).

| File | Scoreboard run | What it shows |
|---|---|---|
| `run05_phase2_correct100.json` | Run 5 (0e8a97f, Phase 2) | Correctness baseline: 100% correct, 72 runs |
| `run06_group2_sameness83.json` | Run 6 (Group 2 variants) | First design-direction sameness measurement: 83% between different businesses (KI-29 found) |
| `run09_d239_sameness44.json` | Run 9 (D-239) | Design variety fix: sameness down to 44%, near the ~40% random floor |
