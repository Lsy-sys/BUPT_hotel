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
    ) -> DetailRecord:
        factor = current_app.config.get("TIME_ACCELERATION_FACTOR", 1.0)
        try:
            factor = float(factor)
        except (TypeError, ValueError):
            factor = 1.0
        factor = factor if factor > 0 else 1.0

        scaled_duration = max(
            1, int(((end_time - start_time).total_seconds() / 60.0) * factor)
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
        )
        db.session.add(detail)
        db.session.commit()
        return detail

    def getBillDetailsByRoomIdAndTimeRange(
        self, room_id: int, start: datetime, end: datetime, customer_id: int | None = None
    ) -> List[DetailRecord]:
        query = DetailRecord.query.filter(
            DetailRecord.room_id == room_id,
            DetailRecord.start_time >= start,
            DetailRecord.end_time <= end,
        )
        # 如果提供了customer_id，只返回该客户的账单详情（排除管理员开启的空调产生的账单）
        if customer_id is not None:
            query = query.filter(DetailRecord.customer_id == customer_id)
        return query.order_by(DetailRecord.start_time).all()

