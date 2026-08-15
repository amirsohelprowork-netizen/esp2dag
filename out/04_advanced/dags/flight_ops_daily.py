"""Generated from CA ESP application 'FLIGHT_OPS_DAILY'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='flight_ops_daily',
    description='ESP application FLIGHT_OPS_DAILY',
    schedule='0 4,22 * * *',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['crew_scheduling'] = MainframeSubmitJobOperator(
        task_id='crew_scheduling',
        job_name='CREW_SCHEDULING',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:31 (application FLIGHT_OPS_DAILY, job CREW_SCHEDULING)',
        params={'esp_source_application': 'FLIGHT_OPS_DAILY', 'esp_source_job': 'CREW_SCHEDULING', 'esp_source_line': 31},
    )
    tasks['gate_assignments'] = MainframeSubmitJobOperator(
        task_id='gate_assignments',
        job_name='GATE_ASSIGNMENTS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:37 (application FLIGHT_OPS_DAILY, job GATE_ASSIGNMENTS)',
        params={'esp_source_application': 'FLIGHT_OPS_DAILY', 'esp_source_job': 'GATE_ASSIGNMENTS', 'esp_source_line': 37},
    )
    tasks['fuel_planning'] = MainframeSubmitJobOperator(
        task_id='fuel_planning',
        job_name='FUEL_PLANNING',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:43 (application FLIGHT_OPS_DAILY, job FUEL_PLANNING)',
        params={'esp_source_application': 'FLIGHT_OPS_DAILY', 'esp_source_job': 'FUEL_PLANNING', 'esp_source_line': 43},
    )
    tasks['catering_orders'] = MainframeSubmitJobOperator(
        task_id='catering_orders',
        job_name='CATERING_ORDERS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:48 (application FLIGHT_OPS_DAILY, job CATERING_ORDERS)',
        params={'esp_source_application': 'FLIGHT_OPS_DAILY', 'esp_source_job': 'CATERING_ORDERS', 'esp_source_line': 48},
    )
    tasks['dispatch_briefing'] = MainframeSubmitJobOperator(
        task_id='dispatch_briefing',
        job_name='DISPATCH_BRIEFING',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:53 (application FLIGHT_OPS_DAILY, job DISPATCH_BRIEFING)',
        params={'esp_source_application': 'FLIGHT_OPS_DAILY', 'esp_source_job': 'DISPATCH_BRIEFING', 'esp_source_line': 53},
    )
    tasks['weekly_ops_analysis'] = MainframeSubmitJobOperator(
        task_id='weekly_ops_analysis',
        job_name='WEEKLY_OPS_ANALYSIS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:61 (application FLIGHT_OPS_DAILY, job WEEKLY_OPS_ANALYSIS)',
        params={'esp_source_application': 'FLIGHT_OPS_DAILY', 'esp_source_job': 'WEEKLY_OPS_ANALYSIS', 'esp_source_line': 61},
    )
    tasks['ops_complete'] = EmptyOperator(
        task_id='ops_complete',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:66 (application FLIGHT_OPS_DAILY, job OPS_COMPLETE)',
        params={'esp_source_application': 'FLIGHT_OPS_DAILY', 'esp_source_job': 'OPS_COMPLETE', 'esp_source_line': 66},
    )

    tasks['catering_orders'] >> tasks['dispatch_briefing']
    tasks['crew_scheduling'] >> tasks['gate_assignments']
    tasks['dispatch_briefing'] >> tasks['ops_complete']
    tasks['fuel_planning'] >> tasks['dispatch_briefing']
    tasks['gate_assignments'] >> tasks['catering_orders']
    tasks['gate_assignments'] >> tasks['fuel_planning']
    tasks['weekly_ops_analysis'] >> tasks['ops_complete']
