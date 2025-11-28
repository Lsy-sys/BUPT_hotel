import io
import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from ..services import bill_detail_service, maintenance_service, room_service

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.post("/rooms/<int:roomId>/offline")
def take_room_offline(roomId: int):
    try:
        room = maintenance_service.mark_room_offline(roomId)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"message": "房间已标记为维修", "room": room.to_dict()})


@admin_bp.post("/rooms/<int:roomId>/online")
def bring_room_online(roomId: int):
    try:
        room = maintenance_service.mark_room_online(roomId)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"message": "房间已重新可用", "room": room.to_dict()})


@admin_bp.post("/maintenance/force-rotation")
def force_rotation():
    payload = maintenance_service.force_rebalance()
    return jsonify({"message": "调度队列已强制轮转", "schedule": payload})


@admin_bp.post("/maintenance/simulate-temperature")
def simulate_temperature():
    payload = maintenance_service.simulate_temperature()
    return jsonify(payload)


@admin_bp.post("/details/export")
def export_details():
    """生成详单并保存到本地csv文件夹，每个房间生成一张详单"""
    import csv
    
    data = request.get_json() or {}
    specified_room_id = data.get("roomId")
    if specified_room_id:
        specified_room_id = int(specified_room_id)
    
    # 查询所有详单（不限制时间范围）
    start_time = datetime.min
    end_time = datetime.utcnow()
    
    # 确定要生成详单的房间列表
    if specified_room_id:
        # 如果指定了房间号，只生成该房间的详单
        room_ids = [specified_room_id]
    else:
        # 如果没有指定房间，获取所有房间
        rooms = room_service.getAllRooms()
        room_ids = [room.id for room in rooms]
    
    # 确保csv文件夹存在
    csv_dir = Path(current_app.root_path) / "csv"
    csv_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    saved_files = []
    total_count = 0
    
    # 为每个房间生成一张详单
    for room_id in room_ids:
        # 查询该房间的详单
        details = bill_detail_service.getBillDetailsByRoomIdAndTimeRange(
            room_id=room_id,
            start=start_time,
            end=end_time,
            customer_id=None,  # 包含所有详单（包括管理员开启的）
        )
        
        # 生成CSV内容
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["房间号", "客户ID", "开始时间", "结束时间", "时长(分钟)", "风速", "模式", "费率", "费用"])
        for detail in details:
            writer.writerow(
                [
                    detail.room_id,
                    detail.customer_id if detail.customer_id else "管理员",
                    detail.start_time.isoformat() if detail.start_time else "",
                    detail.end_time.isoformat() if detail.end_time else "",
                    detail.duration,
                    detail.fan_speed,
                    detail.ac_mode,
                    detail.rate,
                    detail.cost,
                ]
            )
        csv_content = buffer.getvalue()
        buffer.close()
        
        # 生成文件名
        filename = f"room_{room_id}_details_{timestamp}.csv"
        
        # 保存文件到csv文件夹
        file_path = csv_dir / filename
        # 添加BOM以支持Excel正确显示中文
        csv_content_with_bom = "\ufeff" + csv_content
        file_path.write_text(csv_content_with_bom, encoding="utf-8-sig")
        
        saved_files.append({
            "roomId": room_id,
            "filename": filename,
            "count": len(details)
        })
        total_count += len(details)
    
    return jsonify({
        "message": f"已为 {len(room_ids)} 个房间生成详单",
        "files": saved_files,
        "totalCount": total_count
    })

