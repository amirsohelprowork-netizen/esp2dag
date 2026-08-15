"""Generated from CA ESP application 'REGULATORY_CAPITAL'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.microsoft.winrm.operators.winrm import WinRMOperator
from airflow.providers.sap.operators.sap_rfc import SapRfcOperator
from airflow.providers.ssh.operators.ssh import SSHOperator
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='regulatory_capital',
    description='ESP application REGULATORY_CAPITAL. Schedule requires migration review: 08.00 1ST WORKDAY OF QUARTER',
    schedule=None,
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'riskengine'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['rc_extract_positions'] = MainframeSubmitJobOperator(
        task_id='rc_extract_positions',
        job_name='RC_EXTRACT_POSITIONS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:702 (application REGULATORY_CAPITAL, job RC_EXTRACT_POSITIONS)',
        params={'esp_source_application': 'REGULATORY_CAPITAL', 'esp_source_job': 'RC_EXTRACT_POSITIONS', 'esp_source_line': 702},
    )
    tasks['rc_extract_risk_weights'] = MainframeSubmitJobOperator(
        task_id='rc_extract_risk_weights',
        job_name='RC_EXTRACT_RISK_WEIGHTS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:707 (application REGULATORY_CAPITAL, job RC_EXTRACT_RISK_WEIGHTS)',
        params={'esp_source_application': 'REGULATORY_CAPITAL', 'esp_source_job': 'RC_EXTRACT_RISK_WEIGHTS', 'esp_source_line': 707},
    )
    tasks['rc_calc_rwa'] = SSHOperator(
        task_id='rc_calc_rwa',
        ssh_conn_id='AIX_RISK_PROD_01',
        command='/opt/risk/bin/rwa_calculator --framework basel4 --approach advanced',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:713 (application REGULATORY_CAPITAL, job RC_CALC_RWA)',
        params={'esp_source_application': 'REGULATORY_CAPITAL', 'esp_source_job': 'RC_CALC_RWA', 'esp_source_line': 713},
    )
    tasks['rc_calc_capital_ratio'] = MainframeSubmitJobOperator(
        task_id='rc_calc_capital_ratio',
        job_name='RC_CALC_CAPITAL_RATIO',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:724 (application REGULATORY_CAPITAL, job RC_CALC_CAPITAL_RATIO)',
        params={'esp_source_application': 'REGULATORY_CAPITAL', 'esp_source_job': 'RC_CALC_CAPITAL_RATIO', 'esp_source_line': 724},
    )
    tasks['rc_build_submission'] = SSHOperator(
        task_id='rc_build_submission',
        ssh_conn_id='LNX_REGULATORY_01',
        command='/opt/regulatory/scripts/build_corep_xml.py',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:731 (application REGULATORY_CAPITAL, job RC_BUILD_SUBMISSION)',
        params={'esp_source_application': 'REGULATORY_CAPITAL', 'esp_source_job': 'RC_BUILD_SUBMISSION', 'esp_source_line': 731},
    )
    tasks['rc_sap_post_capital'] = SapRfcOperator(
        task_id='rc_sap_post_capital',
        conn_id='SAP_PROD_01',
        abap_name='ZREGCAP01',
        variant='QUARTERLY_CAPITAL',
        sap_job_name='REG_CAPITAL_POST',
        sap_job_class='A',
        step_user='BATCHREG',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:741 (application REGULATORY_CAPITAL, job RC_SAP_POST_CAPITAL)',
        params={'esp_source_application': 'REGULATORY_CAPITAL', 'esp_source_job': 'RC_SAP_POST_CAPITAL', 'esp_source_line': 741},
    )
    tasks['rc_generate_board_report'] = WinRMOperator(
        task_id='rc_generate_board_report',
        ssh_conn_id='WIN_RPT_01',
        command='E:\\Regulatory\\scripts\\generate_board_capital_report.bat',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:753 (application REGULATORY_CAPITAL, job RC_GENERATE_BOARD_REPORT)',
        params={'esp_source_application': 'REGULATORY_CAPITAL', 'esp_source_job': 'RC_GENERATE_BOARD_REPORT', 'esp_source_line': 753},
    )
    tasks['rc_submit_to_regulator'] = MainframeSubmitJobOperator(
        task_id='rc_submit_to_regulator',
        job_name='RC_SUBMIT_TO_REGULATOR',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:761 (application REGULATORY_CAPITAL, job RC_SUBMIT_TO_REGULATOR)',
        params={'esp_source_application': 'REGULATORY_CAPITAL', 'esp_source_job': 'RC_SUBMIT_TO_REGULATOR', 'esp_source_line': 761},
    )

    tasks['rc_build_submission'] >> tasks['rc_generate_board_report']
    tasks['rc_build_submission'] >> tasks['rc_sap_post_capital']
    tasks['rc_calc_capital_ratio'] >> tasks['rc_build_submission']
    tasks['rc_calc_rwa'] >> tasks['rc_calc_capital_ratio']
    tasks['rc_extract_positions'] >> tasks['rc_extract_risk_weights']
    tasks['rc_extract_risk_weights'] >> tasks['rc_calc_rwa']
    tasks['rc_generate_board_report'] >> tasks['rc_submit_to_regulator']
    tasks['rc_sap_post_capital'] >> tasks['rc_submit_to_regulator']
