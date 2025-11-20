from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, text

from ..extensions import db
from ..models import ACConfig

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def execute_schema_sql() -> None:
    sql_text = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [stmt.strip() for stmt in sql_text.split(";") if stmt.strip()]
    for statement in statements:
        db.session.execute(text(statement))
    db.session.commit()


def seed_default_ac_config() -> None:
    if ACConfig.query.count() > 0:
        return
    configs = [
        ACConfig(
            id=1,
            mode="COOLING",
            min_temp=18.0,
            max_temp=28.0,
            default_temp=25.0,
            rate=1.0,
            low_speed_rate=0.5,
            mid_speed_rate=1.0,
            high_speed_rate=1.5,
            default_speed="M",
        ),
        ACConfig(
            id=2,
            mode="HEATING",
            min_temp=20.0,
            max_temp=30.0,
            default_temp=26.0,
            rate=1.2,
            low_speed_rate=0.6,
            mid_speed_rate=1.1,
            high_speed_rate=1.6,
            default_speed="M",
        ),
    ]
    db.session.add_all(configs)
    db.session.commit()


def ensure_bill_detail_update_time_column() -> None:
    inspector = inspect(db.engine)
    columns = {column["name"] for column in inspector.get_columns("bill_details")}
    if "update_time" in columns:
        return
    db.session.execute(
        text(
            """
            ALTER TABLE bill_details
            ADD COLUMN update_time DATETIME
            DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP
            """
        )
    )
    db.session.commit()


def ensure_room_last_temp_update_column() -> None:
    """确保rooms表有last_temp_update字段"""
    inspector = inspect(db.engine)
    try:
        # 检查表是否存在
        if "rooms" not in inspector.get_table_names():
            # 表不存在，会在create_all时创建，不需要手动添加字段
            return
        
        columns = {column["name"] for column in inspector.get_columns("rooms")}
        if "last_temp_update" in columns:
            return
        
        # 表存在但字段不存在，添加字段
        db.session.execute(
            text(
                """
                ALTER TABLE rooms
                ADD COLUMN last_temp_update DATETIME
                """
            )
        )
        db.session.commit()
    except Exception as e:
        # 如果出错，回滚并打印错误（但不中断程序）
        db.session.rollback()
        print(f"警告：添加last_temp_update字段时出错: {e}")
        # 如果字段已存在或其他非致命错误，继续执行