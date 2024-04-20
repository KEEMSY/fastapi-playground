from typing import Optional

from sqlalchemy import Integer, Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship, Mapped

from src.database import Base
from src.domains.user.models import User  # Adjust the path according to your project structure


class SyncExample(Base):
    __tablename__ = "sync_example"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(255), index=True)
    description: Mapped[str] = Column(String(255), index=True)
    create_date: Mapped[DateTime] = Column(DateTime, index=True, default=func.now())
    modify_date: Mapped[Optional[DateTime]] = Column(DateTime, index=True, onupdate=func.now())
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", backref="example_users")
