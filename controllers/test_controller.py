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


@test_bp.post("/rooms/<int:roomId>/init-temp")
def initRoomTemperature(roomId: int):
    """初始化房间温度：同时设置default_temp和current_temp（不修改target_temp）"""
    temperature = request.args.get("temperature", type=float)
    if temperature is None:
        return jsonify({"error": "temperature参数不能为空"}), 400
    
    room = room_service.getRoomById(roomId)
    if room is None:
        return jsonify({"error": "房间不存在"}), 404
    
    # 同时设置default_temp和current_temp，确保温度不会自动变化
    # 注意：不修改target_temp，target_temp是空调属性，默认值为25℃
    room.default_temp = temperature
    room.current_temp = temperature
    # target_temp保持原值或使用默认值25℃，不在这里修改
    if room.target_temp is None:
        room.target_temp = 25.0  # 如果为None，设置为默认值25℃
    room.last_temp_update = None  # 清除温度更新时间，避免自动变化
    room_service.updateRoom(room)
    return jsonify({
        "message": f"房间{roomId}温度已初始化：default_temp={temperature:.1f}℃, current_temp={temperature:.1f}℃, target_temp={room.target_temp:.1f}℃",
        "defaultTemp": temperature,
        "currentTemp": temperature,
        "targetTemp": room.target_temp
    })


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

