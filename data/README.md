# Data

| Path | Purpose |
|------|---------|
| `anonymized/schedule.esp` | Redacted full schedule (primary input) |
| `anonymized/events.esp` | Redacted full events (primary input) |
| `samples/` | Small safe fixtures for demos and tests |

Compile:

```bash
python -m esp2dag yaml data/anonymized/schedule.esp data/anonymized/events.esp -o out/yaml_full
```
