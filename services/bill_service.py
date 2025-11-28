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
        # 兜底费率
        daily_rate = 100.0
        if room.daily_rate is not None and room.daily_rate > 0:
            daily_rate = room.daily_rate
        else:
            daily_rate = current_app.config.get("BILLING_ROOM_RATE", 100.0)

        charge_units = stay_days
        if current_app.config.get("ENABLE_AC_CYCLE_DAILY_FEE"):
            cycle_days = sum(1 for d in bill_details if getattr(d, 'detail_type', 'AC') == 'POWER_OFF_CYCLE')
            if bill_details:
                cycle_days = max(1, cycle_days)
            else:
                cycle_days = 0
            charge_units = max(stay_days, cycle_days)

        room_fee = float(charge_units) * float(daily_rate)
        
        ac_fee_bill = ACFeeBill(room_id=room.id, detail_records=bill_details)
        ac_fee = ac_fee_bill.calculate_AC_Fee()

        bill = AccommodationFeeBill(
            room_id=room.id,
            customer_id=customer.id,
            check_in_time=customer.check_in_time,
            check_out_time=customer.check_out_time,
            stay_days=charge_units,
            room_fee=room_fee,
            ac_total_fee=ac_fee,
            total_amount=room_fee + ac_fee,
            status="UNPAID",
        )
        db.session.add(bill)
        db.session.commit()
        return bill

    def getCurrentFeeDetail(self, room: Room) -> Dict[str, float]:
        """计算房间当前实时房费（基础房费 + 空调费）"""

        daily_rate = 100.0
        if room.daily_rate is not None and room.daily_rate > 0:
            daily_rate = room.daily_rate
        else:
            daily_rate = current_app.config.get("BILLING_ROOM_RATE", 100.0)
        
        # 1. 累加数据库里已结算的历史详单费用
        from ..services import bill_detail_service
        details = bill_detail_service.getBillDetailsByRoomIdAndTimeRange(
            room_id=room.id,
            start=datetime.min,
            end=datetime.utcnow(),
            customer_id=None,
        )
        ac_fee = sum(detail.cost for detail in details)
        
        # 2. 计算当前正在进行的片段 (Pending Cost)
        current_session_fee = 0.0
        
        # === 核心修复：只有 serving_start_time 存在时，说明正在吹风，才计算实时费用 ===
        # 如果是 PAUSED 或 WAITING，serving_start_time 是 None，这里就不会进，费用就不会涨
        if room.ac_on and room.serving_start_time:
            now = datetime.utcnow()
            factor = current_app.config.get("TIME_ACCELERATION_FACTOR", 1.0)
            
            # 使用 serving_start_time 计算当前片段时长
            elapsed_seconds = (now - room.serving_start_time).total_seconds()
            elapsed_minutes = max(1, int((elapsed_seconds / 60.0) * factor))
            
            # 费率逻辑
            fan_speed = (room.fan_speed or "MEDIUM").upper()
            if fan_speed == "HIGH": rate = 1.0
            elif fan_speed == "MEDIUM": rate = 0.5
            else: rate = 1.0 / 3.0
            
            current_session_fee = rate * elapsed_minutes
            ac_fee += current_session_fee
        # ===================================================================
        
        # 3. 计算房费 (Cycle Logic)
        cycle_days = 1 
        if current_app.config.get("ENABLE_AC_CYCLE_DAILY_FEE"):
            history_cycles = sum(1 for d in details if getattr(d, 'detail_type', 'AC') == 'POWER_OFF_CYCLE')
            cycle_days = history_cycles
            if room.ac_on:
                cycle_days += 1
            cycle_days = max(1, cycle_days)
            
        room_fee = float(cycle_days) * float(daily_rate)
        
        return {
            "roomFee": room_fee,
            "acFee": round(ac_fee, 2),
            "total": round(room_fee + ac_fee, 2),
            "current_session_fee": round(current_session_fee, 2),
            "total_fee": round(ac_fee, 2) 
        }

    # ... (Getter 方法保持不变) ...
    def getAllBills(self) -> List[AccommodationFeeBill]:
        return AccommodationFeeBill.query.order_by(AccommodationFeeBill.create_time.desc()).all()

    def getBillById(self, bill_id: int) -> Optional[AccommodationFeeBill]:
        return AccommodationFeeBill.query.get(bill_id)

    def getBillsByRoomId(self, room_id: int) -> List[AccommodationFeeBill]:
        return AccommodationFeeBill.query.filter_by(room_id=room_id).order_by(AccommodationFeeBill.create_time.desc()).all()

    def getBillsByCustomerId(self, customer_id: int) -> List[AccommodationFeeBill]:
        return AccommodationFeeBill.query.filter_by(customer_id=customer_id).order_by(AccommodationFeeBill.create_time.desc()).all()

    def getUnpaidBills(self) -> List[AccommodationFeeBill]:
        return AccommodationFeeBill.query.filter_by(status="UNPAID").order_by(AccommodationFeeBill.create_time.desc()).all()

    def markBillPaid(self, bill_id: int) -> AccommodationFeeBill:
        bill = self.getBillById(bill_id)
        if bill and bill.status != "CANCELLED" and bill.status != "PAID":
            bill.status = "PAID"; bill.paid_time = datetime.utcnow(); db.session.add(bill); db.session.commit()
        return bill

    def cancelBill(self, bill_id: int) -> AccommodationFeeBill:
        bill = self.getBillById(bill_id)
        if bill and bill.status != "PAID" and bill.status != "CANCELLED":
            bill.status = "CANCELLED"; bill.cancelled_time = datetime.utcnow(); db.session.add(bill); db.session.commit()
        return bill

    def markBillPrinted(self, bill_id: int) -> AccommodationFeeBill:
        bill = self.getBillById(bill_id)
        if bill:
            bill.print_status = "PRINTED"; bill.print_time = datetime.utcnow(); db.session.add(bill); db.session.commit()
        return bill

    def buildPrintablePayload(self, bill: AccommodationFeeBill, details: List[DetailRecord]) -> Dict[str, object]:
        return {
            "bill": bill.to_dict(),
            "detailItems": [{
                "startTime": d.start_time.isoformat() if d.start_time else None,
                "endTime": d.end_time.isoformat() if d.end_time else None,
                "duration": d.duration, "fanSpeed": d.fan_speed, "mode": d.ac_mode, "rate": d.rate, "cost": d.cost
            } for d in details],
            "totals": {
                "acDurationMinutes": sum(d.duration for d in details),
                "acFee": sum(d.cost for d in details),
                "roomFee": bill.room_fee, "grandTotal": bill.total_amount
            }
        }
