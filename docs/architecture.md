# Architecture — my_agents PRIS v12.0

## Overview
Pre-Resolved Invariant System (PRIS). All hard problems solved offline. Runtime is O(1) lookup only.

## Layers
1. **Build** — Offline resolution, pareto, lattice proof, recovery verification
2. **Kernel** — Config, Universe, Events, Resolution Table, Lattice Verifier, Recovery
3. **Cells** — Reflex, Deliberation, Evolution, Runtime, Workspace, MCP, Gateway
4. **Plasma** — SQLite WAL, Event Log, Snapshots, Recovery Journal, Blob Store
5. **Frontend** — React 18 + Vite + Tailwind, dual panels, observatory

## Invariants
See `build/outputs/lattice_proof.md`.

## Entry Point
`python kernel/main.py`
