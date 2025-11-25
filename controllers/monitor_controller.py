from flask import Blueprint, jsonify

from ..services import ac, room_service, scheduler

monitor_bp = Blueprint("monitor", __name__, url_prefix="/api/monitor")


@monitor_bp.get("/roomstatus")
def getRoomStatus():
    from ..services import customer_service
    
    rooms = room_service.getAllRooms()
    result = []
    for room in rooms:
        ac_state = ac.getACByRoomId(room.id)
        customer = customer_service.getCustomerByRoomId(room.id) if room.status == "OCCUPIED" else None
        
        # 获取队列状态信息
        try:
            ac_status = scheduler.RequestState(room.id)
            queue_state = ac_status.get("queueState", "IDLE")
        except:
            queue_state = "IDLE"
        
        status = {
            "roomId": room.id,
            "roomStatus": room.status,
            "currentTemp": room.current_temp,
            "defaultTemp": room.default_temp,
            "targetTemp": ac_state.target_temp if ac_state else None,
            "fanSpeed": ac_state.fan_speed if ac_state else None,
            "mode": ac_state.ac_mode if ac_state else None,
            "acOn": ac_state.ac_on if ac_state else False,
            "queueState": queue_state,
            "customerName": customer.name if customer else (room.customer_name if room.status == "OCCUPIED" else None),
            "customerIdCard": customer.id_card if customer else None,
            "customerPhone": customer.phone_number if customer else None,
            "checkInTime": (customer.check_in_time.isoformat() + 'Z') if customer and customer.check_in_time else None,
        }
        result.append(status)
    return jsonify(result)


@monitor_bp.get("/queuestatus")
def getQueueStatus():
    from datetime import datetime

    now = datetime.utcnow()

    serving = [
        {
            "roomId": req.roomId,
            "fanSpeed": req.fanSpeed,
            "servingTime": req.servingTime.isoformat() if req.servingTime else None,
            "servingSeconds": (now - req.servingTime).total_seconds()
            if req.servingTime
            else 0,
        }
        for req in scheduler.getServingQueue()
    ]
    waiting = [
        {
            "roomId": req.roomId,
            "fanSpeed": req.fanSpeed,
            "waitingTime": req.waitingTime.isoformat() if req.waitingTime else None,
            "waitingSeconds": (now - req.waitingTime).total_seconds()
            if req.waitingTime
            else 0,
        }
        for req in scheduler.getWaitingQueue()
    ]
    return jsonify({"servingQueue": serving, "waitingQueue": waiting})

