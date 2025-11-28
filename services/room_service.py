from typing import List, Optional

from ..extensions import db
from ..models import Room


class RoomService:
    def getAllRooms(self) -> List[Room]:
        return Room.query.order_by(Room.id).all()

    def getRoomById(self, room_id: int) -> Optional[Room]:
        return Room.query.get(room_id)

    def updateRoom(self, room: Room) -> Room:
        db.session.add(room)
        db.session.commit()
        return room

    def getAvailableRoomIds(self) -> List[int]:
        return [room.id for room in self.getAllRooms() if room.status == "AVAILABLE"]

    def ensureRoomsInitialized(self, total_count: int, default_temp: float) -> None:
        existing = {room.id for room in self.getAllRooms()}
        need_create = [idx for idx in range(1, total_count + 1) if idx not in existing]
        if not need_create:
            return
        for room_id in need_create:
            room = Room(
                id=room_id,
                status="AVAILABLE",
                current_temp=default_temp,
                target_temp=default_temp,
                default_temp=default_temp,
                fan_speed="MEDIUM",
                daily_rate=100.0,  # 默认日房费 100元/天
            )
            db.session.add(room)
        db.session.commit()

