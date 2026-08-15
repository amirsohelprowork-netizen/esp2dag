"""Generated from CA ESP application 'SAP_FINANCIALS'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.sap.operators.sap_rfc import SapRfcOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor

with DAG(
    dag_id='sap_financials',
    description='ESP application SAP_FINANCIALS',
    schedule='0 23 * * 1-5',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['wait_core_for_sap'] = ExternalTaskSensor(
        task_id='wait_core_for_sap',
        external_dag_id='core_banking_eod',
        external_task_id='wait_core_for_sap',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:384 (application SAP_FINANCIALS, job WAIT_CORE_FOR_SAP)',
        params={'esp_source_application': 'SAP_FINANCIALS', 'esp_source_job': 'WAIT_CORE_FOR_SAP', 'esp_source_line': 384},
    )
    tasks['wait_lending_for_sap'] = ExternalTaskSensor(
        task_id='wait_lending_for_sap',
        external_dag_id='lending_batch',
        external_task_id='wait_lending_for_sap',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:389 (application SAP_FINANCIALS, job WAIT_LENDING_FOR_SAP)',
        params={'esp_source_application': 'SAP_FINANCIALS', 'esp_source_job': 'WAIT_LENDING_FOR_SAP', 'esp_source_line': 389},
    )
    tasks['sap_post_gl'] = SapRfcOperator(
        task_id='sap_post_gl',
        conn_id='SAP_PROD_01',
        abap_name='RGGBS000',
        variant='PROD_GL_DAILY',
        sap_job_name='FI_GL_POST',
        sap_job_class='A',
        step_user='BATCHFI',
        pool='nw_0005',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:394 (application SAP_FINANCIALS, job SAP_POST_GL)',
        params={'esp_source_application': 'SAP_FINANCIALS', 'esp_source_job': 'SAP_POST_GL', 'esp_source_line': 394},
    )
    tasks['sap_post_ar'] = SapRfcOperator(
        task_id='sap_post_ar',
        conn_id='SAP_PROD_01',
        abap_name='RFEPOS00',
        variant='PROD_AR_DAILY',
        sap_job_name='FI_AR_POST',
        sap_job_class='A',
        step_user='BATCHFI',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:409 (application SAP_FINANCIALS, job SAP_POST_AR)',
        params={'esp_source_application': 'SAP_FINANCIALS', 'esp_source_job': 'SAP_POST_AR', 'esp_source_line': 409},
    )
    tasks['sap_post_ap'] = SapRfcOperator(
        task_id='sap_post_ap',
        conn_id='SAP_PROD_01',
        abap_name='RFFOUS_T',
        variant='PROD_AP_DAILY',
        sap_job_name='FI_AP_POST',
        sap_job_class='A',
        step_user='BATCHFI',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:420 (application SAP_FINANCIALS, job SAP_POST_AP)',
        params={'esp_source_application': 'SAP_FINANCIALS', 'esp_source_job': 'SAP_POST_AP', 'esp_source_line': 420},
    )
    tasks['sap_reconcile'] = SapRfcOperator(
        task_id='sap_reconcile',
        conn_id='SAP_PROD_01',
        abap_name='SAPF190',
        variant='PROD_RECONCILE',
        sap_job_name='FI_RECONCILE',
        sap_job_class='B',
        step_user='BATCHFI',
        pool='nw_0005',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:431 (application SAP_FINANCIALS, job SAP_RECONCILE)',
        params={'esp_source_application': 'SAP_FINANCIALS', 'esp_source_job': 'SAP_RECONCILE', 'esp_source_line': 431},
    )
    tasks['sap_fi_complete'] = EmptyOperator(
        task_id='sap_fi_complete',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:447 (application SAP_FINANCIALS, job SAP_FI_COMPLETE)',
        params={'esp_source_application': 'SAP_FINANCIALS', 'esp_source_job': 'SAP_FI_COMPLETE', 'esp_source_line': 447},
    )

    tasks['sap_post_ap'] >> tasks['sap_reconcile']
    tasks['sap_post_ar'] >> tasks['sap_reconcile']
    tasks['sap_post_gl'] >> tasks['sap_post_ap']
    tasks['sap_post_gl'] >> tasks['sap_post_ar']
    tasks['sap_reconcile'] >> tasks['sap_fi_complete']
    tasks['wait_core_for_sap'] >> tasks['sap_post_gl']
    tasks['wait_lending_for_sap'] >> tasks['sap_post_gl']
