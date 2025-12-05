from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from flask import current_app
from ..models import (
    AccommodationFeeBill,
    AccommodationOrder,
    Customer,
    DetailRecord,
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
        if room.ac_on:
            from ..services import scheduler
            try:
                # 这会触发结算，生成 "POWER_OFF_CYCLE" 记录，并清理内存队列
                scheduler.PowerOff(room_id)
            except Exception as e:
                # 防止调度器错误阻碍退房，但记录日志
                print(f"Error powering off AC during checkout: {e}")
                import traceback
                traceback.print_exc()
        
        # 重新获取房间对象（因为 PowerOff 可能已经更新了状态）
        room = self.room_service.getRoomById(room_id)
        
        # 清除所有客户相关信息
        room.status = "AVAILABLE"
        room.customer_name = None
        room.check_in_time = None
        
        # 清除空调相关状态
        room.ac_on = False
        room.ac_session_start = None
        room.waiting_start_time = None
        room.serving_start_time = None
        room.cooling_paused = False
        room.pause_start_temp = None
        room.billing_start_temp = None
        
        # 重置温度和风速到默认值
        default_temp = room.default_temp or current_app.config.get(
            "HOTEL_DEFAULT_TEMP", 25
        )
        room.current_temp = default_temp
        room.target_temp = None
        room.fan_speed = "MEDIUM"  # 重置为默认风速
        room.last_temp_update = datetime.utcnow()
        
        # 清除分配的空调编号（如果有）
        room.assigned_ac_number = None
        
        self.room_service.updateRoom(room)

        # 与报告页面完全一致：查询该房间的所有详单
        details = DetailRecord.query.filter_by(room_id=room_id)\
            .order_by(DetailRecord.start_time.desc()).all()
        bill = self.accommodation_fee_bill_service.createAndSettleBill(details, customer, room)
        _ = DepositReceipt(customer_id=customer.id, room_id=room_id, amount=0.0)

        from ..vo.checkout_response import CustomerInfo
        
        checkout_response = CheckoutResponse()
        checkout_response.customer = CustomerInfo(
            name=customer.name,
            idCard=customer.id_card,
            phoneNumber=customer.phone_number,
        )
        # 参照测试脚本的方式获取房费和空调费数据
        from . import scheduler
        state = scheduler.RequestState(room_id)

        # 计算入住时长：房间总费 ÷ 该房间的每日费率
        room_fee_total = state.get('room_fee', 0.0)
        daily_rate = room.daily_rate if room.daily_rate and room.daily_rate > 0 else 100.0
        stay_days = room_fee_total / daily_rate if daily_rate > 0 else 0

        checkout_response.bill = BillResponse(
            roomId=bill.room_id,
            checkinTime=bill.check_in_time.date().isoformat(),
            checkoutTime=bill.check_out_time.date().isoformat(),
            duration=str(round(stay_days, 1)),
            roomFee=room_fee_total,
            acFee=state.get('ac_fee', 0.0),
        )

        # 完全复制报告页面的逻辑
        # 获取时间加速因子，用于将加速时间转换为真实物理时间
        factor = float(current_app.config.get("TIME_ACCELERATION_FACTOR", 1.0))
        if factor <= 0:
            factor = 1.0

        # 获取该房间的所有账单，计算总房费和总空调费
        all_bills = AccommodationFeeBill.query.filter_by(room_id=room_id).all()
        total_room_fee = sum(bill.room_fee for bill in all_bills)
        total_ac_fee = sum(bill.ac_total_fee for bill in all_bills)

        # 参照测试脚本的方式：只显示空调费记录，房费在汇总中显示
        checkout_response.detailBill = []
        for detail in details:
            d_type = getattr(detail, 'detail_type', 'AC')

            # 只显示空调费记录，跳过房费记录
            if d_type == 'ROOM_FEE':
                continue

            # 将加速时间转换为真实物理时间的分钟数
            real_duration = round(detail.duration / factor, 1)

            checkout_response.detailBill.append(
                DetailBill(
                    roomId=detail.room_id,
                    startTime=detail.start_time.isoformat(),
                    endTime=detail.end_time.isoformat(),
                    duration=real_duration,
                    fanSpeed=detail.fan_speed,
                    rate=detail.rate,
                    acFee=round(detail.cost, 2),
                    roomFee=0.0,  # 空调记录的房费设为0，房费在汇总中显示
                    fee=round(detail.cost, 2),  # 空调记录的总费用就是空调费
                )
        )
        
        # === 自动保存详单到本地 csv 文件夹 ===
        try:
            self._save_details_to_csv(room_id, details, check_out_time)
        except Exception as e:
            # 保存失败不影响退房流程，只记录日志
            print(f"保存详单到 CSV 失败: {e}")
            import traceback
            traceback.print_exc()
        
        return checkout_response

    def checkOut(self, room_id: int) -> CheckoutResponse:
        return self.Process_CheckOut(room_id)
    
    def _save_details_to_csv(self, room_id: int, details: List, checkout_time: datetime) -> None:
        """保存房间详单到本地 csv 文件夹"""
        # 确保 csv 文件夹存在
        csv_dir = Path("csv")
        csv_dir.mkdir(exist_ok=True)
        
        # 生成文件名：room_{room_id}_details_{timestamp}.csv
        timestamp = checkout_time.strftime("%Y%m%d_%H%M%S")
        filename = csv_dir / f"room_{room_id}_details_{timestamp}.csv"
        
        # 写入 CSV 文件
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            # 写入表头
            writer.writerow(["房间号", "客户ID", "开始时间", "结束时间", "时长(分钟)", "风速", "模式", "费率", "费用", "类型"])
            
            # 写入详单数据
            for detail in details:
                # 处理客户ID显示
                customer_id_str = str(detail.customer_id) if detail.customer_id else "管理员"
                
                # 处理记录类型显示
                d_type = getattr(detail, 'detail_type', 'AC')
                if d_type == 'POWER_OFF_CYCLE':
                    type_str = "关机结算(房费周期)"
                elif d_type == 'ROOM_FEE':
                    type_str = "房费"
                else:
                    type_str = "空调运行"
                
                writer.writerow([
                    detail.room_id,
                    customer_id_str,
                    detail.start_time.strftime("%Y-%m-%dT%H:%M:%S") if detail.start_time else "",
                    detail.end_time.strftime("%Y-%m-%dT%H:%M:%S") if detail.end_time else "",
                    detail.duration,
                    detail.fan_speed or "",
                    detail.ac_mode or "",
                    detail.rate,
                    detail.cost,
                    type_str
                ])
        
        print(f"详单已保存到: {filename}")

