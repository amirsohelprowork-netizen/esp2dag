"""Generated from CA ESP application 'REPORT_DISTRIBUTION'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='report_distribution',
    description='ESP application REPORT_DISTRIBUTION',
    schedule='0 5 * * *',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['build_daily_summary'] = MainframeSubmitJobOperator(
        task_id='build_daily_summary',
        job_name='BUILD_DAILY_SUMMARY',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:107 (application REPORT_DISTRIBUTION, job BUILD_DAILY_SUMMARY)',
        params={'esp_source_application': 'REPORT_DISTRIBUTION', 'esp_source_job': 'BUILD_DAILY_SUMMARY', 'esp_source_line': 107},
    )
    tasks['print_branch_reports'] = MainframeSubmitJobOperator(
        task_id='print_branch_reports',
        job_name='PRINT_BRANCH_REPORTS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:114 (application REPORT_DISTRIBUTION, job PRINT_BRANCH_REPORTS)',
        params={'esp_source_application': 'REPORT_DISTRIBUTION', 'esp_source_job': 'PRINT_BRANCH_REPORTS', 'esp_source_line': 114},
    )
    tasks['print_exec_summary'] = MainframeSubmitJobOperator(
        task_id='print_exec_summary',
        job_name='PRINT_EXEC_SUMMARY',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:118 (application REPORT_DISTRIBUTION, job PRINT_EXEC_SUMMARY)',
        params={'esp_source_application': 'REPORT_DISTRIBUTION', 'esp_source_job': 'PRINT_EXEC_SUMMARY', 'esp_source_line': 118},
    )
    tasks['archive_reports'] = MainframeSubmitJobOperator(
        task_id='archive_reports',
        job_name='ARCHIVE_REPORTS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\01_basic_batch.esp:122 (application REPORT_DISTRIBUTION, job ARCHIVE_REPORTS)',
        params={'esp_source_application': 'REPORT_DISTRIBUTION', 'esp_source_job': 'ARCHIVE_REPORTS', 'esp_source_line': 122},
    )

    tasks['build_daily_summary'] >> tasks['archive_reports']
    tasks['build_daily_summary'] >> tasks['print_branch_reports']
    tasks['build_daily_summary'] >> tasks['print_exec_summary']
