"""Generated from CA ESP application 'RISK_ENGINE_AIX'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator

with DAG(
    dag_id='risk_engine_aix',
    description='ESP application RISK_ENGINE_AIX',
    schedule='0 17 * * 1-5',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'riskuser'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['load_market_data'] = SSHOperator(
        task_id='load_market_data',
        ssh_conn_id='AIX_RISK_01',
        command='/opt/risk/scripts/load_market_data.ksh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:181 (application RISK_ENGINE_AIX, job LOAD_MARKET_DATA)',
        params={'esp_source_application': 'RISK_ENGINE_AIX', 'esp_source_job': 'LOAD_MARKET_DATA', 'esp_source_line': 181},
    )
    tasks['calc_var'] = SSHOperator(
        task_id='calc_var',
        ssh_conn_id='AIX_RISK_01',
        command='/opt/risk/bin/var_engine --model montecarlo --iterations 100000',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:190 (application RISK_ENGINE_AIX, job CALC_VAR)',
        params={'esp_source_application': 'RISK_ENGINE_AIX', 'esp_source_job': 'CALC_VAR', 'esp_source_line': 190},
    )
    tasks['calc_credit_risk'] = SSHOperator(
        task_id='calc_credit_risk',
        ssh_conn_id='AIX_RISK_02',
        command='/opt/risk/bin/credit_risk_engine --portfolio ALL --horizon 1Y',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:199 (application RISK_ENGINE_AIX, job CALC_CREDIT_RISK)',
        params={'esp_source_application': 'RISK_ENGINE_AIX', 'esp_source_job': 'CALC_CREDIT_RISK', 'esp_source_line': 199},
    )
    tasks['aggregate_risk'] = SSHOperator(
        task_id='aggregate_risk',
        ssh_conn_id='AIX_RISK_01',
        command='/opt/risk/scripts/aggregate_reports.ksh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\02_multi_platform.esp:208 (application RISK_ENGINE_AIX, job AGGREGATE_RISK)',
        params={'esp_source_application': 'RISK_ENGINE_AIX', 'esp_source_job': 'AGGREGATE_RISK', 'esp_source_line': 208},
    )

    tasks['calc_credit_risk'] >> tasks['aggregate_risk']
    tasks['calc_var'] >> tasks['aggregate_risk']
    tasks['load_market_data'] >> tasks['calc_credit_risk']
    tasks['load_market_data'] >> tasks['calc_var']
