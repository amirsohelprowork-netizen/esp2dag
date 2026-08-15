# Migration Report

- Applications summarized: **11**
- Manual review suggested: **8**
- Colliding DAG ids: **0**

## Custom operators required

- `custom_operators.mainframe.MainframeSubmitJobOperator`: 32 task(s)
- `custom_operators.as400.AS400Operator`: 4 task(s)
- `custom_operators.mainframe.MainframeDatasetSensor`: 2 task(s)

## Colliding DAG ids

- (none)

## Applications needing attention

- `as400_legacy_feeds`: custom ops
- `core_banking_eod`: custom ops
- `credit_risk_batch`: custom ops
- `data_lake_ingestion`: custom ops
- `lending_batch`: custom ops
- `month_end_close`: custom ops
- `regulatory_capital`: custom ops
- `trading_settlement`: custom ops
