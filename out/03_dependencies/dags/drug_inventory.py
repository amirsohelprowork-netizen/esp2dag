"""Generated from CA ESP application 'DRUG_INVENTORY'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from custom_operators.mainframe import MainframeDatasetSensor
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='drug_inventory',
    description='ESP application DRUG_INVENTORY',
    schedule='@daily',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['wait_inventory_feed'] = MainframeDatasetSensor(
        task_id='wait_inventory_feed',
        dsname='PHARMA.INVENTORY.DAILY.FEED',
        mode='reschedule',
        poke_interval=60,
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:27 (application DRUG_INVENTORY, job WAIT_INVENTORY_FEED)',
        params={'esp_source_application': 'DRUG_INVENTORY', 'esp_source_job': 'WAIT_INVENTORY_FEED', 'esp_source_line': 27},
    )
    tasks['validate_inventory'] = MainframeSubmitJobOperator(
        task_id='validate_inventory',
        job_name='VALIDATE_INVENTORY',
        ccchk='(0,4)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:33 (application DRUG_INVENTORY, job VALIDATE_INVENTORY)',
        params={'esp_source_application': 'DRUG_INVENTORY', 'esp_source_job': 'VALIDATE_INVENTORY', 'esp_source_line': 33},
    )
    tasks['update_stock_levels'] = MainframeSubmitJobOperator(
        task_id='update_stock_levels',
        job_name='UPDATE_STOCK_LEVELS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:41 (application DRUG_INVENTORY, job UPDATE_STOCK_LEVELS)',
        params={'esp_source_application': 'DRUG_INVENTORY', 'esp_source_job': 'UPDATE_STOCK_LEVELS', 'esp_source_line': 41},
    )
    tasks['flag_expiring_drugs'] = MainframeSubmitJobOperator(
        task_id='flag_expiring_drugs',
        job_name='FLAG_EXPIRING_DRUGS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:46 (application DRUG_INVENTORY, job FLAG_EXPIRING_DRUGS)',
        params={'esp_source_application': 'DRUG_INVENTORY', 'esp_source_job': 'FLAG_EXPIRING_DRUGS', 'esp_source_line': 46},
    )
    tasks['inventory_complete'] = EmptyOperator(
        task_id='inventory_complete',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:52 (application DRUG_INVENTORY, job INVENTORY_COMPLETE)',
        params={'esp_source_application': 'DRUG_INVENTORY', 'esp_source_job': 'INVENTORY_COMPLETE', 'esp_source_line': 52},
    )

    tasks['flag_expiring_drugs'] >> tasks['inventory_complete']
    tasks['update_stock_levels'] >> tasks['inventory_complete']
    tasks['validate_inventory'] >> tasks['flag_expiring_drugs']
    tasks['validate_inventory'] >> tasks['update_stock_levels']
    tasks['wait_inventory_feed'] >> tasks['validate_inventory']
