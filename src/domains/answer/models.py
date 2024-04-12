from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from src.database import Base

"""
question = relationship("Question", backref="answers")

- relationship 은 두 테이블 간의 관계를 나타낸다.
  - 첫번째 파라미터: 참조할 모델명
  - backref: 역참조 설정 ex. Question 객체 A에서 A.answers로 A에 달린 답변을 참조
"""


class Answer(Base):
    __tablename__ = "answer"

    id = Column(Integer, primary_key=True)
    content = Column(String(255), nullable=False)
    create_date = Column(DateTime, nullable=False)
    modify_date = Column(DateTime, nullable=True)
    question_id = Column(Integer, ForeignKey("question.id"))
    question = relationship("Question", backref="answers")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", backref="answer_users")
