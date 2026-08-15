"""Generated from CA ESP application 'TRADING_SETTLEMENT'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor
from custom_operators.mainframe import MainframeDatasetSensor
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='trading_settlement',
    description='ESP application TRADING_SETTLEMENT',
    schedule='0 19 * * 1-5',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'settle_svc'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['wait_market_data'] = MainframeDatasetSensor(
        task_id='wait_market_data',
        dsname='TRADING.MARKET.PRICES.DAILY',
        mode='reschedule',
        poke_interval=60,
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:195 (application TRADING_SETTLEMENT, job WAIT_MARKET_DATA)',
        params={'esp_source_application': 'TRADING_SETTLEMENT', 'esp_source_job': 'WAIT_MARKET_DATA', 'esp_source_line': 195},
    )
    tasks['wait_core_for_settle'] = ExternalTaskSensor(
        task_id='wait_core_for_settle',
        external_dag_id='core_banking_eod',
        external_task_id='wait_core_for_settle',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:202 (application TRADING_SETTLEMENT, job WAIT_CORE_FOR_SETTLE)',
        params={'esp_source_application': 'TRADING_SETTLEMENT', 'esp_source_job': 'WAIT_CORE_FOR_SETTLE', 'esp_source_line': 202},
    )
    tasks['ts_match_trades'] = MainframeSubmitJobOperator(
        task_id='ts_match_trades',
        job_name='TS_MATCH_TRADES',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:207 (application TRADING_SETTLEMENT, job TS_MATCH_TRADES)',
        params={'esp_source_application': 'TRADING_SETTLEMENT', 'esp_source_job': 'TS_MATCH_TRADES', 'esp_source_line': 207},
    )
    tasks['ts_calc_settlement'] = MainframeSubmitJobOperator(
        task_id='ts_calc_settlement',
        job_name='TS_CALC_SETTLEMENT',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:214 (application TRADING_SETTLEMENT, job TS_CALC_SETTLEMENT)',
        params={'esp_source_application': 'TRADING_SETTLEMENT', 'esp_source_job': 'TS_CALC_SETTLEMENT', 'esp_source_line': 214},
    )
    tasks['ts_process_fails'] = MainframeSubmitJobOperator(
        task_id='ts_process_fails',
        job_name='TS_PROCESS_FAILS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:221 (application TRADING_SETTLEMENT, job TS_PROCESS_FAILS)',
        params={'esp_source_application': 'TRADING_SETTLEMENT', 'esp_source_job': 'TS_PROCESS_FAILS', 'esp_source_line': 221},
    )
    tasks['ts_deliver_securities'] = SSHOperator(
        task_id='ts_deliver_securities',
        ssh_conn_id='UNIX_SETTLE_01',
        command='/opt/trading/scripts/deliver_securities.sh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:226 (application TRADING_SETTLEMENT, job TS_DELIVER_SECURITIES)',
        params={'esp_source_application': 'TRADING_SETTLEMENT', 'esp_source_job': 'TS_DELIVER_SECURITIES', 'esp_source_line': 226},
    )
    tasks['ts_reconcile_positions'] = SSHOperator(
        task_id='ts_reconcile_positions',
        ssh_conn_id='UNIX_SETTLE_01',
        command='/opt/trading/scripts/reconcile_positions.ksh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:234 (application TRADING_SETTLEMENT, job TS_RECONCILE_POSITIONS)',
        params={'esp_source_application': 'TRADING_SETTLEMENT', 'esp_source_job': 'TS_RECONCILE_POSITIONS', 'esp_source_line': 234},
    )
    tasks['ts_settlement_complete'] = EmptyOperator(
        task_id='ts_settlement_complete',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:242 (application TRADING_SETTLEMENT, job TS_SETTLEMENT_COMPLETE)',
        params={'esp_source_application': 'TRADING_SETTLEMENT', 'esp_source_job': 'TS_SETTLEMENT_COMPLETE', 'esp_source_line': 242},
    )

    tasks['ts_calc_settlement'] >> tasks['ts_deliver_securities']
    tasks['ts_calc_settlement'] >> tasks['ts_process_fails']
    tasks['ts_deliver_securities'] >> tasks['ts_reconcile_positions']
    tasks['ts_match_trades'] >> tasks['ts_calc_settlement']
    tasks['ts_reconcile_positions'] >> tasks['ts_settlement_complete']
    tasks['wait_core_for_settle'] >> tasks['ts_match_trades']
    tasks['wait_market_data'] >> tasks['ts_match_trades']
