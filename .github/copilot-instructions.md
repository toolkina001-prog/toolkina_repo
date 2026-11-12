# Copilot instructions for this repository

This repository contains a Python implementation scaffold for the Windows desktop bottle-pouring puzzle game described in `README.md`. Treat the README as the source of truth for gameplay rules, level-generation requirements, and acceptance criteria.

## Build, test, and lint commands

- Run the desktop UI: `python main.py`
- Run the console prototype: `python main.py --console`
- Run all tests: `python -m unittest discover -s tests -v`
- Run one test module: `python -m unittest discover -s tests -p test_game.py -v`
- Export a campaign pack: `python scripts/export_campaign.py --levels 120 --out campaign/levels.json`
- There is no separate linter or packaging configuration checked in yet.

## High-level architecture

The project is organized around the following layers, which are reflected in the README and should remain distinct in implementation:

- Core game rules engine
  - The rules layer should be pure and UI-independent.
  - Keep logic for bottle state, valid pours, applying a move, and solved-state detection in a dedicated module.
  - Example responsibilities from the spec: `canPour(state, from, to)`, `applyPour`, `isSolved`.

- Solver / validation
  - An A* solver with canonicalized states is used for generating and validating levels.
  - This is not just a UI helper; it is part of content correctness.
  - Solver checks should be used both for generation and for validating campaign content at build time.

- Level generation
  - Levels are built by reverse-shuffling solved boards; each level stores a forward solution witness that `verify_campaign` replays.
  - The generator should produce only valid, solvable states and reject trivial/unsolved outputs.
  - Campaign progression should follow the described complexity curve rather than making levels artificially harder by creating unsolvable states.

- Content / campaign data
  - The game is expected to ship with a campaign of 100+ levels.
  - Level packs should be generated offline, verified, and stored as JSON or another data artifact. The export entry point is `scripts/export_campaign.py`.
  - Each level should have a clear progression path and a corresponding tutorial/feature gate for new mechanics.

- User interface and game flow
  - The UI is a desktop puzzle game with menu, level selection, settings, save/progress, and in-level controls.
  - The gameplay screen should remain thin and delegate game-state logic to the core engine.
  - Features like undo, restart, hinting, and save/load are interaction concerns, not rule-engine concerns.

- Persistence and progression
  - Progress should be saved automatically, including completed levels and current level state.
  - The project expects a clean separation between game logic and persisted UI state.

The current Python package is split into `engine.py` (pure move rules), `solver.py` (search), `generator.py` (solvable board generation), `campaign.py` (campaign data and JSON), `mechanics.py` (mechanic metadata), and `gui.py` (Tkinter UI). `main.py` selects the GUI or console entry point.

## Key conventions

- Rule logic must stay separate from rendering and input handling.
  - Any function that decides whether a move is legal or computes a result should be deterministic and testable without the UI.

- Levels must be generated and validated as solvable.
  - Do not rely on “looks right” or hand-authored states without a solver pass.
  - The README explicitly rejects generating unsolvable random configurations just to increase difficulty.

- Difficulty should grow through solvable complexity, not through broken boards.
  - The intended progression is geometric growth in color count and mechanics, with tutorial gates for each mechanic.

- Additional mechanics should be introduced one at a time.
  - The README calls out stone layers, larger bottle capacities, frozen layers, decoy bottles, and hidden layers as separate mechanics that need tutorial coverage and solver validation.

- Symmetry and canonicalization matter for the solver.
  - If implementing solver state hashing or BFS/A* search, normalize bottle ordering to avoid duplicate equivalent states.

- Treat the README as the project contract.
  - The rules, level-generation guarantees, and acceptance criteria in the README are the authoritative baseline for future work.

## Working style for this repo

- Keep changes small and directly linked to the game spec.
- When adding code, prefer a clear separation between pure rule logic, solver logic, generator logic, and UI logic.
- If there is no implementation yet, do not add speculative framework structure just to “make it feel like a project”; build the minimum structure required to match the spec.
- When tests are introduced, keep them focused on game rules, solvability, and progression checks rather than broad UI-only assertions.

## Notes for future Copilot sessions

- This repo is a design-driven implementation task; the README is the real source of truth.
- The current checkout is intentionally sparse and should not be treated as a fully scaffolded codebase.
- Any future implementation should preserve the game’s “rule engine first, UI second” architecture and never weaken the solvability guarantees.
