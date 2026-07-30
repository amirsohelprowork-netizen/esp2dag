# Data

| Path | Purpose |
|------|---------|
| `anonymized/schedule.esp` | Redacted full ESP schedule (demo / evaluation input) |
| `anonymized/events.esp` | Redacted full ESP events |
| `samples/` | Tiny fixtures for quick demos and CI |

Private raw extracts (if present locally) live under `not_atonymized/` and are **gitignored** — never commit them. Rebuild public samples with `python scripts/rebuild_anonymized.py`.

## Convert

```bash
python -m esp2dag yaml data/anonymized/schedule.esp data/anonymized/events.esp -o out/yaml_full
python -m esp2dag compile data/anonymized/schedule.esp data/anonymized/events.esp -o out/full
```

More detail: [docs/USAGE.md](../docs/USAGE.md)

## License

Inputs here are synthetic/redacted. The project license still applies — commercial use requires permission ([LICENSE](../LICENSE)).
