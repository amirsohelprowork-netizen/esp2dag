"""Generated from CA ESP application 'MARKET_RISK_VAR'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor

with DAG(
    dag_id='market_risk_var',
    description='ESP application MARKET_RISK_VAR',
    schedule='0 21 * * 1-5',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'riskengine'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['wait_settlement'] = ExternalTaskSensor(
        task_id='wait_settlement',
        external_dag_id='trading_settlement',
        external_task_id='wait_settlement',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:258 (application MARKET_RISK_VAR, job WAIT_SETTLEMENT)',
        params={'esp_source_application': 'MARKET_RISK_VAR', 'esp_source_job': 'WAIT_SETTLEMENT', 'esp_source_line': 258},
    )
    tasks['mr_load_positions'] = SSHOperator(
        task_id='mr_load_positions',
        ssh_conn_id='AIX_RISK_PROD_01',
        command='/opt/risk/scripts/load_positions.ksh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:263 (application MARKET_RISK_VAR, job MR_LOAD_POSITIONS)',
        params={'esp_source_application': 'MARKET_RISK_VAR', 'esp_source_job': 'MR_LOAD_POSITIONS', 'esp_source_line': 263},
    )
    tasks['mr_monte_carlo'] = SSHOperator(
        task_id='mr_monte_carlo',
        ssh_conn_id='AIX_RISK_PROD_01',
        command='/opt/risk/bin/mc_var_engine --iterations 500000 --confidence 0.99 --horizon 10d',
        pool='nw_0004',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:271 (application MARKET_RISK_VAR, job MR_MONTE_CARLO)',
        params={'esp_source_application': 'MARKET_RISK_VAR', 'esp_source_job': 'MR_MONTE_CARLO', 'esp_source_line': 271},
    )
    tasks['mr_stress_test'] = SSHOperator(
        task_id='mr_stress_test',
        ssh_conn_id='AIX_RISK_PROD_02',
        command='/opt/risk/bin/stress_test_engine --scenarios /opt/risk/conf/stress_scenarios.json',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:281 (application MARKET_RISK_VAR, job MR_STRESS_TEST)',
        params={'esp_source_application': 'MARKET_RISK_VAR', 'esp_source_job': 'MR_STRESS_TEST', 'esp_source_line': 281},
    )
    tasks['mr_aggregate_risk'] = SSHOperator(
        task_id='mr_aggregate_risk',
        ssh_conn_id='AIX_RISK_PROD_01',
        command='/opt/risk/scripts/aggregate_risk_metrics.ksh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:290 (application MARKET_RISK_VAR, job MR_AGGREGATE_RISK)',
        params={'esp_source_application': 'MARKET_RISK_VAR', 'esp_source_job': 'MR_AGGREGATE_RISK', 'esp_source_line': 290},
    )
    tasks['mr_risk_complete'] = EmptyOperator(
        task_id='mr_risk_complete',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:300 (application MARKET_RISK_VAR, job MR_RISK_COMPLETE)',
        params={'esp_source_application': 'MARKET_RISK_VAR', 'esp_source_job': 'MR_RISK_COMPLETE', 'esp_source_line': 300},
    )

    tasks['mr_aggregate_risk'] >> tasks['mr_risk_complete']
    tasks['mr_load_positions'] >> tasks['mr_monte_carlo']
    tasks['mr_monte_carlo'] >> tasks['mr_stress_test']
    tasks['mr_stress_test'] >> tasks['mr_aggregate_risk']
    tasks['wait_settlement'] >> tasks['mr_load_positions']
