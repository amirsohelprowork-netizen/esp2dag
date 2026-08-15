"""Generated from CA ESP application 'QUARTERLY_COMPLIANCE'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='quarterly_compliance',
    description='ESP application QUARTERLY_COMPLIANCE. Schedule requires migration review: 08.00 1ST WORKDAY OF QUARTER',
    schedule=None,
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['extract_quarterly_data'] = MainframeSubmitJobOperator(
        task_id='extract_quarterly_data',
        job_name='EXTRACT_QUARTERLY_DATA',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:214 (application QUARTERLY_COMPLIANCE, job EXTRACT_QUARTERLY_DATA)',
        params={'esp_source_application': 'QUARTERLY_COMPLIANCE', 'esp_source_job': 'EXTRACT_QUARTERLY_DATA', 'esp_source_line': 214},
    )
    tasks['standard_audit'] = MainframeSubmitJobOperator(
        task_id='standard_audit',
        job_name='STANDARD_AUDIT',
        ccchk='(0,4)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:220 (application QUARTERLY_COMPLIANCE, job STANDARD_AUDIT)',
        params={'esp_source_application': 'QUARTERLY_COMPLIANCE', 'esp_source_job': 'STANDARD_AUDIT', 'esp_source_line': 220},
    )
    tasks['safety_audit'] = MainframeSubmitJobOperator(
        task_id='safety_audit',
        job_name='SAFETY_AUDIT',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:226 (application QUARTERLY_COMPLIANCE, job SAFETY_AUDIT)',
        params={'esp_source_application': 'QUARTERLY_COMPLIANCE', 'esp_source_job': 'SAFETY_AUDIT', 'esp_source_line': 226},
    )
    tasks['compile_quarterly_report'] = MainframeSubmitJobOperator(
        task_id='compile_quarterly_report',
        job_name='COMPILE_QUARTERLY_REPORT',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:231 (application QUARTERLY_COMPLIANCE, job COMPILE_QUARTERLY_REPORT)',
        params={'esp_source_application': 'QUARTERLY_COMPLIANCE', 'esp_source_job': 'COMPILE_QUARTERLY_REPORT', 'esp_source_line': 231},
    )
    tasks['submit_to_faa'] = MainframeSubmitJobOperator(
        task_id='submit_to_faa',
        job_name='SUBMIT_TO_FAA',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:239 (application QUARTERLY_COMPLIANCE, job SUBMIT_TO_FAA)',
        params={'esp_source_application': 'QUARTERLY_COMPLIANCE', 'esp_source_job': 'SUBMIT_TO_FAA', 'esp_source_line': 239},
    )

    tasks['compile_quarterly_report'] >> tasks['submit_to_faa']
    tasks['extract_quarterly_data'] >> tasks['safety_audit']
    tasks['extract_quarterly_data'] >> tasks['standard_audit']
    tasks['safety_audit'] >> tasks['compile_quarterly_report']
    tasks['standard_audit'] >> tasks['compile_quarterly_report']
