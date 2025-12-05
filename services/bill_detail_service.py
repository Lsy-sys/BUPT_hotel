from datetime import datetime
from typing import List

from flask import current_app

from ..extensions import db
from ..models import DetailRecord


class BillDetailService:
    def createBillDetail(
        self,
        room_id: int,
        ac_mode: str,
        fan_speed: str,
        start_time: datetime,
        end_time: datetime,
        rate: float,
        cost: float,
        customer_id: int | None = None,
        detail_type: str = "AC",
    ) -> DetailRecord:
        # === 防重复检查：在添加之前再次检查是否存在 ===
        # 这可以防止并发调用时创建重复记录
        # 强制刷新数据库会话，确保查询到最新提交的数据
        from ..extensions import db
        db.session.expire_all()
        existing = DetailRecord.query.filter(
            DetailRecord.room_id == room_id,
            DetailRecord.detail_type == detail_type,
            DetailRecord.start_time == start_time
        ).first()
        
        if existing:
            print(f"[BillDetailService] 发现已存在的详单，Room {room_id}, start_time={start_time}, existing_id={existing.id}, 跳过创建")
            return existing
        
        factor = current_app.config.get("TIME_ACCELERATION_FACTOR", 1.0)
        try:
            factor = float(factor)
        except (TypeError, ValueError):
            factor = 1.0
        factor = factor if factor > 0 else 1.0

        scaled_duration = max(
            0, int(((end_time - start_time).total_seconds() / 60.0) * factor)
        )

        detail = DetailRecord(
            room_id=room_id,
            customer_id=customer_id,
            ac_mode=ac_mode,
            fan_speed=fan_speed,
            request_time=start_time,
            start_time=start_time,
            end_time=end_time,
            duration=scaled_duration,
            rate=rate,
            cost=cost,
            detail_type=detail_type,
        )
        db.session.add(detail)
        db.session.commit()
        return detail

    def getBillDetailsByRoomIdAndTimeRange(
        self, room_id: int, start: datetime, end: datetime, customer_id: int | None = None
    ) -> List[DetailRecord]:
        # === 关键修复：使用更宽松的查询条件，确保查询到所有相关费用 ===
        # 使用 start_time < end + 1秒，或者使用 end_time <= end + 1秒
        # 这样可以确保所有在时间范围内的记录都被查询到，即使时间精度有微小差异
        from datetime import timedelta
        query_end = end + timedelta(seconds=1)  # 添加1秒缓冲，确保查询到所有费用
        query = DetailRecord.query.filter(
            DetailRecord.room_id == room_id,
            DetailRecord.start_time >= start,
            DetailRecord.start_time < query_end,  # 使用 < 而不是 <=，并添加缓冲时间
        )
        # 如果提供了customer_id，只返回该客户的账单详情（排除管理员开启的空调产生的账单）
        if customer_id is not None:
            query = query.filter(DetailRecord.customer_id == customer_id)
        return query.order_by(DetailRecord.start_time).all()

