"""Generated from CA ESP application 'REVENUE_MONTHLY'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='revenue_monthly',
    description='ESP application REVENUE_MONTHLY. Schedule requires migration review: 18.00 LAST WORKDAY OF MONTH',
    schedule=None,
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['close_revenue_period'] = MainframeSubmitJobOperator(
        task_id='close_revenue_period',
        job_name='CLOSE_REVENUE_PERIOD',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:85 (application REVENUE_MONTHLY, job CLOSE_REVENUE_PERIOD)',
        params={'esp_source_application': 'REVENUE_MONTHLY', 'esp_source_job': 'CLOSE_REVENUE_PERIOD', 'esp_source_line': 85},
    )
    tasks['calc_deferred_revenue'] = MainframeSubmitJobOperator(
        task_id='calc_deferred_revenue',
        job_name='CALC_DEFERRED_REVENUE',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:92 (application REVENUE_MONTHLY, job CALC_DEFERRED_REVENUE)',
        params={'esp_source_application': 'REVENUE_MONTHLY', 'esp_source_job': 'CALC_DEFERRED_REVENUE', 'esp_source_line': 92},
    )
    tasks['calc_accruals'] = MainframeSubmitJobOperator(
        task_id='calc_accruals',
        job_name='CALC_ACCRUALS',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:98 (application REVENUE_MONTHLY, job CALC_ACCRUALS)',
        params={'esp_source_application': 'REVENUE_MONTHLY', 'esp_source_job': 'CALC_ACCRUALS', 'esp_source_line': 98},
    )
    tasks['revenue_reconciliation'] = MainframeSubmitJobOperator(
        task_id='revenue_reconciliation',
        job_name='REVENUE_RECONCILIATION',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:104 (application REVENUE_MONTHLY, job REVENUE_RECONCILIATION)',
        params={'esp_source_application': 'REVENUE_MONTHLY', 'esp_source_job': 'REVENUE_RECONCILIATION', 'esp_source_line': 104},
    )
    tasks['management_reporting'] = MainframeSubmitJobOperator(
        task_id='management_reporting',
        job_name='MANAGEMENT_REPORTING',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:113 (application REVENUE_MONTHLY, job MANAGEMENT_REPORTING)',
        params={'esp_source_application': 'REVENUE_MONTHLY', 'esp_source_job': 'MANAGEMENT_REPORTING', 'esp_source_line': 113},
    )

    tasks['calc_accruals'] >> tasks['revenue_reconciliation']
    tasks['calc_deferred_revenue'] >> tasks['revenue_reconciliation']
    tasks['close_revenue_period'] >> tasks['calc_accruals']
    tasks['close_revenue_period'] >> tasks['calc_deferred_revenue']
    tasks['revenue_reconciliation'] >> tasks['management_reporting']
