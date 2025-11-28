from datetime import datetime
from typing import Dict, List, Optional

from flask import current_app

from ..extensions import db
from ..models import ACFeeBill, AccommodationFeeBill, Customer, DetailRecord, Room


class AccommodationFeeBillService:
    def createAndSettleBill(
        self, bill_details: List[DetailRecord], customer: Customer, room: Room
    ) -> AccommodationFeeBill:
        if not customer.check_in_time:
            customer.check_in_time = datetime.utcnow()
        if not customer.check_out_time:
            customer.check_out_time = datetime.utcnow()

        stay_days = max(
            1, (customer.check_out_time.date() - customer.check_in_time.date()).days or 1
        )
        # 优先使用房间的 daily_rate，如果为空则使用全局配置
        daily_rate = (
            room.daily_rate
            if room.daily_rate is not None
            else current_app.config["BILLING_ROOM_RATE"]
        )

        charge_units = stay_days
        if current_app.config.get("ENABLE_AC_CYCLE_DAILY_FEE"):
            cycle_days = len(bill_details)
            charge_units = max(stay_days, cycle_days)

        room_fee = AccommodationFeeBill.calculate_Accommodation_Fee(
            charge_units, daily_rate
        )
        ac_fee = ACFeeBill(room_id=room.id, detail_records=bill_details).calculate_AC_Fee()

        bill = AccommodationFeeBill(
            room_id=room.id,
            customer_id=customer.id,
            check_in_time=customer.check_in_time,
            check_out_time=customer.check_out_time,
            stay_days=stay_days,
            room_fee=room_fee,
            ac_total_fee=ac_fee,
            total_amount=room_fee + ac_fee,
            status="UNPAID",
        )
        db.session.add(bill)
        db.session.commit()
        return bill

    def getCurrentFeeDetail(self, room: Room) -> Dict[str, float]:
        """计算房间当前实时房费（基础房费 + 空调费），不落库"""
        # 获取日房费
        daily_rate = (
            room.daily_rate
            if room.daily_rate is not None and room.daily_rate > 0
            else current_app.config.get("BILLING_ROOM_RATE", 100.0)
        )
        
        # 调试信息
        print(f"[DEBUG] 房间 {room.id}: daily_rate={room.daily_rate}, 使用值={daily_rate}")

        from ..services import bill_detail_service

        # 查询所有历史详单（包括管理员开启的，不过滤customer_id）
        details = bill_detail_service.getBillDetailsByRoomIdAndTimeRange(
            room_id=room.id,
            start=datetime.min,
            end=datetime.utcnow(),
            customer_id=None,  # 不过滤customer_id，包含所有详单
        )
        # 计算历史详单费用
        ac_fee = sum(detail.cost for detail in details)
        print(f"[DEBUG] 房间 {room.id}: 历史详单数量={len(details)}, 历史费用={ac_fee}")
        
        # 如果空调正在运行，计算当前会话的费用
        # 注意：当前会话还未关闭，所以不计入 AC 周期数
        if room.ac_on and room.ac_session_start:
            now = datetime.utcnow()
            factor = current_app.config.get("TIME_ACCELERATION_FACTOR", 1.0)
            try:
                factor = float(factor)
            except (TypeError, ValueError):
                factor = 1.0
            factor = factor if factor > 0 else 1.0
            
            # 计算当前会话的时长（分钟，考虑时间加速）
            elapsed_seconds = (now - room.ac_session_start).total_seconds()
            elapsed_minutes = max(1, int((elapsed_seconds / 60.0) * factor))
            
            # 获取费率
            fan_speed = room.fan_speed or "MEDIUM"
            if fan_speed == "HIGH":
                rate = current_app.config.get("BILLING_AC_RATE_HIGH", 1.5)
            elif fan_speed == "MEDIUM":
                rate = current_app.config.get("BILLING_AC_RATE_MEDIUM", 1.0)
            else:
                rate = current_app.config.get("BILLING_AC_RATE_LOW", 0.5)
            
            # 计算当前会话费用
            current_session_fee = rate * elapsed_minutes
            ac_fee += current_session_fee
            print(f"[DEBUG] 房间 {room.id}: 当前会话时长={elapsed_minutes}分钟, 费率={rate}, 当前会话费用={current_session_fee}, 总空调费={ac_fee}")
        else:
            print(f"[DEBUG] 房间 {room.id}: 空调未开启或没有会话开始时间 (ac_on={room.ac_on}, ac_session_start={room.ac_session_start})")
        
        # 如果启用了 AC 周期计费，房费应该基于 AC 周期数计算
        room_fee = daily_rate
        if current_app.config.get("ENABLE_AC_CYCLE_DAILY_FEE"):
            # 计算 AC 周期数（已关闭的完整周期）
            cycle_days = len(details)
            # 如果当前有正在运行的会话，也计入一个周期（因为管理员开启也算）
            if room.ac_on and room.ac_session_start:
                cycle_days += 1
            # 房费 = max(1天, AC周期数) * 日房费
            room_fee = max(1, cycle_days) * daily_rate
            print(f"[DEBUG] 房间 {room.id}: AC周期数={cycle_days}, 计算房费={room_fee}")
        
        result = {"roomFee": room_fee, "acFee": round(ac_fee, 2), "total": round(room_fee + ac_fee, 2)}
        print(f"[DEBUG] 房间 {room.id}: 最终结果={result}")
        return result

    def getAllBills(self) -> List[AccommodationFeeBill]:
        return AccommodationFeeBill.query.order_by(AccommodationFeeBill.create_time.desc()).all()

    def getBillById(self, bill_id: int) -> Optional[AccommodationFeeBill]:
        return AccommodationFeeBill.query.get(bill_id)

    def getBillsByRoomId(self, room_id: int) -> List[AccommodationFeeBill]:
        return (
            AccommodationFeeBill.query.filter_by(room_id=room_id)
            .order_by(AccommodationFeeBill.create_time.desc())
            .all()
        )

    def getBillsByCustomerId(self, customer_id: int) -> List[AccommodationFeeBill]:
        return (
            AccommodationFeeBill.query.filter_by(customer_id=customer_id)
            .order_by(AccommodationFeeBill.create_time.desc())
            .all()
        )

    def getUnpaidBills(self) -> List[AccommodationFeeBill]:
        return (
            AccommodationFeeBill.query.filter_by(status="UNPAID")
            .order_by(AccommodationFeeBill.create_time.desc())
            .all()
        )

    def markBillPaid(self, bill_id: int) -> AccommodationFeeBill:
        bill = self.getBillById(bill_id)
        if bill is None:
            raise ValueError("账单不存在")
        if bill.status == "CANCELLED":
            raise ValueError("账单已取消，无法支付")
        if bill.status == "PAID":
            return bill
        bill.status = "PAID"
        bill.paid_time = datetime.utcnow()
        db.session.add(bill)
        db.session.commit()
        return bill

    def cancelBill(self, bill_id: int) -> AccommodationFeeBill:
        bill = self.getBillById(bill_id)
        if bill is None:
            raise ValueError("账单不存在")
        if bill.status == "PAID":
            raise ValueError("账单已支付，无法取消")
        if bill.status == "CANCELLED":
            return bill
        bill.status = "CANCELLED"
        bill.cancelled_time = datetime.utcnow()
        db.session.add(bill)
        db.session.commit()
        return bill

    def markBillPrinted(self, bill_id: int) -> AccommodationFeeBill:
        bill = self.getBillById(bill_id)
        if bill is None:
            raise ValueError("账单不存在")
        bill.print_status = "PRINTED"
        bill.print_time = datetime.utcnow()
        db.session.add(bill)
        db.session.commit()
        return bill

    def buildPrintablePayload(
        self, bill: AccommodationFeeBill, details: List[DetailRecord]
    ) -> Dict[str, object]:
        return {
            "bill": bill.to_dict(),
            "detailItems": [
                {
                    "startTime": detail.start_time.isoformat() if detail.start_time else None,
                    "endTime": detail.end_time.isoformat() if detail.end_time else None,
                    "durationMinutes": detail.duration,
                    "fanSpeed": detail.fan_speed,
                    "mode": detail.ac_mode,
                    "rate": detail.rate,
                    "cost": detail.cost,
                }
                for detail in details
            ],
            "totals": {
                "acDurationMinutes": sum(detail.duration for detail in details),
                "acFee": sum(detail.cost for detail in details),
                "roomFee": bill.room_fee,
                "grandTotal": bill.total_amount,
            },
        }

