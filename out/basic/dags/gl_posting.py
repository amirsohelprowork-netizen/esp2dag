"""Generated from CA ESP application 'GL_POSTING'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='gl_posting',
    description='ESP application GL_POSTING',
    schedule='0 23 * * 1-5',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['gl_initialize'] = MainframeSubmitJobOperator(
        task_id='gl_initialize',
        job_name='GL_INITIALIZE',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:61 (application GL_POSTING, job GL_INITIALIZE)',
        params={'esp_source_application': 'GL_POSTING', 'esp_source_job': 'GL_INITIALIZE', 'esp_source_line': 61},
    )
    tasks['gl_post_ar'] = MainframeSubmitJobOperator(
        task_id='gl_post_ar',
        job_name='GL_POST_AR',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:68 (application GL_POSTING, job GL_POST_AR)',
        params={'esp_source_application': 'GL_POSTING', 'esp_source_job': 'GL_POST_AR', 'esp_source_line': 68},
    )
    tasks['gl_post_ap'] = MainframeSubmitJobOperator(
        task_id='gl_post_ap',
        job_name='GL_POST_AP',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:73 (application GL_POSTING, job GL_POST_AP)',
        params={'esp_source_application': 'GL_POSTING', 'esp_source_job': 'GL_POST_AP', 'esp_source_line': 73},
    )
    tasks['gl_post_payroll'] = MainframeSubmitJobOperator(
        task_id='gl_post_payroll',
        job_name='GL_POST_PAYROLL',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:78 (application GL_POSTING, job GL_POST_PAYROLL)',
        params={'esp_source_application': 'GL_POSTING', 'esp_source_job': 'GL_POST_PAYROLL', 'esp_source_line': 78},
    )
    tasks['gl_consolidate'] = MainframeSubmitJobOperator(
        task_id='gl_consolidate',
        job_name='GL_CONSOLIDATE',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:84 (application GL_POSTING, job GL_CONSOLIDATE)',
        params={'esp_source_application': 'GL_POSTING', 'esp_source_job': 'GL_CONSOLIDATE', 'esp_source_line': 84},
    )
    tasks['gl_balance_check'] = MainframeSubmitJobOperator(
        task_id='gl_balance_check',
        job_name='GL_BALANCE_CHECK',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:92 (application GL_POSTING, job GL_BALANCE_CHECK)',
        params={'esp_source_application': 'GL_POSTING', 'esp_source_job': 'GL_BALANCE_CHECK', 'esp_source_line': 92},
    )

    tasks['gl_consolidate'] >> tasks['gl_balance_check']
    tasks['gl_initialize'] >> tasks['gl_post_ap']
    tasks['gl_initialize'] >> tasks['gl_post_ar']
    tasks['gl_initialize'] >> tasks['gl_post_payroll']
    tasks['gl_post_ap'] >> tasks['gl_consolidate']
    tasks['gl_post_ar'] >> tasks['gl_consolidate']
    tasks['gl_post_payroll'] >> tasks['gl_consolidate']
