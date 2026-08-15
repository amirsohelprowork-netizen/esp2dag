"""Generated from CA ESP application 'CLAIMS_WINDOWS'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.microsoft.winrm.operators.winrm import WinRMOperator

with DAG(
    dag_id='claims_windows',
    description='ESP application CLAIMS_WINDOWS',
    schedule='0 20 * * *',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'svc_claims'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['claims_intake'] = WinRMOperator(
        task_id='claims_intake',
        ssh_conn_id='WIN_CLAIMS_01',
        command='D:\\ClaimsApp\\bin\\intake_processor.bat',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:22 (application CLAIMS_WINDOWS, job CLAIMS_INTAKE)',
        params={'esp_source_application': 'CLAIMS_WINDOWS', 'esp_source_job': 'CLAIMS_INTAKE', 'esp_source_line': 22},
    )
    tasks['claims_validate'] = WinRMOperator(
        task_id='claims_validate',
        ssh_conn_id='WIN_CLAIMS_01',
        command='D:\\ClaimsApp\\bin\\validate_claims.exe',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:30 (application CLAIMS_WINDOWS, job CLAIMS_VALIDATE)',
        params={'esp_source_application': 'CLAIMS_WINDOWS', 'esp_source_job': 'CLAIMS_VALIDATE', 'esp_source_line': 30},
    )
    tasks['claims_adjudicate'] = WinRMOperator(
        task_id='claims_adjudicate',
        ssh_conn_id='WIN_CLAIMS_02',
        command='D:\\ClaimsApp\\bin\\adjudicate.bat',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:39 (application CLAIMS_WINDOWS, job CLAIMS_ADJUDICATE)',
        params={'esp_source_application': 'CLAIMS_WINDOWS', 'esp_source_job': 'CLAIMS_ADJUDICATE', 'esp_source_line': 39},
    )
    tasks['claims_fraud_check'] = WinRMOperator(
        task_id='claims_fraud_check',
        ssh_conn_id='WIN_CLAIMS_02',
        command='D:\\FraudDetection\\run_check.ps1',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:47 (application CLAIMS_WINDOWS, job CLAIMS_FRAUD_CHECK)',
        params={'esp_source_application': 'CLAIMS_WINDOWS', 'esp_source_job': 'CLAIMS_FRAUD_CHECK', 'esp_source_line': 47},
    )
    tasks['claims_payment'] = WinRMOperator(
        task_id='claims_payment',
        ssh_conn_id='WIN_CLAIMS_01',
        command='D:\\PaymentGateway\\process_payments.bat',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:55 (application CLAIMS_WINDOWS, job CLAIMS_PAYMENT)',
        params={'esp_source_application': 'CLAIMS_WINDOWS', 'esp_source_job': 'CLAIMS_PAYMENT', 'esp_source_line': 55},
    )

    tasks['claims_adjudicate'] >> tasks['claims_payment']
    tasks['claims_fraud_check'] >> tasks['claims_payment']
    tasks['claims_intake'] >> tasks['claims_validate']
    tasks['claims_validate'] >> tasks['claims_adjudicate']
    tasks['claims_validate'] >> tasks['claims_fraud_check']
