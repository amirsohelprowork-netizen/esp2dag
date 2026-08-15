"""Generated from CA ESP application 'DATA_LAKE_INGESTION'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor
from custom_operators.mainframe import MainframeDatasetSensor

with DAG(
    dag_id='data_lake_ingestion',
    description='ESP application DATA_LAKE_INGESTION',
    schedule='0 1 * * *',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'hadoop_svc'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['wait_core_for_lake'] = ExternalTaskSensor(
        task_id='wait_core_for_lake',
        external_dag_id='core_banking_eod',
        external_task_id='wait_core_for_lake',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:535 (application DATA_LAKE_INGESTION, job WAIT_CORE_FOR_LAKE)',
        params={'esp_source_application': 'DATA_LAKE_INGESTION', 'esp_source_job': 'WAIT_CORE_FOR_LAKE', 'esp_source_line': 535},
    )
    tasks['wait_trading_for_lake'] = ExternalTaskSensor(
        task_id='wait_trading_for_lake',
        external_dag_id='trading_settlement',
        external_task_id='wait_trading_for_lake',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:540 (application DATA_LAKE_INGESTION, job WAIT_TRADING_FOR_LAKE)',
        params={'esp_source_application': 'DATA_LAKE_INGESTION', 'esp_source_job': 'WAIT_TRADING_FOR_LAKE', 'esp_source_line': 540},
    )
    tasks['dl_wait_sap_extract'] = MainframeDatasetSensor(
        task_id='dl_wait_sap_extract',
        dsname='SAP.EXTRACT.DAILY.FEED',
        mode='reschedule',
        poke_interval=60,
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:546 (application DATA_LAKE_INGESTION, job DL_WAIT_SAP_EXTRACT)',
        params={'esp_source_application': 'DATA_LAKE_INGESTION', 'esp_source_job': 'DL_WAIT_SAP_EXTRACT', 'esp_source_line': 546},
    )
    tasks['dl_ingest_core'] = SSHOperator(
        task_id='dl_ingest_core',
        ssh_conn_id='LNX_HADOOP_01',
        command='/opt/datalake/scripts/ingest_core_banking.sh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:552 (application DATA_LAKE_INGESTION, job DL_INGEST_CORE)',
        params={'esp_source_application': 'DATA_LAKE_INGESTION', 'esp_source_job': 'DL_INGEST_CORE', 'esp_source_line': 552},
    )
    tasks['dl_ingest_trading'] = SSHOperator(
        task_id='dl_ingest_trading',
        ssh_conn_id='LNX_HADOOP_01',
        command='/opt/datalake/scripts/ingest_trading.sh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:560 (application DATA_LAKE_INGESTION, job DL_INGEST_TRADING)',
        params={'esp_source_application': 'DATA_LAKE_INGESTION', 'esp_source_job': 'DL_INGEST_TRADING', 'esp_source_line': 560},
    )
    tasks['dl_ingest_sap'] = SSHOperator(
        task_id='dl_ingest_sap',
        ssh_conn_id='LNX_HADOOP_02',
        command='/opt/datalake/scripts/ingest_sap.sh',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:568 (application DATA_LAKE_INGESTION, job DL_INGEST_SAP)',
        params={'esp_source_application': 'DATA_LAKE_INGESTION', 'esp_source_job': 'DL_INGEST_SAP', 'esp_source_line': 568},
    )
    tasks['dl_build_unified_view'] = SSHOperator(
        task_id='dl_build_unified_view',
        ssh_conn_id='LNX_HADOOP_01',
        command='/opt/spark/bin/spark-submit --master yarn --deploy-mode cluster --class com.bank.UnifiedView /opt/datalake/jars/unified_view.jar',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:576 (application DATA_LAKE_INGESTION, job DL_BUILD_UNIFIED_VIEW)',
        params={'esp_source_application': 'DATA_LAKE_INGESTION', 'esp_source_job': 'DL_BUILD_UNIFIED_VIEW', 'esp_source_line': 576},
    )
    tasks['dl_quality_checks'] = SSHOperator(
        task_id='dl_quality_checks',
        ssh_conn_id='LNX_HADOOP_02',
        command='/opt/datalake/scripts/data_quality_checks.py',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:586 (application DATA_LAKE_INGESTION, job DL_QUALITY_CHECKS)',
        params={'esp_source_application': 'DATA_LAKE_INGESTION', 'esp_source_job': 'DL_QUALITY_CHECKS', 'esp_source_line': 586},
    )
    tasks['dl_complete'] = EmptyOperator(
        task_id='dl_complete',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:595 (application DATA_LAKE_INGESTION, job DL_COMPLETE)',
        params={'esp_source_application': 'DATA_LAKE_INGESTION', 'esp_source_job': 'DL_COMPLETE', 'esp_source_line': 595},
    )

    tasks['dl_build_unified_view'] >> tasks['dl_quality_checks']
    tasks['dl_ingest_core'] >> tasks['dl_build_unified_view']
    tasks['dl_ingest_sap'] >> tasks['dl_build_unified_view']
    tasks['dl_ingest_trading'] >> tasks['dl_build_unified_view']
    tasks['dl_quality_checks'] >> tasks['dl_complete']
    tasks['dl_wait_sap_extract'] >> tasks['dl_ingest_sap']
    tasks['wait_core_for_lake'] >> tasks['dl_ingest_core']
    tasks['wait_trading_for_lake'] >> tasks['dl_ingest_trading']
