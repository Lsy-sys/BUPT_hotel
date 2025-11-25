from __future__ import annotations

import csv
import io

from flask import Blueprint, Response, jsonify

from ..services import accommodation_fee_bill_service, bill_detail_service

bill_bp = Blueprint("bill", __name__, url_prefix="/api/bills")


def _serialize_bill(bill) -> dict:
    return bill.to_dict()


@bill_bp.get("")
def list_bills():
    bills = accommodation_fee_bill_service.getAllBills()
    return jsonify([_serialize_bill(bill) for bill in bills])


@bill_bp.get("/<int:billId>")
def get_bill(billId: int):
    bill = accommodation_fee_bill_service.getBillById(billId)
    if bill is None:
        return jsonify({"error": "账单不存在"}), 404
    return jsonify(_serialize_bill(bill))


@bill_bp.get("/customer/<int:customerId>")
def get_bills_by_customer(customerId: int):
    bills = accommodation_fee_bill_service.getBillsByCustomerId(customerId)
    return jsonify([_serialize_bill(bill) for bill in bills])


@bill_bp.get("/room/<int:roomNumber>")
def get_bills_by_room_number(roomNumber: int):
    bills = accommodation_fee_bill_service.getBillsByRoomId(roomNumber)
    return jsonify([_serialize_bill(bill) for bill in bills])


@bill_bp.get("/room-id/<int:roomId>")
def get_bills_by_room_id(roomId: int):
    bills = accommodation_fee_bill_service.getBillsByRoomId(roomId)
    return jsonify([_serialize_bill(bill) for bill in bills])


@bill_bp.get("/unpaid")
def get_unpaid_bills():
    bills = accommodation_fee_bill_service.getUnpaidBills()
    return jsonify([_serialize_bill(bill) for bill in bills])


@bill_bp.post("/<int:billId>/pay")
def pay_bill(billId: int):
    try:
        bill = accommodation_fee_bill_service.markBillPaid(billId)
        return jsonify({"message": "账单已支付", "bill": _serialize_bill(bill)})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bill_bp.post("/<int:billId>/cancel")
def cancel_bill(billId: int):
    try:
        bill = accommodation_fee_bill_service.cancelBill(billId)
        return jsonify({"message": "账单已取消", "bill": _serialize_bill(bill)})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bill_bp.get("/<int:billId>/details")
def get_bill_details(billId: int):
    bill = accommodation_fee_bill_service.getBillById(billId)
    if bill is None:
        return jsonify({"error": "账单不存在"}), 404
    details = bill_detail_service.getBillDetailsByRoomIdAndTimeRange(
        room_id=bill.room_id,
        start=bill.check_in_time,
        end=bill.check_out_time,
    )
    return jsonify([detail.to_dict() for detail in details])


@bill_bp.post("/<int:billId>/print")
def print_bill(billId: int):
    bill = accommodation_fee_bill_service.getBillById(billId)
    if bill is None:
        return jsonify({"error": "账单不存在"}), 404
    details = bill_detail_service.getBillDetailsByRoomIdAndTimeRange(
        room_id=bill.room_id,
        start=bill.check_in_time,
        end=bill.check_out_time,
    )
    accommodation_fee_bill_service.markBillPrinted(billId)
    payload = accommodation_fee_bill_service.buildPrintablePayload(bill, details)
    return jsonify(payload)


@bill_bp.get("/<int:billId>/export-details")
def export_bill_details(billId: int):
    bill = accommodation_fee_bill_service.getBillById(billId)
    if bill is None:
        return jsonify({"error": "账单不存在"}), 404
    details = bill_detail_service.getBillDetailsByRoomIdAndTimeRange(
        room_id=bill.room_id,
        start=bill.check_in_time,
        end=bill.check_out_time,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["房间号", "开始时间", "结束时间", "时长(分钟)", "风速", "模式", "费率", "费用"])
    for detail in details:
        writer.writerow(
            [
                detail.room_id,
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
    filename = f"bill_{billId}_details.csv"
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

