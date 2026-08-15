"""Generated from CA ESP application 'REGULATORY_REPORTING'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='regulatory_reporting',
    description='ESP application REGULATORY_REPORTING',
    schedule='0 6 * * 1-5',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['extract_compliance_data'] = MainframeSubmitJobOperator(
        task_id='extract_compliance_data',
        job_name='EXTRACT_COMPLIANCE_DATA',
        pool='nw_0001',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:122 (application REGULATORY_REPORTING, job EXTRACT_COMPLIANCE_DATA)',
        params={'esp_source_application': 'REGULATORY_REPORTING', 'esp_source_job': 'EXTRACT_COMPLIANCE_DATA', 'esp_source_line': 122},
    )
    tasks['build_fda_report'] = MainframeSubmitJobOperator(
        task_id='build_fda_report',
        job_name='BUILD_FDA_REPORT',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:129 (application REGULATORY_REPORTING, job BUILD_FDA_REPORT)',
        params={'esp_source_application': 'REGULATORY_REPORTING', 'esp_source_job': 'BUILD_FDA_REPORT', 'esp_source_line': 129},
    )
    tasks['build_ema_report'] = MainframeSubmitJobOperator(
        task_id='build_ema_report',
        job_name='BUILD_EMA_REPORT',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:134 (application REGULATORY_REPORTING, job BUILD_EMA_REPORT)',
        params={'esp_source_application': 'REGULATORY_REPORTING', 'esp_source_job': 'BUILD_EMA_REPORT', 'esp_source_line': 134},
    )
    tasks['submit_regulatory'] = MainframeSubmitJobOperator(
        task_id='submit_regulatory',
        job_name='SUBMIT_REGULATORY',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:139 (application REGULATORY_REPORTING, job SUBMIT_REGULATORY)',
        params={'esp_source_application': 'REGULATORY_REPORTING', 'esp_source_job': 'SUBMIT_REGULATORY', 'esp_source_line': 139},
    )

    tasks['build_ema_report'] >> tasks['submit_regulatory']
    tasks['build_fda_report'] >> tasks['submit_regulatory']
    tasks['extract_compliance_data'] >> tasks['build_ema_report']
    tasks['extract_compliance_data'] >> tasks['build_fda_report']
