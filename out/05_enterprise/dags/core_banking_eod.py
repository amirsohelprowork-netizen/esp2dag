"""Generated from CA ESP application 'CORE_BANKING_EOD'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='core_banking_eod',
    description='ESP application CORE_BANKING_EOD',
    schedule='30 18 * * 1-5',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['cb_cutoff_transactions'] = MainframeSubmitJobOperator(
        task_id='cb_cutoff_transactions',
        job_name='CB_CUTOFF_TRANSACTIONS',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:41 (application CORE_BANKING_EOD, job CB_CUTOFF_TRANSACTIONS)',
        params={'esp_source_application': 'CORE_BANKING_EOD', 'esp_source_job': 'CB_CUTOFF_TRANSACTIONS', 'esp_source_line': 41},
    )
    tasks['cb_post_debits'] = MainframeSubmitJobOperator(
        task_id='cb_post_debits',
        job_name='CB_POST_DEBITS',
        ccchk='(0,4)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:49 (application CORE_BANKING_EOD, job CB_POST_DEBITS)',
        params={'esp_source_application': 'CORE_BANKING_EOD', 'esp_source_job': 'CB_POST_DEBITS', 'esp_source_line': 49},
    )
    tasks['cb_post_credits'] = MainframeSubmitJobOperator(
        task_id='cb_post_credits',
        job_name='CB_POST_CREDITS',
        ccchk='(0,4)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:55 (application CORE_BANKING_EOD, job CB_POST_CREDITS)',
        params={'esp_source_application': 'CORE_BANKING_EOD', 'esp_source_job': 'CB_POST_CREDITS', 'esp_source_line': 55},
    )
    tasks['cb_update_balances'] = MainframeSubmitJobOperator(
        task_id='cb_update_balances',
        job_name='CB_UPDATE_BALANCES',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:61 (application CORE_BANKING_EOD, job CB_UPDATE_BALANCES)',
        params={'esp_source_application': 'CORE_BANKING_EOD', 'esp_source_job': 'CB_UPDATE_BALANCES', 'esp_source_line': 61},
    )
    tasks['cb_calc_interest'] = MainframeSubmitJobOperator(
        task_id='cb_calc_interest',
        job_name='CB_CALC_INTEREST',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:72 (application CORE_BANKING_EOD, job CB_CALC_INTEREST)',
        params={'esp_source_application': 'CORE_BANKING_EOD', 'esp_source_job': 'CB_CALC_INTEREST', 'esp_source_line': 72},
    )
    tasks['cb_calc_fees'] = MainframeSubmitJobOperator(
        task_id='cb_calc_fees',
        job_name='CB_CALC_FEES',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:77 (application CORE_BANKING_EOD, job CB_CALC_FEES)',
        params={'esp_source_application': 'CORE_BANKING_EOD', 'esp_source_job': 'CB_CALC_FEES', 'esp_source_line': 77},
    )
    tasks['cb_apply_charges'] = MainframeSubmitJobOperator(
        task_id='cb_apply_charges',
        job_name='CB_APPLY_CHARGES',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:82 (application CORE_BANKING_EOD, job CB_APPLY_CHARGES)',
        params={'esp_source_application': 'CORE_BANKING_EOD', 'esp_source_job': 'CB_APPLY_CHARGES', 'esp_source_line': 82},
    )
    tasks['cb_revalue_accounts'] = MainframeSubmitJobOperator(
        task_id='cb_revalue_accounts',
        job_name='CB_REVALUE_ACCOUNTS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:91 (application CORE_BANKING_EOD, job CB_REVALUE_ACCOUNTS)',
        params={'esp_source_application': 'CORE_BANKING_EOD', 'esp_source_job': 'CB_REVALUE_ACCOUNTS', 'esp_source_line': 91},
    )
    tasks['cb_fx_revaluation'] = MainframeSubmitJobOperator(
        task_id='cb_fx_revaluation',
        job_name='CB_FX_REVALUATION',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:96 (application CORE_BANKING_EOD, job CB_FX_REVALUATION)',
        params={'esp_source_application': 'CORE_BANKING_EOD', 'esp_source_job': 'CB_FX_REVALUATION', 'esp_source_line': 96},
    )
    tasks['cb_regulatory_extract'] = MainframeSubmitJobOperator(
        task_id='cb_regulatory_extract',
        job_name='CB_REGULATORY_EXTRACT',
        ccchk='(0)',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:102 (application CORE_BANKING_EOD, job CB_REGULATORY_EXTRACT)',
        params={'esp_source_application': 'CORE_BANKING_EOD', 'esp_source_job': 'CB_REGULATORY_EXTRACT', 'esp_source_line': 102},
    )
    tasks['cb_generate_statements'] = MainframeSubmitJobOperator(
        task_id='cb_generate_statements',
        job_name='CB_GENERATE_STATEMENTS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:112 (application CORE_BANKING_EOD, job CB_GENERATE_STATEMENTS)',
        params={'esp_source_application': 'CORE_BANKING_EOD', 'esp_source_job': 'CB_GENERATE_STATEMENTS', 'esp_source_line': 112},
    )
    tasks['cb_eod_complete'] = EmptyOperator(
        task_id='cb_eod_complete',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\05_enterprise_production.esp:117 (application CORE_BANKING_EOD, job CB_EOD_COMPLETE)',
        params={'esp_source_application': 'CORE_BANKING_EOD', 'esp_source_job': 'CB_EOD_COMPLETE', 'esp_source_line': 117},
    )

    tasks['cb_apply_charges'] >> tasks['cb_fx_revaluation']
    tasks['cb_apply_charges'] >> tasks['cb_revalue_accounts']
    tasks['cb_calc_fees'] >> tasks['cb_apply_charges']
    tasks['cb_calc_interest'] >> tasks['cb_apply_charges']
    tasks['cb_cutoff_transactions'] >> tasks['cb_post_credits']
    tasks['cb_cutoff_transactions'] >> tasks['cb_post_debits']
    tasks['cb_fx_revaluation'] >> tasks['cb_regulatory_extract']
    tasks['cb_post_credits'] >> tasks['cb_update_balances']
    tasks['cb_post_debits'] >> tasks['cb_update_balances']
    tasks['cb_regulatory_extract'] >> tasks['cb_eod_complete']
    tasks['cb_regulatory_extract'] >> tasks['cb_generate_statements']
    tasks['cb_revalue_accounts'] >> tasks['cb_regulatory_extract']
    tasks['cb_update_balances'] >> tasks['cb_calc_fees']
    tasks['cb_update_balances'] >> tasks['cb_calc_interest']
