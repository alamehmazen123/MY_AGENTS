# Troubleshooting

## System won't start
- Check `build/outputs/resolution_table.json` exists
- Run `python build/build_resolver.py` to regenerate
- Verify lattice: `python -c "from kernel.lattice_verifier import verifier; print(verifier.verify())"`

## Event chain corrupted
- Recovery will auto-trigger on startup
- Check `data/dna/events.jsonl` integrity

## Model load fails
- Check Ollama running at OLLAMA_HOST
- Verify circuit breaker status in runtime metrics
