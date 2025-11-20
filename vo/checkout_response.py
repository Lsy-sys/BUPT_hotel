from dataclasses import dataclass, field
from typing import List


@dataclass
class DetailBill:
    roomId: int
    startTime: str
    endTime: str
    duration: int
    fanSpeed: str
    currentFee: float
    fee: float


@dataclass
class BillResponse:
    roomId: int
    checkinTime: str
    checkoutTime: str
    duration: str
    roomFee: float
    acFee: float


@dataclass
class CustomerInfo:
    name: str
    idCard: str | None
    phoneNumber: str | None


@dataclass
class CheckoutResponse:
    customer: CustomerInfo | None = None
    detailBill: List[DetailBill] = field(default_factory=list)
    bill: BillResponse | None = None

    def to_dict(self) -> dict:
        return {
            "customer": self.customer.__dict__ if self.customer else None,
            "detailBill": [detail.__dict__ for detail in self.detailBill],
            "bill": self.bill.__dict__ if self.bill else None,
        }

