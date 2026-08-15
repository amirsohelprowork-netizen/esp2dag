"""Generated from CA ESP application 'MAINTENANCE_CYCLIC'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='maintenance_cyclic',
    description='ESP application MAINTENANCE_CYCLIC',
    schedule='0 6 * * *',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['check_fleet_status'] = MainframeSubmitJobOperator(
        task_id='check_fleet_status',
        job_name='CHECK_FLEET_STATUS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:174 (application MAINTENANCE_CYCLIC, job CHECK_FLEET_STATUS)',
        params={'esp_source_application': 'MAINTENANCE_CYCLIC', 'esp_source_job': 'CHECK_FLEET_STATUS', 'esp_source_line': 174},
    )
    tasks['schedule_inspections'] = MainframeSubmitJobOperator(
        task_id='schedule_inspections',
        job_name='SCHEDULE_INSPECTIONS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:179 (application MAINTENANCE_CYCLIC, job SCHEDULE_INSPECTIONS)',
        params={'esp_source_application': 'MAINTENANCE_CYCLIC', 'esp_source_job': 'SCHEDULE_INSPECTIONS', 'esp_source_line': 179},
    )
    tasks['assign_mechanics'] = MainframeSubmitJobOperator(
        task_id='assign_mechanics',
        job_name='ASSIGN_MECHANICS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:184 (application MAINTENANCE_CYCLIC, job ASSIGN_MECHANICS)',
        params={'esp_source_application': 'MAINTENANCE_CYCLIC', 'esp_source_job': 'ASSIGN_MECHANICS', 'esp_source_line': 184},
    )
    tasks['track_completion'] = MainframeSubmitJobOperator(
        task_id='track_completion',
        job_name='TRACK_COMPLETION',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:189 (application MAINTENANCE_CYCLIC, job TRACK_COMPLETION)',
        params={'esp_source_application': 'MAINTENANCE_CYCLIC', 'esp_source_job': 'TRACK_COMPLETION', 'esp_source_line': 189},
    )
    tasks['maint_cycle_done'] = EmptyOperator(
        task_id='maint_cycle_done',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\04_advanced_scheduling.esp:196 (application MAINTENANCE_CYCLIC, job MAINT_CYCLE_DONE)',
        params={'esp_source_application': 'MAINTENANCE_CYCLIC', 'esp_source_job': 'MAINT_CYCLE_DONE', 'esp_source_line': 196},
    )

    tasks['assign_mechanics'] >> tasks['track_completion']
    tasks['check_fleet_status'] >> tasks['schedule_inspections']
    tasks['schedule_inspections'] >> tasks['assign_mechanics']
    tasks['track_completion'] >> tasks['maint_cycle_done']
