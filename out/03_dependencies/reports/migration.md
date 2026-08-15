# Migration Report

- Applications summarized: **5**
- Manual review suggested: **4**
- Colliding DAG ids: **0**

## Custom operators required

- `custom_operators.mainframe.MainframeSubmitJobOperator`: 15 task(s)
- `custom_operators.mainframe.MainframeDatasetSensor`: 1 task(s)

## Colliding DAG ids

- (none)

## Applications needing attention

- `drug_inventory`: custom ops
- `order_fulfillment`: custom ops
- `regulatory_reporting`: custom ops
- `supply_chain`: custom ops
