"""Generated from CA ESP application 'CLINICAL_TRIALS_ETL'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor

with DAG(
    dag_id='clinical_trials_etl',
    description='ESP application CLINICAL_TRIALS_ETL',
    schedule='0 1 * * *',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'clinical_svc'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['wait_inventory'] = ExternalTaskSensor(
        task_id='wait_inventory',
        external_dag_id='drug_inventory',
        external_task_id='wait_inventory',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:72 (application CLINICAL_TRIALS_ETL, job WAIT_INVENTORY)',
        params={'esp_source_application': 'CLINICAL_TRIALS_ETL', 'esp_source_job': 'WAIT_INVENTORY', 'esp_source_line': 72},
    )
    tasks['extract_trial_data'] = SSHOperator(
        task_id='extract_trial_data',
        ssh_conn_id='LNX_CLINICAL_01',
        command='/opt/clinical/scripts/extract_trials.sh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:77 (application CLINICAL_TRIALS_ETL, job EXTRACT_TRIAL_DATA)',
        params={'esp_source_application': 'CLINICAL_TRIALS_ETL', 'esp_source_job': 'EXTRACT_TRIAL_DATA', 'esp_source_line': 77},
    )
    tasks['analyze_efficacy'] = SSHOperator(
        task_id='analyze_efficacy',
        ssh_conn_id='LNX_CLINICAL_01',
        command='/opt/clinical/scripts/efficacy_analysis.py',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:86 (application CLINICAL_TRIALS_ETL, job ANALYZE_EFFICACY)',
        params={'esp_source_application': 'CLINICAL_TRIALS_ETL', 'esp_source_job': 'ANALYZE_EFFICACY', 'esp_source_line': 86},
    )
    tasks['analyze_safety'] = SSHOperator(
        task_id='analyze_safety',
        ssh_conn_id='LNX_CLINICAL_02',
        command='/opt/clinical/scripts/safety_analysis.py',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:94 (application CLINICAL_TRIALS_ETL, job ANALYZE_SAFETY)',
        params={'esp_source_application': 'CLINICAL_TRIALS_ETL', 'esp_source_job': 'ANALYZE_SAFETY', 'esp_source_line': 94},
    )
    tasks['trial_report'] = SSHOperator(
        task_id='trial_report',
        ssh_conn_id='LNX_CLINICAL_01',
        command='/opt/clinical/scripts/generate_report.sh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:102 (application CLINICAL_TRIALS_ETL, job TRIAL_REPORT)',
        params={'esp_source_application': 'CLINICAL_TRIALS_ETL', 'esp_source_job': 'TRIAL_REPORT', 'esp_source_line': 102},
    )

    tasks['analyze_efficacy'] >> tasks['trial_report']
    tasks['analyze_safety'] >> tasks['trial_report']
    tasks['extract_trial_data'] >> tasks['analyze_efficacy']
    tasks['extract_trial_data'] >> tasks['analyze_safety']
    tasks['wait_inventory'] >> tasks['extract_trial_data']
