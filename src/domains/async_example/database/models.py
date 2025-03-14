from typing import Optional

from sqlalchemy import Column, Integer, String, ForeignKey, func, DateTime
from sqlalchemy.orm import Mapped, relationship

from src.database.database import Base


class AsyncExample(Base):
    __tablename__ = "async_examples"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(255), index=True)
    description: Mapped[str] = Column(String(255), index=True)
    create_date: Mapped[DateTime] = Column(DateTime, index=True, default=func.now())
    modify_date: Mapped[Optional[DateTime]] = Column(DateTime, index=True, onupdate=func.now())
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", backref="async_example_users")


class RelatedAsyncExample(Base):
    __tablename__ = "related_to_async_examples"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(255), index=True)
    description: Mapped[str] = Column(String(255), index=True)
    create_date: Mapped[DateTime] = Column(DateTime, index=True, default=func.now())
    modify_date: Mapped[Optional[DateTime]] = Column(DateTime, index=True, onupdate=func.now())
    async_example_id: Mapped[int] = Column(Integer, ForeignKey("async_examples.id"), nullable=True)

    async_example = relationship("AsyncExample", backref="async_another_example")


class DerivedFromAsyncExample(Base):
    __tablename__ = "derived_from_async_examples"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(255), index=True)
    description: Mapped[str] = Column(String(255), index=True)
    create_date: Mapped[DateTime] = Column(DateTime, index=True, default=func.now())
    modify_date: Mapped[Optional[DateTime]] = Column(DateTime, index=True, onupdate=func.now())
    async_example_id: Mapped[int] = Column(Integer, ForeignKey("async_examples.id"), nullable=True)

    async_example = relationship("AsyncExample", backref="derived_from_async_example")
