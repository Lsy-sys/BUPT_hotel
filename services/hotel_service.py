from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ..models import (
    AccommodationOrder,
    Customer,
    DepositReceipt,
    Room,
)
from ..vo.checkout_response import BillResponse, CheckoutResponse, DetailBill
from .bill_detail_service import BillDetailService
from .bill_service import AccommodationFeeBillService
from .customer_service import CustomerService
from .room_service import RoomService


class FrontDesk:
    def __init__(
        self,
        room_service: RoomService,
        customer_service: CustomerService,
        accommodation_fee_bill_service: AccommodationFeeBillService,
        bill_detail_service: BillDetailService,
    ):
        self.room_service = room_service
        self.customer_service = customer_service
        self.accommodation_fee_bill_service = accommodation_fee_bill_service
        self.bill_detail_service = bill_detail_service
        self._latest_order: Optional[AccommodationOrder] = None

    def getAvailableRooms(self) -> List[Room]:
        return [
            room
            for room in self.Check_RoomState(None)
            if room.status == "AVAILABLE"
        ]

    def Check_RoomState(self, date: datetime | None) -> List[Room]:
        # 当前实现未基于日期筛选，预留扩展点
        return self.room_service.getAllRooms()

    def Regist_CustomerInfo(
        self, Cust_id: str, Cust_name: str, number: str, date: datetime | None = None
    ) -> Customer:
        if not Cust_name:
            raise ValueError("客户姓名不能为空")
        if not Cust_id:
            raise ValueError("客户证件号不能为空")
        if not number:
            raise ValueError("联系电话不能为空")
        customer = Customer(
            name=Cust_name,
            id_card=Cust_id,
            phone_number=number,
            check_in_time=date or datetime.utcnow(),
            status="REGISTERED",
        )
        return self.customer_service.saveCustomer(customer)

    def _prepare_room_for_checkin(self, room_id: int) -> Room:
        room = self.room_service.getRoomById(room_id)
        if room is None:
            raise ValueError("房间不存在")
        if room.status != "AVAILABLE":
            raise ValueError("房间当前不可用")
        if room.ac_on:
            from ..services import scheduler

            scheduler.PowerOff(room_id)
            from ..models import DetailRecord
            from ..extensions import db

            DetailRecord.query.filter(
                DetailRecord.room_id == room_id,
                DetailRecord.customer_id.is_(None),
            ).delete()
            db.session.commit()
        return room

    def Create_Accommodation_Order(self, Customer_id: int, Room_id: int) -> str:
        customer = self.customer_service.getCustomerById(Customer_id)
        if customer is None:
            raise ValueError("客户不存在")
        room = self._prepare_room_for_checkin(Room_id)
        customer.current_room_id = room.id
        customer.status = "CHECKED_IN"
        customer.check_in_time = customer.check_in_time or datetime.utcnow()
        self.customer_service.updateCustomer(customer)
        room.updateState("OCCUPIED")
        room.associateCustomer(customer)
        room.check_in_time = customer.check_in_time
        self.room_service.updateRoom(room)
        self._latest_order = AccommodationOrder(
            customer_id=customer.id,
            room_id=room.id,
        )
        return "入住成功"

    def checkIn(self, payload: Dict) -> str:
        room_id = payload.get("roomId")
        if room_id is None:
            raise ValueError("roomId 不能为空")
        customer = self.Regist_CustomerInfo(
            Cust_id=payload.get("idCard"),
            Cust_name=payload.get("name"),
            number=payload.get("phoneNumber"),
            date=datetime.utcnow(),
        )
        return self.Create_Accommodation_Order(customer.id, room_id)

    def Process_CheckOut(self, Room_id: int) -> CheckoutResponse:
        room_id = Room_id
        customer = self.customer_service.getCustomerByRoomId(room_id)
        if customer is None:
            # 如果没有入住记录，检查房间状态
            room = self.room_service.getRoomById(room_id)
            if room and room.ac_on:
                # 如果空调开启但没有入住记录，可能是管理员开启的，关闭空调并清理状态
                from ..services import scheduler
                try:
                    scheduler.PowerOff(room_id)
                except:
                    pass
                room.status = "AVAILABLE"
                room.customer_name = None
                room.ac_on = False
                room.ac_session_start = None
                self.room_service.updateRoom(room)
            raise ValueError("房间没有入住记录，无法办理退房")

        check_out_time = datetime.utcnow()
        customer.check_out_time = check_out_time
        customer.status = "CHECKED_OUT"
        customer.current_room_id = None
        self.customer_service.updateCustomer(customer)

        room = self.room_service.getRoomById(room_id)
        room.status = "AVAILABLE"
        room.customer_name = None
        room.ac_on = False
        room.ac_session_start = None
        self.room_service.updateRoom(room)

        details = self.bill_detail_service.getBillDetailsByRoomIdAndTimeRange(
            room_id=room_id,
            start=customer.check_in_time,
            end=check_out_time,
            customer_id=customer.id,  # 只计算该客户的账单详情，排除管理员开启的空调产生的账单
        )
        bill = self.accommodation_fee_bill_service.createAndSettleBill(details, customer, room)
        _ = DepositReceipt(customer_id=customer.id, room_id=room_id, amount=0.0)

        from ..vo.checkout_response import CustomerInfo
        
        checkout_response = CheckoutResponse()
        checkout_response.customer = CustomerInfo(
            name=customer.name,
            idCard=customer.id_card,
            phoneNumber=customer.phone_number,
        )
        checkout_response.detailBill = [
            DetailBill(
                roomId=detail.room_id,
                startTime=detail.start_time.isoformat(),
                endTime=detail.end_time.isoformat(),
                duration=detail.duration,
                fanSpeed=detail.fan_speed,
                currentFee=detail.cost,
                fee=detail.cost,
            )
            for detail in details
        ]
        checkout_response.bill = BillResponse(
            roomId=bill.room_id,
            checkinTime=bill.check_in_time.date().isoformat(),
            checkoutTime=bill.check_out_time.date().isoformat(),
            duration=str(bill.stay_days),
            roomFee=bill.room_fee,
            acFee=bill.ac_total_fee,
        )
        return checkout_response

    def checkOut(self, room_id: int) -> CheckoutResponse:
        return self.Process_CheckOut(room_id)

