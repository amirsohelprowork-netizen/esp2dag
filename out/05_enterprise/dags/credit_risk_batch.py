"""Generated from CA ESP application 'CREDIT_RISK_BATCH'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='credit_risk_batch',
    description='ESP application CREDIT_RISK_BATCH',
    schedule='0 22 * * 1-5',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'riskengine'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['wait_core_for_credit'] = ExternalTaskSensor(
        task_id='wait_core_for_credit',
        external_dag_id='core_banking_eod',
        external_task_id='wait_core_for_credit',
        mode='reschedule',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:313 (application CREDIT_RISK_BATCH, job WAIT_CORE_FOR_CREDIT)',
        params={'esp_source_application': 'CREDIT_RISK_BATCH', 'esp_source_job': 'WAIT_CORE_FOR_CREDIT', 'esp_source_line': 313},
    )
    tasks['cr_extract_exposures'] = MainframeSubmitJobOperator(
        task_id='cr_extract_exposures',
        job_name='CR_EXTRACT_EXPOSURES',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:318 (application CREDIT_RISK_BATCH, job CR_EXTRACT_EXPOSURES)',
        params={'esp_source_application': 'CREDIT_RISK_BATCH', 'esp_source_job': 'CR_EXTRACT_EXPOSURES', 'esp_source_line': 318},
    )
    tasks['cr_calc_pd'] = SSHOperator(
        task_id='cr_calc_pd',
        ssh_conn_id='AIX_RISK_PROD_01',
        command='/opt/risk/bin/pd_model --model logistic --vintage 12m',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:324 (application CREDIT_RISK_BATCH, job CR_CALC_PD)',
        params={'esp_source_application': 'CREDIT_RISK_BATCH', 'esp_source_job': 'CR_CALC_PD', 'esp_source_line': 324},
    )
    tasks['cr_calc_lgd'] = SSHOperator(
        task_id='cr_calc_lgd',
        ssh_conn_id='AIX_RISK_PROD_02',
        command='/opt/risk/bin/lgd_model --recovery workout --horizon 3y',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:333 (application CREDIT_RISK_BATCH, job CR_CALC_LGD)',
        params={'esp_source_application': 'CREDIT_RISK_BATCH', 'esp_source_job': 'CR_CALC_LGD', 'esp_source_line': 333},
    )
    tasks['cr_simulate_defaults'] = SSHOperator(
        task_id='cr_simulate_defaults',
        ssh_conn_id='AIX_RISK_PROD_01',
        command='/opt/risk/bin/default_simulator --correlations /opt/risk/conf/correlation_matrix.dat',
        pool='nw_0003',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:342 (application CREDIT_RISK_BATCH, job CR_SIMULATE_DEFAULTS)',
        params={'esp_source_application': 'CREDIT_RISK_BATCH', 'esp_source_job': 'CR_SIMULATE_DEFAULTS', 'esp_source_line': 342},
    )
    tasks['cr_provision_calc'] = MainframeSubmitJobOperator(
        task_id='cr_provision_calc',
        job_name='CR_PROVISION_CALC',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:355 (application CREDIT_RISK_BATCH, job CR_PROVISION_CALC)',
        params={'esp_source_application': 'CREDIT_RISK_BATCH', 'esp_source_job': 'CR_PROVISION_CALC', 'esp_source_line': 355},
    )
    tasks['cr_risk_complete'] = EmptyOperator(
        task_id='cr_risk_complete',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:362 (application CREDIT_RISK_BATCH, job CR_RISK_COMPLETE)',
        params={'esp_source_application': 'CREDIT_RISK_BATCH', 'esp_source_job': 'CR_RISK_COMPLETE', 'esp_source_line': 362},
    )

    tasks['cr_calc_lgd'] >> tasks['cr_simulate_defaults']
    tasks['cr_calc_pd'] >> tasks['cr_simulate_defaults']
    tasks['cr_extract_exposures'] >> tasks['cr_calc_lgd']
    tasks['cr_extract_exposures'] >> tasks['cr_calc_pd']
    tasks['cr_provision_calc'] >> tasks['cr_risk_complete']
    tasks['cr_simulate_defaults'] >> tasks['cr_provision_calc']
    tasks['wait_core_for_credit'] >> tasks['cr_extract_exposures']
