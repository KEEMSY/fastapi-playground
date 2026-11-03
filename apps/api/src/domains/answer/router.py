from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from src.database.database import get_db
from src.domains.answer.schemas import AnswerCreate, Answer, AnswerUpdate, AnswerDelete, AnswerVote
from src.domains.answer import service as answer_service
from src.domains.question import service as question_service
from src.domains.user.router import get_current_user_with_sync
from src.domains.user.schemas import User
from src.domains.notification import service as notification_service

router = APIRouter(
    prefix="/api/answer",
)


@router.post("/create/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def answer_create(
        question_id: int,
        _answer_create: AnswerCreate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user_with_sync)
):
    # create answer
    question = question_service.get_question_sync(db, question_id=question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    answer_service.create_answer(db, question=question, answer_create=_answer_create, user=current_user)

    # 알림 생성
    notification_service.create_notification_sync(
        db=db,
        user_id=question.user_id,
        actor_user_id=current_user.id,
        event_type="answer_created",
        resource_type="question",
        resource_id=question_id,
        message=f"{current_user.username}님이 회원님의 질문에 답변했습니다.",
    )


@router.get("/detail/{answer_id}", response_model=Answer)
def answer_detail(answer_id: int, db: Session = Depends(get_db)):
    answer = answer_service.get_answer_by_id(db, answer_id=answer_id)

    # 존재하지 않는 답변을 조회할 경우 404 에러를 반환한다.
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    return answer


@router.put("/update", status_code=status.HTTP_204_NO_CONTENT)
def answer_update(_answer_update: AnswerUpdate,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user_with_sync)):
    """
    답변 수정
    answer_id 를 path params 로 받지 않는 이유: body 에서 AnswerUpdate 를 받기 때문
    """
    db_answer = answer_service.get_answer_by_id(db, answer_id=_answer_update.answer_id)
    if not db_answer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="데이터를 찾을수 없습니다.")
    if current_user.id != db_answer.user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="수정 권한이 없습니다.")
    answer_service.update_answer(db=db, db_answer=db_answer,
                                 answer_update=_answer_update)


@router.delete("/delete/{answer_id}", status_code=status.HTTP_204_NO_CONTENT)
def answer_delete(answer_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user_with_sync)):
    """삭제 방법 1. answer_id 를 path params 로 받는 방법"""
    db_answer = answer_service.get_answer_by_id(db, answer_id=answer_id)
    if not db_answer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="데이터를 찾을수 없습니다.")
    if current_user.id != db_answer.user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="삭제 권한이 없습니다.")
    answer_service.delete_answer(db=db, db_answer=db_answer)


@router.delete("/delete2", status_code=status.HTTP_204_NO_CONTENT)
def answer_delete2(_answer_delete: AnswerDelete,
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user_with_sync)):
    """삭제 방법 2. answer_id 를 body 에서 받는 방법(AnswerDelete)"""
    db_answer = answer_service.get_answer_by_id(db, answer_id=_answer_delete.answer_id)
    if not db_answer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="데이터를 찾을수 없습니다.")
    if current_user.id != db_answer.user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="삭제 권한이 없습니다.")
    answer_service.delete_answer(db=db, db_answer=db_answer)


@router.post("/vote", status_code=status.HTTP_204_NO_CONTENT)
def answer_vote(_answer_vote: AnswerVote,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user_with_sync)):
    db_answer = answer_service.get_answer_by_id(db, answer_id=_answer_vote.answer_id)
    if not db_answer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="데이터를 찾을수 없습니다.")
    answer_service.vote_answer(db, db_answer=db_answer, db_user=current_user)

    # 알림 생성 (백그라운드)
    notification_service.create_notification_sync(
        user_id=db_answer.user_id,
        actor_user_id=current_user.id,
        event_type="answer_voted",
        resource_type="answer",
        resource_id=db_answer.id,
        message=f"{current_user.username}님이 회원님의 답변에 투표했습니다.",
    )