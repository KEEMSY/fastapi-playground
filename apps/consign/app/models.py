from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Item(Base):
    """위탁 상품. 판매자가 맡기고, 팔리면 수수료를 뗀 금액을 정산받는다."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str]
    price: Mapped[int]  # 원 단위 정수. 돈에 float 를 쓰지 않는다
    commission_rate: Mapped[int]  # 퍼센트 정수 (예: 30 = 30%)
    status: Mapped[str] = mapped_column(default="ON_SALE")  # ON_SALE | SOLD


# 시각은 전부 timestamptz. 시간대 없는 timestamp 는 UTC 인지 KST 인지 값만 봐선 알 수 없고,
# 화면·다른 서비스가 제각각 해석해 9시간씩 어긋난다(이 콘솔에서 실제로 겪었다)


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique: 같은 상품이 두 번 팔리는 것을 DB 가 마지막으로 막는다
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), unique=True)
    sold_price: Mapped[int]
    settlement_amount: Mapped[int]  # 판매 시점의 수수료율로 확정해 저장한다 — 나중에 요율이 바뀌어도 과거 정산이 흔들리지 않게
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Outbox(Base):
    """다른 서비스로 보낼 이벤트. 판매와 같은 트랜잭션에 쓰므로 "판매는 됐는데 이벤트는 사라짐"이 없다.

    DB 커밋과 메시지 발행을 따로 하면 둘 중 하나만 성공할 수 있다(이중 쓰기 문제).
    여기 쓰고 나서 relay 가 Redis 로 옮긴다.
    """

    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str]
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
