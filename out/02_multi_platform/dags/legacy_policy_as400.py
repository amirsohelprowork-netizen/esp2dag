"""Generated from CA ESP application 'LEGACY_POLICY_AS400'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from custom_operators.as400 import AS400Operator

with DAG(
    dag_id='legacy_policy_as400',
    description='ESP application LEGACY_POLICY_AS400',
    schedule='0 21 * * *',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'QSECOFR'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['extract_policies'] = AS400Operator(
        task_id='extract_policies',
        conn_id='AS400_PROD_01_AS400',
        command='CALL PGM(POLLIB/POLEXT) PARM(DAILY)',
        job_queue='QBATCH',
        pool='AS400_PROD_01',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:136 (application LEGACY_POLICY_AS400, job EXTRACT_POLICIES)',
        params={'esp_source_application': 'LEGACY_POLICY_AS400', 'esp_source_job': 'EXTRACT_POLICIES', 'esp_source_line': 136},
    )
    tasks['calc_premiums'] = AS400Operator(
        task_id='calc_premiums',
        conn_id='AS400_PROD_01_AS400',
        command='CALL PGM(POLLIB/PREMCALC)',
        job_queue='QBATCH',
        pool='AS400_PROD_01',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:145 (application LEGACY_POLICY_AS400, job CALC_PREMIUMS)',
        params={'esp_source_application': 'LEGACY_POLICY_AS400', 'esp_source_job': 'CALC_PREMIUMS', 'esp_source_line': 145},
    )
    tasks['update_policy_db'] = AS400Operator(
        task_id='update_policy_db',
        conn_id='AS400_PROD_01_AS400',
        command='CALL PGM(POLLIB/POLUPD) PARM(COMMIT)',
        job_queue='QBATCH',
        pool='AS400_PROD_01',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:155 (application LEGACY_POLICY_AS400, job UPDATE_POLICY_DB)',
        params={'esp_source_application': 'LEGACY_POLICY_AS400', 'esp_source_job': 'UPDATE_POLICY_DB', 'esp_source_line': 155},
    )
    tasks['generate_notices'] = AS400Operator(
        task_id='generate_notices',
        conn_id='AS400_PROD_01_AS400',
        command='CALL PGM(POLLIB/NOTICEGEN)',
        job_queue='QBATCH',
        pool='AS400_PROD_01',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:163 (application LEGACY_POLICY_AS400, job GENERATE_NOTICES)',
        params={'esp_source_application': 'LEGACY_POLICY_AS400', 'esp_source_job': 'GENERATE_NOTICES', 'esp_source_line': 163},
    )

    tasks['calc_premiums'] >> tasks['generate_notices']
    tasks['calc_premiums'] >> tasks['update_policy_db']
    tasks['extract_policies'] >> tasks['calc_premiums']
