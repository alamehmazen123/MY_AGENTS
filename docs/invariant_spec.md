# Invariant Spec

## Core Invariants
- single_runtime: Only one model active at any time
- reflex_deterministic: Reflex layer never calls inference
- memory_bounded: RAM < 95% available
- thermal_safe: GPU < 85C
- deliberation_bounded: Iterations <= 4, tokens <= 12000
- workspace_jailed: All file ops within workspace root
- queue_bounded: Queue depth <= 100
- model_switch_safe: Switch < 30s, no VRAM leak
- evolution_reversible: Every patch has verified rollback
- recovery_automatic: Recovery < 5000ms, 0 event loss

## Lattice Property
If A implies B, satisfying A satisfies B. No cycles.
