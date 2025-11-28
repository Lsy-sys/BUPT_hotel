from flask import Blueprint, jsonify, current_app

from ..services import ac, room_service, scheduler, bill_service

monitor_bp = Blueprint("monitor", __name__, url_prefix="/api/monitor")


@monitor_bp.get("/roomstatus")
def getRoomStatus():
    from ..services import customer_service
    
    rooms = room_service.getAllRooms()
    result = []
    time_slice = current_app.config["HOTEL_TIME_SLICE"]
    for room in rooms:
        ac_state = ac.getACByRoomId(room.id)
        customer = customer_service.getCustomerByRoomId(room.id) if room.status == "OCCUPIED" else None
        
        # 获取队列状态信息
        try:
            ac_status = scheduler.RequestState(room.id)
            queue_state = ac_status.get("queueState", "IDLE")
            waiting_seconds = ac_status.get("waitingSeconds", 0.0)
            serving_seconds = ac_status.get("servingSeconds", 0.0)
            queue_position = ac_status.get("queuePosition")
        except:
            queue_state = "IDLE"
            waiting_seconds = 0.0
            serving_seconds = 0.0
            queue_position = None
        
        # 计算实时房费
        try:
            bill_info = bill_service.getCurrentFeeDetail(room)
        except Exception as e:
            # 调试：打印异常信息
            import traceback
            print(f"计算房间 {room.id} 费用时出错: {e}")
            traceback.print_exc()
            bill_info = {"roomFee": 0.0, "acFee": 0.0, "total": 0.0}

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
            "waitingSeconds": waiting_seconds,
            "servingSeconds": serving_seconds,
            "queuePosition": queue_position,
            "timeSlice": time_slice,
            "roomFee": bill_info["roomFee"],
            "acFee": bill_info["acFee"],
            "totalFee": bill_info["total"],
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

