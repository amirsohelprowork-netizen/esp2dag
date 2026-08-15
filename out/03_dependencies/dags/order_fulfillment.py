"""Generated from CA ESP application 'ORDER_FULFILLMENT'."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG
from custom_operators.mainframe import MainframeSubmitJobOperator

with DAG(
    dag_id='order_fulfillment',
    description='ESP application ORDER_FULFILLMENT',
    schedule='0 7 * * *',
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={'owner': 'maestro'},
    tags=['esp'],
) as dag:
    tasks = {}
    tasks['pick_orders'] = MainframeSubmitJobOperator(
        task_id='pick_orders',
        job_name='PICK_ORDERS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:214 (application ORDER_FULFILLMENT, job PICK_ORDERS)',
        params={'esp_source_application': 'ORDER_FULFILLMENT', 'esp_source_job': 'PICK_ORDERS', 'esp_source_line': 214},
    )
    tasks['pack_orders_zone_a'] = MainframeSubmitJobOperator(
        task_id='pack_orders_zone_a',
        job_name='PACK_ORDERS_ZONE_A',
        pool='nw_0002',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:222 (application ORDER_FULFILLMENT, job PACK_ORDERS_ZONE_A)',
        params={'esp_source_application': 'ORDER_FULFILLMENT', 'esp_source_job': 'PACK_ORDERS_ZONE_A', 'esp_source_line': 222},
    )
    tasks['pack_orders_zone_b'] = MainframeSubmitJobOperator(
        task_id='pack_orders_zone_b',
        job_name='PACK_ORDERS_ZONE_B',
        pool='nw_0002',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:228 (application ORDER_FULFILLMENT, job PACK_ORDERS_ZONE_B)',
        params={'esp_source_application': 'ORDER_FULFILLMENT', 'esp_source_job': 'PACK_ORDERS_ZONE_B', 'esp_source_line': 228},
    )
    tasks['ship_orders'] = MainframeSubmitJobOperator(
        task_id='ship_orders',
        job_name='SHIP_ORDERS',
        doc_md='ESP source: C:\\Users\\amirs\\ESP2DAG\\data\\samples\\03_dependencies_and_triggers.esp:234 (application ORDER_FULFILLMENT, job SHIP_ORDERS)',
        params={'esp_source_application': 'ORDER_FULFILLMENT', 'esp_source_job': 'SHIP_ORDERS', 'esp_source_line': 234},
    )

    tasks['pack_orders_zone_a'] >> tasks['ship_orders']
    tasks['pack_orders_zone_b'] >> tasks['ship_orders']
    tasks['pick_orders'] >> tasks['pack_orders_zone_a']
    tasks['pick_orders'] >> tasks['pack_orders_zone_b']
