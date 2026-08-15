"""Generated from CA ESP application 'AS400_LEGACY_FEEDS'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from custom_operators.as400 import AS400Operator

with DAG(
    dag_id='as400_legacy_feeds',
    description='ESP application AS400_LEGACY_FEEDS',
    schedule='0 17 * * *',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'QSECOFR'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['as4_extract_customers'] = AS400Operator(
        task_id='as4_extract_customers',
        conn_id='AS400_FINANCE_01_AS400',
        command='CALL PGM(FINLIB/CUSTEXT) PARM(DAILY PROD)',
        job_queue='QBATCH',
        pool='nw_0001',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:779 (application AS400_LEGACY_FEEDS, job AS4_EXTRACT_CUSTOMERS)',
        params={'esp_source_application': 'AS400_LEGACY_FEEDS', 'esp_source_job': 'AS4_EXTRACT_CUSTOMERS', 'esp_source_line': 779},
    )
    tasks['as4_extract_accounts'] = AS400Operator(
        task_id='as4_extract_accounts',
        conn_id='AS400_FINANCE_01_AS400',
        command='CALL PGM(FINLIB/ACCTEXT) PARM(DAILY PROD)',
        job_queue='QBATCH',
        pool='AS400_FINANCE_01',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:789 (application AS400_LEGACY_FEEDS, job AS4_EXTRACT_ACCOUNTS)',
        params={'esp_source_application': 'AS400_LEGACY_FEEDS', 'esp_source_job': 'AS4_EXTRACT_ACCOUNTS', 'esp_source_line': 789},
    )
    tasks['as4_transform_data'] = AS400Operator(
        task_id='as4_transform_data',
        conn_id='AS400_FINANCE_01_AS400',
        command='CALL PGM(FINLIB/XFORMDAT) PARM(FULL)',
        job_queue='QBATCH',
        pool='AS400_FINANCE_01',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:798 (application AS400_LEGACY_FEEDS, job AS4_TRANSFORM_DATA)',
        params={'esp_source_application': 'AS400_LEGACY_FEEDS', 'esp_source_job': 'AS4_TRANSFORM_DATA', 'esp_source_line': 798},
    )
    tasks['as4_send_to_mq'] = AS400Operator(
        task_id='as4_send_to_mq',
        conn_id='AS400_FINANCE_01_AS400',
        command='CALL PGM(FINLIB/MQSEND) PARM(PROD.QUEUE.LEGACY)',
        job_queue='QBATCH',
        pool='AS400_FINANCE_01',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:807 (application AS400_LEGACY_FEEDS, job AS4_SEND_TO_MQ)',
        params={'esp_source_application': 'AS400_LEGACY_FEEDS', 'esp_source_job': 'AS4_SEND_TO_MQ', 'esp_source_line': 807},
    )

    tasks['as4_extract_accounts'] >> tasks['as4_transform_data']
    tasks['as4_extract_customers'] >> tasks['as4_extract_accounts']
    tasks['as4_transform_data'] >> tasks['as4_send_to_mq']
