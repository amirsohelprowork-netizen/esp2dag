"""Generated from CA ESP application 'WINDOWS_REPORTING'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.microsoft.winrm.operators.winrm import WinRMOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor

with DAG(
    dag_id='windows_reporting',
    description='ESP application WINDOWS_REPORTING',
    schedule='0 4 * * 1-5',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'svc_reports'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['wait_sap_for_reports'] = ExternalTaskSensor(
        task_id='wait_sap_for_reports',
        external_dag_id='sap_financials',
        external_task_id='wait_sap_for_reports',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:467 (application WINDOWS_REPORTING, job WAIT_SAP_FOR_REPORTS)',
        params={'esp_source_application': 'WINDOWS_REPORTING', 'esp_source_job': 'WAIT_SAP_FOR_REPORTS', 'esp_source_line': 467},
    )
    tasks['wait_risk_for_reports'] = ExternalTaskSensor(
        task_id='wait_risk_for_reports',
        external_dag_id='market_risk_var',
        external_task_id='wait_risk_for_reports',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:472 (application WINDOWS_REPORTING, job WAIT_RISK_FOR_REPORTS)',
        params={'esp_source_application': 'WINDOWS_REPORTING', 'esp_source_job': 'WAIT_RISK_FOR_REPORTS', 'esp_source_line': 472},
    )
    tasks['wr_build_reports'] = WinRMOperator(
        task_id='wr_build_reports',
        ssh_conn_id='WIN_RPT_01',
        command='E:\\Reporting\\scripts\\build_all_reports.bat',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:477 (application WINDOWS_REPORTING, job WR_BUILD_REPORTS)',
        params={'esp_source_application': 'WINDOWS_REPORTING', 'esp_source_job': 'WR_BUILD_REPORTS', 'esp_source_line': 477},
    )
    tasks['wr_generate_executive'] = WinRMOperator(
        task_id='wr_generate_executive',
        ssh_conn_id='WIN_RPT_01',
        command='E:\\Reporting\\scripts\\exec_dashboard.ps1',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:489 (application WINDOWS_REPORTING, job WR_GENERATE_EXECUTIVE)',
        params={'esp_source_application': 'WINDOWS_REPORTING', 'esp_source_job': 'WR_GENERATE_EXECUTIVE', 'esp_source_line': 489},
    )
    tasks['wr_generate_regulatory'] = WinRMOperator(
        task_id='wr_generate_regulatory',
        ssh_conn_id='WIN_RPT_02',
        command='E:\\Reporting\\scripts\\regulatory_reports.bat',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:497 (application WINDOWS_REPORTING, job WR_GENERATE_REGULATORY)',
        params={'esp_source_application': 'WINDOWS_REPORTING', 'esp_source_job': 'WR_GENERATE_REGULATORY', 'esp_source_line': 497},
    )
    tasks['wr_generate_branch'] = WinRMOperator(
        task_id='wr_generate_branch',
        ssh_conn_id='WIN_RPT_02',
        command='E:\\Reporting\\scripts\\branch_reports.bat',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:505 (application WINDOWS_REPORTING, job WR_GENERATE_BRANCH)',
        params={'esp_source_application': 'WINDOWS_REPORTING', 'esp_source_job': 'WR_GENERATE_BRANCH', 'esp_source_line': 505},
    )
    tasks['wr_distribute'] = WinRMOperator(
        task_id='wr_distribute',
        ssh_conn_id='WIN_RPT_01',
        command='E:\\Reporting\\scripts\\distribute_reports.ps1',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:513 (application WINDOWS_REPORTING, job WR_DISTRIBUTE)',
        params={'esp_source_application': 'WINDOWS_REPORTING', 'esp_source_job': 'WR_DISTRIBUTE', 'esp_source_line': 513},
    )

    tasks['wait_risk_for_reports'] >> tasks['wr_build_reports']
    tasks['wait_sap_for_reports'] >> tasks['wr_build_reports']
    tasks['wr_build_reports'] >> tasks['wr_generate_branch']
    tasks['wr_build_reports'] >> tasks['wr_generate_executive']
    tasks['wr_build_reports'] >> tasks['wr_generate_regulatory']
    tasks['wr_generate_branch'] >> tasks['wr_distribute']
    tasks['wr_generate_executive'] >> tasks['wr_distribute']
    tasks['wr_generate_regulatory'] >> tasks['wr_distribute']
