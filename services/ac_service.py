from __future__ import annotations

from typing import Optional

from ..models import Room
from .room_service import RoomService
from .scheduler import Scheduler


class AC:
    def __init__(self, room_service: RoomService, scheduler: Scheduler):
        self.room_service = room_service
        self.scheduler = scheduler

    def getACByRoomId(self, room_id: int) -> Optional[Room]:
        return self.room_service.getRoomById(room_id)

    def PowerOn(self, RoomId: int, CurrentRoomTemp: float | None) -> str:
        return self.scheduler.PowerOn(RoomId, CurrentRoomTemp)

    def PowerOff(self, RoomId: int) -> str:
        return self.scheduler.PowerOff(RoomId)

    def ChangeTemp(self, RoomId: int, TargetTemp: float) -> str:
        return self.scheduler.ChangeTemp(RoomId, TargetTemp)

    def ChangeSpeed(self, RoomId: int, FanSpeed: str) -> str:
        return self.scheduler.ChangeSpeed(RoomId, FanSpeed)

    def RequestState(self, RoomId: int) -> dict:
        return self.scheduler.RequestState(RoomId)

