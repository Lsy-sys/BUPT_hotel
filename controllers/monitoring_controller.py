import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, jsonify, Response
from ..services import room_service, scheduler, customer_service
from ..models import DetailRecord

# 监控端控制器
monitoring_bp = Blueprint("monitoring", __name__, url_prefix="/manager")

@monitoring_bp.route("/monitoring")
def monitoring_page():
    """监控页面"""
    return render_template("monitoring.html")

@monitoring_bp.route("/monitoring/data")
def get_monitoring_data():
    """获取所有房间的监控数据"""
    try:
        # 获取所有房间
        rooms = room_service.getAllRooms()

        # 为每个房间获取详细信息
        data = []
        for room in rooms:
            state = scheduler.RequestState(room.id)
            data.append({
                "room_id": state.get("room_id", room.id),
                "current_temp": state.get("current_temp", 25.0),
                "target_temp": state.get("target_temp", 25.0),
                "fan_speed": state.get("fan_speed", "MEDIUM"),
                "ac_mode": state.get("ac_mode", "COOLING"),
                "ac_on": state.get("ac_on", False),
                "current_fee": state.get("ac_fee", 0.0),  # 当前费用（未结算）
                "total_fee": state.get("total_cost", 0.0),  # 累计费用（含房费）
                "schedule_count": state.get("schedule_count", 0),
                "queue_state": state.get("state", "OFF")
            })

        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

@monitoring_bp.route("/monitoring/export")
def export_monitoring_details():
    """导出所有房间的监控状态"""
    try:
        # 获取所有房间的监控数据（与前端显示的数据一致）
        rooms = room_service.getAllRooms()

        # 使用 utf-8-sig 方便 Excel 打开不乱码
        si = io.StringIO()
        writer = csv.writer(si)

        # 写入表头
        writer.writerow([
            "客户姓名",
            "客户ID",
            "房间号",
            "当前温度(°C)",
            "目标温度(°C)",
            "风速",
            "模式",
            "空调状态",
            "当前费用(元)",
            "累计费用(元)",
            "调度次数",
            "队列状态"
        ])

        # 写入房间数据
        for room in rooms:
            state = scheduler.RequestState(room.id)

            # 处理客户信息
            customer_id = state.get("customer_id", None)
            customer_name = "管理员"
            customer_id_str = "管理员"

            if customer_id is not None:
                try:
                    customer = customer_service.getCustomerById(customer_id)
                    if customer:
                        customer_name = customer.name
                        customer_id_str = str(customer_id)
                    else:
                        customer_name = f"客户{customer_id}"
                        customer_id_str = str(customer_id)
                except:
                    customer_name = f"客户{customer_id}"
                    customer_id_str = str(customer_id)

            # 处理空调状态
            ac_on = state.get("ac_on", False)
            ac_status = "开启" if ac_on else "关闭"

            # 处理队列状态
            queue_state = state.get("state", "OFF")
            queue_status_map = {
                "SERVING": "服务中",
                "WAITING": "等待中",
                "PAUSED": "暂停",
                "OFF": "离线"
            }
            queue_status = queue_status_map.get(queue_state, queue_state)

            writer.writerow([
                customer_name,  # 客户姓名（第一列）
                customer_id_str,  # 客户ID
                state.get("room_id", room.id),
                round(state.get("current_temp", 25.0), 1),
                state.get("target_temp", 25.0),
                state.get("fan_speed", "MEDIUM"),
                state.get("ac_mode", "COOLING"),
                ac_status,
                round(state.get("ac_fee", 0.0), 2),
                round(state.get("total_cost", 0.0), 2),
                state.get("schedule_count", 0),
                queue_status
            ])

        output = si.getvalue()
        # 转换编码
        output_bytes = output.encode("utf-8-sig")

        # 生成带时间戳的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"monitoring_status_{timestamp}.csv"

        return Response(
            output_bytes,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"},
        )

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
