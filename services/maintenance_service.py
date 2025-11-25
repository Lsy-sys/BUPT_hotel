from __future__ import annotations

from datetime import datetime

from ..models import Room
from .room_service import RoomService
from .scheduler import Scheduler


class MaintenanceService:
    def __init__(
        self, room_service: RoomService, scheduler: Scheduler
    ):
        self.room_service = room_service
        self.scheduler = scheduler

    def mark_room_offline(self, room_id: int) -> Room:
        room = self.room_service.getRoomById(room_id)
        if room is None:
            raise ValueError("房间不存在")
        # 已入住房间不能标记为维修，必须先退房
        if room.status == "OCCUPIED":
            raise ValueError("已入住房间不能标记为维修，请先办理退房")
        if room.ac_on:
            self.scheduler.PowerOff(room_id)
        room.status = "MAINTENANCE"
        room.customer_name = None
        room.current_temp = room.default_temp
        room.ac_session_start = None
        room.waiting_start_time = None
        room.serving_start_time = None
        return self.room_service.updateRoom(room)

    def mark_room_online(self, room_id: int) -> Room:
        room = self.room_service.getRoomById(room_id)
        if room is None:
            raise ValueError("房间不存在")
        if room.status != "MAINTENANCE":
            return room
        room.status = "AVAILABLE"
        room.customer_name = None
        room.ac_on = False
        room.ac_session_start = None
        room.waiting_start_time = None
        room.serving_start_time = None
        room.update_time = datetime.utcnow()
        return self.room_service.updateRoom(room)

    def force_rebalance(self) -> dict:
        return self.scheduler.forceTimeSliceCheck()

    def simulate_temperature(self) -> dict:
        return self.scheduler.simulateTemperatureUpdate()

