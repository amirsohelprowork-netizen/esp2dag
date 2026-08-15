"""Generated from CA ESP application 'DATA_WAREHOUSE_ETL'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator

with DAG(
    dag_id='data_warehouse_etl',
    description='ESP application DATA_WAREHOUSE_ETL',
    schedule='0 2 * * *',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'etl_svc'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['stage_raw_data'] = SSHOperator(
        task_id='stage_raw_data',
        ssh_conn_id='LNX_ETL_01',
        command='/opt/etl/scripts/stage_raw_data.sh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:75 (application DATA_WAREHOUSE_ETL, job STAGE_RAW_DATA)',
        params={'esp_source_application': 'DATA_WAREHOUSE_ETL', 'esp_source_job': 'STAGE_RAW_DATA', 'esp_source_line': 75},
    )
    tasks['transform_dimensions'] = SSHOperator(
        task_id='transform_dimensions',
        ssh_conn_id='LNX_ETL_01',
        command='/opt/etl/scripts/transform_dims.sh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:84 (application DATA_WAREHOUSE_ETL, job TRANSFORM_DIMENSIONS)',
        params={'esp_source_application': 'DATA_WAREHOUSE_ETL', 'esp_source_job': 'TRANSFORM_DIMENSIONS', 'esp_source_line': 84},
    )
    tasks['transform_facts'] = SSHOperator(
        task_id='transform_facts',
        ssh_conn_id='LNX_ETL_02',
        command='/opt/etl/scripts/transform_facts.sh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:92 (application DATA_WAREHOUSE_ETL, job TRANSFORM_FACTS)',
        params={'esp_source_application': 'DATA_WAREHOUSE_ETL', 'esp_source_job': 'TRANSFORM_FACTS', 'esp_source_line': 92},
    )
    tasks['load_warehouse'] = SSHOperator(
        task_id='load_warehouse',
        ssh_conn_id='LNX_ETL_01',
        command='/opt/etl/scripts/load_warehouse.sh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:100 (application DATA_WAREHOUSE_ETL, job LOAD_WAREHOUSE)',
        params={'esp_source_application': 'DATA_WAREHOUSE_ETL', 'esp_source_job': 'LOAD_WAREHOUSE', 'esp_source_line': 100},
    )
    tasks['build_cubes'] = SSHOperator(
        task_id='build_cubes',
        ssh_conn_id='LNX_ETL_02',
        command='/opt/etl/bin/cube_builder --config /opt/etl/conf/cubes.yaml --parallel 8',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:110 (application DATA_WAREHOUSE_ETL, job BUILD_CUBES)',
        params={'esp_source_application': 'DATA_WAREHOUSE_ETL', 'esp_source_job': 'BUILD_CUBES', 'esp_source_line': 110},
    )
    tasks['refresh_dashboards'] = SSHOperator(
        task_id='refresh_dashboards',
        ssh_conn_id='LNX_ETL_01',
        command='/opt/etl/scripts/refresh_tableau.sh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:119 (application DATA_WAREHOUSE_ETL, job REFRESH_DASHBOARDS)',
        params={'esp_source_application': 'DATA_WAREHOUSE_ETL', 'esp_source_job': 'REFRESH_DASHBOARDS', 'esp_source_line': 119},
    )

    tasks['build_cubes'] >> tasks['refresh_dashboards']
    tasks['load_warehouse'] >> tasks['build_cubes']
    tasks['stage_raw_data'] >> tasks['transform_dimensions']
    tasks['stage_raw_data'] >> tasks['transform_facts']
    tasks['transform_dimensions'] >> tasks['load_warehouse']
    tasks['transform_facts'] >> tasks['load_warehouse']
