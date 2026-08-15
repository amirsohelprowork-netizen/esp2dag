"""Generated from CA ESP application 'SUPPLY_CHAIN'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='supply_chain',
    description='ESP application SUPPLY_CHAIN',
    schedule='0 3 * * *',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['wait_inv_done'] = ExternalTaskSensor(
        task_id='wait_inv_done',
        external_dag_id='drug_inventory',
        external_task_id='wait_inv_done',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:160 (application SUPPLY_CHAIN, job WAIT_INV_DONE)',
        params={'esp_source_application': 'SUPPLY_CHAIN', 'esp_source_job': 'WAIT_INV_DONE', 'esp_source_line': 160},
    )
    tasks['forecast_demand'] = MainframeSubmitJobOperator(
        task_id='forecast_demand',
        job_name='FORECAST_DEMAND',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:165 (application SUPPLY_CHAIN, job FORECAST_DEMAND)',
        params={'esp_source_application': 'SUPPLY_CHAIN', 'esp_source_job': 'FORECAST_DEMAND', 'esp_source_line': 165},
    )
    tasks['plan_procurement'] = MainframeSubmitJobOperator(
        task_id='plan_procurement',
        job_name='PLAN_PROCUREMENT',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:171 (application SUPPLY_CHAIN, job PLAN_PROCUREMENT)',
        params={'esp_source_application': 'SUPPLY_CHAIN', 'esp_source_job': 'PLAN_PROCUREMENT', 'esp_source_line': 171},
    )
    tasks['plan_distribution'] = MainframeSubmitJobOperator(
        task_id='plan_distribution',
        job_name='PLAN_DISTRIBUTION',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:176 (application SUPPLY_CHAIN, job PLAN_DISTRIBUTION)',
        params={'esp_source_application': 'SUPPLY_CHAIN', 'esp_source_job': 'PLAN_DISTRIBUTION', 'esp_source_line': 176},
    )
    tasks['procurement_ready'] = EmptyOperator(
        task_id='procurement_ready',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:182 (application SUPPLY_CHAIN, job PROCUREMENT_READY)',
        params={'esp_source_application': 'SUPPLY_CHAIN', 'esp_source_job': 'PROCUREMENT_READY', 'esp_source_line': 182},
    )
    tasks['distribution_ready'] = EmptyOperator(
        task_id='distribution_ready',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:186 (application SUPPLY_CHAIN, job DISTRIBUTION_READY)',
        params={'esp_source_application': 'SUPPLY_CHAIN', 'esp_source_job': 'DISTRIBUTION_READY', 'esp_source_line': 186},
    )
    tasks['execute_orders'] = MainframeSubmitJobOperator(
        task_id='execute_orders',
        job_name='EXECUTE_ORDERS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:190 (application SUPPLY_CHAIN, job EXECUTE_ORDERS)',
        params={'esp_source_application': 'SUPPLY_CHAIN', 'esp_source_job': 'EXECUTE_ORDERS', 'esp_source_line': 190},
    )
    tasks['supply_chain_done'] = EmptyOperator(
        task_id='supply_chain_done',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:198 (application SUPPLY_CHAIN, job SUPPLY_CHAIN_DONE)',
        params={'esp_source_application': 'SUPPLY_CHAIN', 'esp_source_job': 'SUPPLY_CHAIN_DONE', 'esp_source_line': 198},
    )

    tasks['distribution_ready'] >> tasks['execute_orders']
    tasks['execute_orders'] >> tasks['supply_chain_done']
    tasks['forecast_demand'] >> tasks['plan_distribution']
    tasks['forecast_demand'] >> tasks['plan_procurement']
    tasks['plan_distribution'] >> tasks['distribution_ready']
    tasks['plan_procurement'] >> tasks['procurement_ready']
    tasks['procurement_ready'] >> tasks['execute_orders']
    tasks['wait_inv_done'] >> tasks['forecast_demand']
