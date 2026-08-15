"""Generated from CA ESP application 'LENDING_BATCH'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='lending_batch',
    description='ESP application LENDING_BATCH',
    schedule='0 20 * * 1-5',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['wait_core_banking'] = ExternalTaskSensor(
        task_id='wait_core_banking',
        external_dag_id='core_banking_eod',
        external_task_id='wait_core_banking',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:133 (application LENDING_BATCH, job WAIT_CORE_BANKING)',
        params={'esp_source_application': 'LENDING_BATCH', 'esp_source_job': 'WAIT_CORE_BANKING', 'esp_source_line': 133},
    )
    tasks['ln_extract_payments'] = MainframeSubmitJobOperator(
        task_id='ln_extract_payments',
        job_name='LN_EXTRACT_PAYMENTS',
        pool='nw_0002',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:138 (application LENDING_BATCH, job LN_EXTRACT_PAYMENTS)',
        params={'esp_source_application': 'LENDING_BATCH', 'esp_source_job': 'LN_EXTRACT_PAYMENTS', 'esp_source_line': 138},
    )
    tasks['ln_apply_payments'] = MainframeSubmitJobOperator(
        task_id='ln_apply_payments',
        job_name='LN_APPLY_PAYMENTS',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:144 (application LENDING_BATCH, job LN_APPLY_PAYMENTS)',
        params={'esp_source_application': 'LENDING_BATCH', 'esp_source_job': 'LN_APPLY_PAYMENTS', 'esp_source_line': 144},
    )
    tasks['ln_calc_amortization'] = MainframeSubmitJobOperator(
        task_id='ln_calc_amortization',
        job_name='LN_CALC_AMORTIZATION',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:151 (application LENDING_BATCH, job LN_CALC_AMORTIZATION)',
        params={'esp_source_application': 'LENDING_BATCH', 'esp_source_job': 'LN_CALC_AMORTIZATION', 'esp_source_line': 151},
    )
    tasks['ln_past_due_check'] = MainframeSubmitJobOperator(
        task_id='ln_past_due_check',
        job_name='LN_PAST_DUE_CHECK',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:156 (application LENDING_BATCH, job LN_PAST_DUE_CHECK)',
        params={'esp_source_application': 'LENDING_BATCH', 'esp_source_job': 'LN_PAST_DUE_CHECK', 'esp_source_line': 156},
    )
    tasks['ln_collections_notify'] = MainframeSubmitJobOperator(
        task_id='ln_collections_notify',
        job_name='LN_COLLECTIONS_NOTIFY',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:163 (application LENDING_BATCH, job LN_COLLECTIONS_NOTIFY)',
        params={'esp_source_application': 'LENDING_BATCH', 'esp_source_job': 'LN_COLLECTIONS_NOTIFY', 'esp_source_line': 163},
    )
    tasks['ln_update_schedules'] = MainframeSubmitJobOperator(
        task_id='ln_update_schedules',
        job_name='LN_UPDATE_SCHEDULES',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:167 (application LENDING_BATCH, job LN_UPDATE_SCHEDULES)',
        params={'esp_source_application': 'LENDING_BATCH', 'esp_source_job': 'LN_UPDATE_SCHEDULES', 'esp_source_line': 167},
    )
    tasks['ln_complete'] = EmptyOperator(
        task_id='ln_complete',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:174 (application LENDING_BATCH, job LN_COMPLETE)',
        params={'esp_source_application': 'LENDING_BATCH', 'esp_source_job': 'LN_COMPLETE', 'esp_source_line': 174},
    )

    tasks['ln_apply_payments'] >> tasks['ln_calc_amortization']
    tasks['ln_apply_payments'] >> tasks['ln_past_due_check']
    tasks['ln_calc_amortization'] >> tasks['ln_update_schedules']
    tasks['ln_extract_payments'] >> tasks['ln_apply_payments']
    tasks['ln_past_due_check'] >> tasks['ln_collections_notify']
    tasks['ln_past_due_check'] >> tasks['ln_update_schedules']
    tasks['ln_update_schedules'] >> tasks['ln_complete']
    tasks['wait_core_banking'] >> tasks['ln_extract_payments']
