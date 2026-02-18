from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from src.domains.answer.models import Answer
from src.domains.question.models import Question
from src.domains.question.schemas import QuestionCreate, QuestionUpdate
from src.domains.user.models import User
from src.domains.notification import service as notification_service


# offset: 시작 위치, limit: 가져올 데이터 수
async def get_question_list(db: AsyncSession, offset: int = 0, limit: int = 10, keyword: str = ''):
    query = select(Question)
    if keyword:
        search = '%%{}%%'.format(keyword)
        sub_query = select(Answer.question_id, Answer.content, User.username) \
            .outerjoin(User, Answer.user_id == User.id).subquery()
        query = query \
            .outerjoin(User) \
            .outerjoin(sub_query, sub_query.c.question_id == Question.id) \
            .filter(Question.subject.ilike(search) |  # 질문제목
                    Question.content.ilike(search) |  # 질문내용
                    User.username.ilike(search) |  # 질문작성자
                    sub_query.c.content.ilike(search) |  # 답변내용
                    sub_query.c.username.ilike(search)  # 답변작성자
                    )
    total = await db.execute(select(func.count()).select_from(query))
    question_list = await db.execute(query.offset(offset).limit(limit)
                                     .order_by(Question.create_date.desc())
                                     .distinct()
                                     .options(selectinload(Question.answers).selectinload(Answer.voter))
                                     .options(selectinload(Question.answers).selectinload(Answer.user))
                                     .options(selectinload(Question.user))
                                     .options(selectinload(Question.voter))
                                     )
    return total.scalar_one(), question_list.scalars().fetchall()  # (전체 건수, 페이징 적용된 질문 목록)


async def get_question(db: AsyncSession, question_id: int):
    stmt = (
        select(Question)
        .where(Question.id == question_id)
        .options(
            selectinload(Question.user),
            selectinload(Question.voter),
            selectinload(Question.answers).selectinload(Answer.user),
            selectinload(Question.answers).selectinload(Answer.voter)
        )
    )
    result = await db.execute(stmt)
    question = result.scalars().one_or_none()
    return question


async def create_question(db: AsyncSession, question_create: QuestionCreate, user: User):
    db_question = Question(subject=question_create.subject,
                           content=question_create.content,
                           create_date=datetime.now(),
                           user=user)
    db.add(db_question)
    await db.commit()


async def update_question(db: AsyncSession, question_model: Question, question_update: QuestionUpdate):
    question_model.subject = question_update.subject
    question_model.content = question_update.content
    question_model.modify_date = datetime.now()
    db.add(question_model)
    await db.commit()


async def delete_question(db: AsyncSession, question_model: Question):
    await db.delete(question_model)
    await db.commit()


async def vote_question(db: AsyncSession, question_model: Question, db_user: User):
    question_model.voter.append(db_user)
    await db.commit()

    # 알림 생성
    await notification_service.create_notification(
        db=db,
        user_id=question_model.user_id,
        actor_user_id=db_user.id,
        event_type="question_voted",
        resource_type="question",
        resource_id=question_model.id,
        message=f"{db_user.username}님이 회원님의 질문에 투표했습니다.",
    )
