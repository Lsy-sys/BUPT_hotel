from flask import Blueprint, jsonify, request

from ..services import room_service, scheduler

test_bp = Blueprint("test", __name__, url_prefix="/api/test")


@test_bp.post("/time-slice-check")
def trigger_time_slice_check():
    status = scheduler.forceTimeSliceCheck()
    return jsonify({"message": "时间片检查已执行", "schedule": status})


@test_bp.post("/temperature-update")
def trigger_temperature_update():
    result = scheduler.simulateTemperatureUpdate()
    return jsonify(result)


@test_bp.get("/rooms/status")
def getRoomsStatus():
    return jsonify([room.to_dict() for room in room_service.getAllRooms()])


@test_bp.get("/rooms/<int:roomId>/status")
def getRoomStatus(roomId: int):
    room = room_service.getRoomById(roomId)
    if room is None:
        return jsonify({"error": "房间不存在"}), 404
    return jsonify(room.to_dict())


@test_bp.post("/rooms/<int:roomId>/temperature")
def setRoomTemperature(roomId: int):
    temperature = request.args.get("temperature", type=float)
    room = room_service.getRoomById(roomId)
    if room is None:
        return jsonify({"error": "房间不存在"}), 404
    room.current_temp = temperature
    room_service.updateRoom(room)
    return jsonify({"message": f"房间{roomId}温度已设置为{temperature:.1f}度"})


@test_bp.post("/reset")
def resetSystem():
    for room in room_service.getAllRooms():
        room.ac_on = False
        room.status = "AVAILABLE"
        room.customer_name = None
        room.ac_session_start = None
        room.current_temp = room.default_temp + 7
        room.target_temp = room.default_temp
        room.waiting_start_time = None
        room.serving_start_time = None
        room_service.updateRoom(room)
    return jsonify({"message": "系统状态已重置"})

