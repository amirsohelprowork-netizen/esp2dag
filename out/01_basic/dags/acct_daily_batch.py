"""Generated from CA ESP application 'ACCT_DAILY_BATCH'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='acct_daily_batch',
    description='ESP application ACCT_DAILY_BATCH',
    schedule='0 22 * * *',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['extract_transactions'] = MainframeSubmitJobOperator(
        task_id='extract_transactions',
        job_name='EXTRACT_TRANSACTIONS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:20 (application ACCT_DAILY_BATCH, job EXTRACT_TRANSACTIONS)',
        params={'esp_source_application': 'ACCT_DAILY_BATCH', 'esp_source_job': 'EXTRACT_TRANSACTIONS', 'esp_source_line': 20},
    )
    tasks['validate_data'] = MainframeSubmitJobOperator(
        task_id='validate_data',
        job_name='VALIDATE_DATA',
        ccchk='(0,4)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:25 (application ACCT_DAILY_BATCH, job VALIDATE_DATA)',
        params={'esp_source_application': 'ACCT_DAILY_BATCH', 'esp_source_job': 'VALIDATE_DATA', 'esp_source_line': 25},
    )
    tasks['post_accounts'] = MainframeSubmitJobOperator(
        task_id='post_accounts',
        job_name='POST_ACCOUNTS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:32 (application ACCT_DAILY_BATCH, job POST_ACCOUNTS)',
        params={'esp_source_application': 'ACCT_DAILY_BATCH', 'esp_source_job': 'POST_ACCOUNTS', 'esp_source_line': 32},
    )
    tasks['reconcile'] = MainframeSubmitJobOperator(
        task_id='reconcile',
        job_name='RECONCILE',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:37 (application ACCT_DAILY_BATCH, job RECONCILE)',
        params={'esp_source_application': 'ACCT_DAILY_BATCH', 'esp_source_job': 'RECONCILE', 'esp_source_line': 37},
    )
    tasks['audit_trail'] = MainframeSubmitJobOperator(
        task_id='audit_trail',
        job_name='AUDIT_TRAIL',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:42 (application ACCT_DAILY_BATCH, job AUDIT_TRAIL)',
        params={'esp_source_application': 'ACCT_DAILY_BATCH', 'esp_source_job': 'AUDIT_TRAIL', 'esp_source_line': 42},
    )
    tasks['err_handler'] = MainframeSubmitJobOperator(
        task_id='err_handler',
        job_name='ERR_HANDLER',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:47 (application ACCT_DAILY_BATCH, job ERR_HANDLER)',
        params={'esp_source_application': 'ACCT_DAILY_BATCH', 'esp_source_job': 'ERR_HANDLER', 'esp_source_line': 47},
    )

    tasks['extract_transactions'] >> tasks['validate_data']
    tasks['post_accounts'] >> tasks['reconcile']
    tasks['reconcile'] >> tasks['audit_trail']
    tasks['validate_data'] >> tasks['err_handler']
    tasks['validate_data'] >> tasks['post_accounts']
