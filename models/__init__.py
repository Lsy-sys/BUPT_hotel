from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from ..extensions import db


class TimestampMixin:
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Room(db.Model, TimestampMixin):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default="AVAILABLE", nullable=False)
    current_temp = db.Column(db.Float, default=32.0)
    target_temp = db.Column(db.Float)
    ac_on = db.Column(db.Boolean, default=False)
    ac_mode = db.Column(db.String(20), default="COOLING")
    fan_speed = db.Column(db.String(20), default="MEDIUM")
    default_temp = db.Column(db.Float, default=25.0)
    check_in_time = db.Column(db.DateTime)
    ac_session_start = db.Column(db.DateTime)
    last_temp_update = db.Column(db.DateTime)
    assigned_ac_number = db.Column(db.Integer)
    customer_name = db.Column(db.String(50))
    waiting_start_time = db.Column(db.DateTime)
    serving_start_time = db.Column(db.DateTime)
    cooling_paused = db.Column(db.Boolean, default=False)  # 是否因达到目标温度而暂停服务
    pause_start_temp = db.Column(db.Float)  # 暂停时的温度（用于判断是否回温1℃）
    daily_rate = db.Column(db.Float, default=100.0)  # 房间日房费（元/天）

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "currentTemp": self.current_temp,
            "targetTemp": self.target_temp,
            "acOn": self.ac_on,
            "acMode": self.ac_mode,
            "fanSpeed": self.fan_speed,
            "defaultTemp": self.default_temp,
        }

    def updateState(self, state: str) -> None:
        self.status = state

    def setAccommodationDays(self, days: int) -> None:
        self.check_in_days = days

    def associateDetailRecords(self, records: List["DetailRecord"]) -> None:
        self._detail_records = records  # type: ignore[attr-defined]

    def associateCustomer(self, customer: "Customer") -> None:
        self.customer_name = customer.name


class Customer(db.Model, TimestampMixin):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    id_card = db.Column(db.String(20))
    phone_number = db.Column(db.String(20))
    current_room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"))
    check_in_time = db.Column(db.DateTime)
    check_out_time = db.Column(db.DateTime)
    check_in_days = db.Column(db.Integer)
    status = db.Column(db.String(20), default="CHECKED_IN")

    room = db.relationship("Room", backref=db.backref("customers", lazy=True))


class AccommodationFeeBill(db.Model, TimestampMixin):
    __tablename__ = "bills"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"))
    check_in_time = db.Column(db.DateTime, nullable=False)
    check_out_time = db.Column(db.DateTime, nullable=False)
    stay_days = db.Column(db.Integer, nullable=False)
    room_fee = db.Column(db.Float, default=0.0)
    ac_total_fee = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), nullable=False, default="UNPAID")
    paid_time = db.Column(db.DateTime)
    cancelled_time = db.Column(db.DateTime)
    print_status = db.Column(db.String(20), nullable=False, default="NOT_PRINTED")
    print_time = db.Column(db.DateTime)

    customer = db.relationship("Customer", backref=db.backref("bills", lazy=True))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "roomId": self.room_id,
            "customerId": self.customer_id,
            "checkInTime": self.check_in_time.isoformat() if self.check_in_time else None,
            "checkOutTime": self.check_out_time.isoformat()
            if self.check_out_time
            else None,
            "stayDays": self.stay_days,
            "roomFee": self.room_fee,
            "acFee": self.ac_total_fee,
            "totalAmount": self.total_amount,
            "status": self.status,
            "paidTime": self.paid_time.isoformat() if self.paid_time else None,
            "cancelledTime": self.cancelled_time.isoformat()
            if self.cancelled_time
            else None,
            "printStatus": self.print_status,
            "printTime": self.print_time.isoformat() if self.print_time else None,
            "createdAt": self.create_time.isoformat() if self.create_time else None,
            "updatedAt": self.update_time.isoformat() if self.update_time else None,
        }

    @staticmethod
    def calculate_Accommodation_Fee(days: int, daily_fee: float) -> float:
        if days <= 0:
            return 0.0
        return round(days * daily_fee, 2)


class DetailRecord(db.Model, TimestampMixin):
    __tablename__ = "bill_details"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, nullable=False)
    customer_id = db.Column(db.Integer)
    ac_mode = db.Column(db.String(20))
    fan_speed = db.Column(db.String(20))
    request_time = db.Column(db.DateTime, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    cost = db.Column(db.Float, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    detail_type = db.Column(db.String(50), default="AC")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "roomId": self.room_id,
            "customerId": self.customer_id,
            "acMode": self.ac_mode,
            "fanSpeed": self.fan_speed,
            "requestTime": self.request_time.isoformat()
            if self.request_time
            else None,
            "startTime": self.start_time.isoformat() if self.start_time else None,
            "endTime": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "cost": self.cost,
            "rate": self.rate,
            "detailType": self.detail_type,
        }


class ACConfig(db.Model):
    __tablename__ = "ac_config"

    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.String(20), nullable=False)
    min_temp = db.Column(db.Float, nullable=False)
    max_temp = db.Column(db.Float, nullable=False)
    default_temp = db.Column(db.Float, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    low_speed_rate = db.Column(db.Float, nullable=False)
    mid_speed_rate = db.Column(db.Float, nullable=False)
    high_speed_rate = db.Column(db.Float, nullable=False)
    default_speed = db.Column(db.String(2), nullable=False)


@dataclass
class RoomRequest:
    roomId: int
    fanSpeed: str
    mode: str = "COOLING"
    targetTemp: Optional[float] = None
    servingTime: Optional[datetime] = None
    waitingTime: Optional[datetime] = None
    requestTime: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ACFeeBill:
    room_id: int
    detail_records: List[DetailRecord] = field(default_factory=list)

    def calculate_AC_Fee(self, overrides: Optional[List[DetailRecord]] = None) -> float:
        records = overrides if overrides is not None else self.detail_records
        return round(sum(record.cost for record in records), 2)


@dataclass
class AccommodationOrder:
    customer_id: int
    room_id: int
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DepositReceipt:
    customer_id: int
    room_id: int
    amount: float
    issued_at: datetime = field(default_factory=datetime.utcnow)

