"""Generated from CA ESP application 'LOYALTY_BIWEEKLY'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='loyalty_biweekly',
    description='ESP application LOYALTY_BIWEEKLY. Schedule requires migration review: 01.00 EVERY 2 WEEKS STARTING JAN 8 2025',
    schedule=None,
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'loyalty_svc'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['extract_member_activity'] = MainframeSubmitJobOperator(
        task_id='extract_member_activity',
        job_name='EXTRACT_MEMBER_ACTIVITY',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:130 (application LOYALTY_BIWEEKLY, job EXTRACT_MEMBER_ACTIVITY)',
        params={'esp_source_application': 'LOYALTY_BIWEEKLY', 'esp_source_job': 'EXTRACT_MEMBER_ACTIVITY', 'esp_source_line': 130},
    )
    tasks['calc_points'] = SSHOperator(
        task_id='calc_points',
        ssh_conn_id='LNX_LOYALTY_01',
        command='/opt/loyalty/scripts/calculate_points.py',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:135 (application LOYALTY_BIWEEKLY, job CALC_POINTS)',
        params={'esp_source_application': 'LOYALTY_BIWEEKLY', 'esp_source_job': 'CALC_POINTS', 'esp_source_line': 135},
    )
    tasks['update_tier_status'] = SSHOperator(
        task_id='update_tier_status',
        ssh_conn_id='LNX_LOYALTY_01',
        command='/opt/loyalty/scripts/tier_evaluation.py',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:144 (application LOYALTY_BIWEEKLY, job UPDATE_TIER_STATUS)',
        params={'esp_source_application': 'LOYALTY_BIWEEKLY', 'esp_source_job': 'UPDATE_TIER_STATUS', 'esp_source_line': 144},
    )
    tasks['generate_statements'] = MainframeSubmitJobOperator(
        task_id='generate_statements',
        job_name='GENERATE_STATEMENTS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:152 (application LOYALTY_BIWEEKLY, job GENERATE_STATEMENTS)',
        params={'esp_source_application': 'LOYALTY_BIWEEKLY', 'esp_source_job': 'GENERATE_STATEMENTS', 'esp_source_line': 152},
    )
    tasks['loyalty_complete'] = EmptyOperator(
        task_id='loyalty_complete',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:157 (application LOYALTY_BIWEEKLY, job LOYALTY_COMPLETE)',
        params={'esp_source_application': 'LOYALTY_BIWEEKLY', 'esp_source_job': 'LOYALTY_COMPLETE', 'esp_source_line': 157},
    )

    tasks['calc_points'] >> tasks['generate_statements']
    tasks['calc_points'] >> tasks['update_tier_status']
    tasks['extract_member_activity'] >> tasks['calc_points']
    tasks['generate_statements'] >> tasks['loyalty_complete']
    tasks['update_tier_status'] >> tasks['loyalty_complete']
