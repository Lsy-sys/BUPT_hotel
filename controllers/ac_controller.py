from flask import Blueprint, jsonify, request

from ..services import scheduler

ac_bp = Blueprint("ac", __name__, url_prefix="/api/ac")


@ac_bp.post("/room/<int:roomId>/start")
def PowerOn(roomId: int):
    current_temp = request.args.get("currentTemp", type=float)
    try:
        message = scheduler.PowerOn(roomId, current_temp)
        return jsonify({"message": message})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@ac_bp.post("/room/<int:roomId>/stop")
def PowerOff(roomId: int):
    try:
        message = scheduler.PowerOff(roomId)
        return jsonify({"message": message})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@ac_bp.put("/room/<int:roomId>/temp")
def ChangeTemp(roomId: int):
    target_temp = request.args.get("targetTemp", type=float)
    if target_temp is None:
        return jsonify({"error": "targetTemp 不能为空"}), 400
    try:
        message = scheduler.ChangeTemp(roomId, target_temp)
        return jsonify({"message": message})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@ac_bp.put("/room/<int:roomId>/speed")
def ChangeSpeed(roomId: int):
    fan_speed = request.args.get("fanSpeed")
    if not fan_speed:
        return jsonify({"error": "fanSpeed 不能为空"}), 400
    try:
        message = scheduler.ChangeSpeed(roomId, fan_speed)
        return jsonify({"message": message})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@ac_bp.get("/room/<int:roomId>/detail")
def getRoomACDetail(roomId: int):
    try:
        data = scheduler.getRoomACAccumulatedData(roomId)
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@ac_bp.get("/room/<int:roomId>/status")
def RequestState(roomId: int):
    try:
        data = scheduler.RequestState(roomId)
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@ac_bp.get("/schedule/status")
def getScheduleStatus():
    data = scheduler.getScheduleStatus()
    return jsonify(data)
