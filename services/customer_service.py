from datetime import datetime
from typing import Optional

from ..extensions import db
from ..models import Customer


class CustomerService:
    def saveCustomer(self, customer: Customer) -> Customer:
        db.session.add(customer)
        db.session.commit()
        return customer

    def updateCustomer(self, customer: Customer) -> Customer:
        customer.update_time = datetime.utcnow()
        db.session.add(customer)
        db.session.commit()
        return customer

    def getCustomerById(self, customer_id: int) -> Optional[Customer]:
        return Customer.query.get(customer_id)

    def getCustomerByRoomId(self, room_id: int) -> Optional[Customer]:
        return Customer.query.filter_by(current_room_id=room_id, status="CHECKED_IN").first()

