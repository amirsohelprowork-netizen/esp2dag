"""Generated from CA ESP application 'MONTH_END_CLOSE'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.sap.operators.sap_rfc import SapRfcOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='month_end_close',
    description='ESP application MONTH_END_CLOSE. Schedule requires migration review: 19.00 LAST WORKDAY OF MONTH',
    schedule=None,
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['wait_all_daily_core'] = ExternalTaskSensor(
        task_id='wait_all_daily_core',
        external_dag_id='core_banking_eod',
        external_task_id='wait_all_daily_core',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:620 (application MONTH_END_CLOSE, job WAIT_ALL_DAILY_CORE)',
        params={'esp_source_application': 'MONTH_END_CLOSE', 'esp_source_job': 'WAIT_ALL_DAILY_CORE', 'esp_source_line': 620},
    )
    tasks['wait_all_daily_sap'] = ExternalTaskSensor(
        task_id='wait_all_daily_sap',
        external_dag_id='sap_financials',
        external_task_id='wait_all_daily_sap',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:625 (application MONTH_END_CLOSE, job WAIT_ALL_DAILY_SAP)',
        params={'esp_source_application': 'MONTH_END_CLOSE', 'esp_source_job': 'WAIT_ALL_DAILY_SAP', 'esp_source_line': 625},
    )
    tasks['me_freeze_accounts'] = MainframeSubmitJobOperator(
        task_id='me_freeze_accounts',
        job_name='ME_FREEZE_ACCOUNTS',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:630 (application MONTH_END_CLOSE, job ME_FREEZE_ACCOUNTS)',
        params={'esp_source_application': 'MONTH_END_CLOSE', 'esp_source_job': 'ME_FREEZE_ACCOUNTS', 'esp_source_line': 630},
    )
    tasks['me_accrue_interest'] = MainframeSubmitJobOperator(
        task_id='me_accrue_interest',
        job_name='ME_ACCRUE_INTEREST',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:640 (application MONTH_END_CLOSE, job ME_ACCRUE_INTEREST)',
        params={'esp_source_application': 'MONTH_END_CLOSE', 'esp_source_job': 'ME_ACCRUE_INTEREST', 'esp_source_line': 640},
    )
    tasks['me_accrue_expenses'] = MainframeSubmitJobOperator(
        task_id='me_accrue_expenses',
        job_name='ME_ACCRUE_EXPENSES',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:645 (application MONTH_END_CLOSE, job ME_ACCRUE_EXPENSES)',
        params={'esp_source_application': 'MONTH_END_CLOSE', 'esp_source_job': 'ME_ACCRUE_EXPENSES', 'esp_source_line': 645},
    )
    tasks['me_trial_balance'] = MainframeSubmitJobOperator(
        task_id='me_trial_balance',
        job_name='ME_TRIAL_BALANCE',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:650 (application MONTH_END_CLOSE, job ME_TRIAL_BALANCE)',
        params={'esp_source_application': 'MONTH_END_CLOSE', 'esp_source_job': 'ME_TRIAL_BALANCE', 'esp_source_line': 650},
    )
    tasks['me_intercompany_elim'] = MainframeSubmitJobOperator(
        task_id='me_intercompany_elim',
        job_name='ME_INTERCOMPANY_ELIM',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:659 (application MONTH_END_CLOSE, job ME_INTERCOMPANY_ELIM)',
        params={'esp_source_application': 'MONTH_END_CLOSE', 'esp_source_job': 'ME_INTERCOMPANY_ELIM', 'esp_source_line': 659},
    )
    tasks['me_consolidation'] = MainframeSubmitJobOperator(
        task_id='me_consolidation',
        job_name='ME_CONSOLIDATION',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:664 (application MONTH_END_CLOSE, job ME_CONSOLIDATION)',
        params={'esp_source_application': 'MONTH_END_CLOSE', 'esp_source_job': 'ME_CONSOLIDATION', 'esp_source_line': 664},
    )
    tasks['me_post_to_sap'] = SapRfcOperator(
        task_id='me_post_to_sap',
        conn_id='SAP_PROD_01',
        abap_name='RGGBS000',
        variant='MONTH_END_CLOSE',
        sap_job_name='FI_MONTH_CLOSE',
        sap_job_class='A',
        step_user='BATCHFI',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:671 (application MONTH_END_CLOSE, job ME_POST_TO_SAP)',
        params={'esp_source_application': 'MONTH_END_CLOSE', 'esp_source_job': 'ME_POST_TO_SAP', 'esp_source_line': 671},
    )
    tasks['me_close_complete'] = EmptyOperator(
        task_id='me_close_complete',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:684 (application MONTH_END_CLOSE, job ME_CLOSE_COMPLETE)',
        params={'esp_source_application': 'MONTH_END_CLOSE', 'esp_source_job': 'ME_CLOSE_COMPLETE', 'esp_source_line': 684},
    )

    tasks['me_accrue_expenses'] >> tasks['me_trial_balance']
    tasks['me_accrue_interest'] >> tasks['me_trial_balance']
    tasks['me_consolidation'] >> tasks['me_post_to_sap']
    tasks['me_freeze_accounts'] >> tasks['me_accrue_expenses']
    tasks['me_freeze_accounts'] >> tasks['me_accrue_interest']
    tasks['me_intercompany_elim'] >> tasks['me_consolidation']
    tasks['me_post_to_sap'] >> tasks['me_close_complete']
    tasks['me_trial_balance'] >> tasks['me_intercompany_elim']
    tasks['wait_all_daily_core'] >> tasks['me_freeze_accounts']
    tasks['wait_all_daily_sap'] >> tasks['me_freeze_accounts']
