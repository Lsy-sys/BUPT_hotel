from .ac_service import AC
from .bill_detail_service import BillDetailService
from .bill_service import AccommodationFeeBillService
from .customer_service import CustomerService
from .hotel_service import FrontDesk
from .maintenance_service import MaintenanceService
from .report_service import ReportService
from .room_service import RoomService
from .scheduler import Scheduler

room_service = RoomService()
customer_service = CustomerService()
bill_detail_service = BillDetailService()
accommodation_fee_bill_service = AccommodationFeeBillService()
scheduler = Scheduler(room_service, bill_detail_service)
ac = AC(room_service, scheduler)
maintenance_service = MaintenanceService(room_service, scheduler)
report_service = ReportService()
front_desk = FrontDesk(
    room_service=room_service,
    customer_service=customer_service,
    accommodation_fee_bill_service=accommodation_fee_bill_service,
    bill_detail_service=bill_detail_service,
)

