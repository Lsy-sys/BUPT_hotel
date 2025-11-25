from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from flask import current_app

from ..models import AccommodationFeeBill, DetailRecord, Room


class ReportService:
    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _build_time_filters(self, query, start: Optional[str], end: Optional[str]):
        start_dt = self._parse_datetime(start)
        end_dt = self._parse_datetime(end)
        if start_dt:
            query = query.filter(Bill.check_in_time >= start_dt)
        if end_dt:
            query = query.filter(Bill.check_out_time <= end_dt)
        return query

    def get_overview(self, start: Optional[str], end: Optional[str]) -> Dict[str, object]:
        total_rooms = Room.query.count()
        occupied_rooms = Room.query.filter_by(status="OCCUPIED").count()
        maintenance_rooms = Room.query.filter_by(status="MAINTENANCE").count()

        bill_query = AccommodationFeeBill.query
        bill_query = self._build_time_filters(bill_query, start, end)
        bills: List[AccommodationFeeBill] = bill_query.all()

        room_revenue = sum(bill.room_fee for bill in bills)
        ac_revenue = sum(bill.ac_total_fee for bill in bills)
        total_revenue = sum(bill.total_amount for bill in bills)
        occupancy_rate = (occupied_rooms / total_rooms) if total_rooms else 0.0

        return {
            "timeRange": {"start": start, "end": end},
            "roomStats": {
                "total": total_rooms,
                "occupied": occupied_rooms,
                "maintenance": maintenance_rooms,
                "occupancyRate": round(occupancy_rate, 3),
            },
            "revenue": {
                "roomFee": room_revenue,
                "acFee": ac_revenue,
                "total": total_revenue,
            },
            "billing": {
                "billCount": len(bills),
                "avgAcFee": round(ac_revenue / len(bills), 2) if bills else 0.0,
            },
        }

    def get_ac_usage_summary(
        self, start: Optional[str], end: Optional[str]
    ) -> Dict[str, object]:
        detail_query = DetailRecord.query
        start_dt = self._parse_datetime(start)
        end_dt = self._parse_datetime(end)
        if start_dt:
            detail_query = detail_query.filter(DetailRecord.start_time >= start_dt)
        if end_dt:
            detail_query = detail_query.filter(DetailRecord.end_time <= end_dt)

        details: List[DetailRecord] = detail_query.all()
        grouped_duration: Dict[str, int] = defaultdict(int)
        grouped_cost: Dict[str, float] = defaultdict(float)
        for detail in details:
            speed = (detail.fan_speed or "LOW").upper()
            grouped_duration[speed] += detail.duration
            grouped_cost[speed] += detail.cost

        return {
            "timeRange": {"start": start, "end": end},
            "totalSessions": len(details),
            "totalDurationMinutes": sum(detail.duration for detail in details),
            "totalCost": sum(detail.cost for detail in details),
            "byFanSpeed": [
                {
                    "fanSpeed": speed,
                    "durationMinutes": grouped_duration[speed],
                    "cost": grouped_cost[speed],
                }
                for speed in sorted(grouped_duration.keys())
            ],
        }

    def get_daily_revenue(self, days: int = 7) -> List[Dict[str, object]]:
        if days <= 0:
            raise ValueError("days 必须大于 0")

        rows: List[tuple] = (
            AccommodationFeeBill.query.with_entities(
                AccommodationFeeBill.check_out_time,
                AccommodationFeeBill.room_fee,
                AccommodationFeeBill.ac_total_fee,
            )
            .filter(AccommodationFeeBill.check_out_time != None)  # noqa: E711
            .order_by(AccommodationFeeBill.check_out_time.desc())
            .limit(days * current_app.config.get("HOTEL_ROOM_COUNT", 5))
            .all()
        )
        buckets: Dict[str, Dict[str, float]] = defaultdict(lambda: {"roomFee": 0.0, "acFee": 0.0})
        for checkout_time, room_fee, ac_fee in rows:
            if checkout_time is None:
                continue
            key = checkout_time.date().isoformat()
            buckets[key]["roomFee"] += room_fee or 0.0
            buckets[key]["acFee"] += ac_fee or 0.0

        result = []
        for date_key in sorted(buckets.keys(), reverse=True)[:days]:
            entry = buckets[date_key]
            result.append(
                {
                    "date": date_key,
                    "roomFee": round(entry["roomFee"], 2),
                    "acFee": round(entry["acFee"], 2),
                    "total": round(entry["roomFee"] + entry["acFee"], 2),
                }
            )
        return list(reversed(result))

