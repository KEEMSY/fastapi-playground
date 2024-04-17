from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from starlette import status

from src.database import get_db, get_async_db
from src.domains.question import schemas as question_schema, service as question_service
from src.domains.user.schemas import User
from src.domains.user.router import get_current_user

router = APIRouter(
    prefix="/api/question",
)


@router.get("/list", response_model=question_schema.QuestionList)
async def question_list(db: AsyncSession = Depends(get_async_db), page: int = 0, size: int = 10, keyword: str = ''):
    total, _question_list = await question_service.get_question_list(
        db, offset=page * size, limit=size, keyword=keyword
    )
    return {"total": total, "question_list": _question_list}


@router.get("/detail/{question_id}", response_model=question_schema.Question)
async def question_detail(question_id: int, db: AsyncSession = Depends(get_async_db)):
    question = await question_service.get_question(db, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.post("/create", status_code=status.HTTP_204_NO_CONTENT)
async def question_create(_question_create: question_schema.QuestionCreate,
                          db: AsyncSession = Depends(get_async_db),
                          current_user: User = Depends(get_current_user)):
    await question_service.create_question(db=db, question_create=_question_create,
                                           user=current_user)


@router.put("/update", status_code=status.HTTP_204_NO_CONTENT)
def question_update(_question_update: question_schema.QuestionUpdate,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    question_model = question_service.get_question(db, question_id=_question_update.question_id)
    if not question_model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="데이터를 찾을수 없습니다.")

    if current_user.id != question_model.user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="수정 권한이 없습니다.")
    question_service.update_question(db=db, question_model=question_model,
                                     question_update=_question_update)


@router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
def question_delete(_question_delete: question_schema.QuestionDelete,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    question_model = question_service.get_question(db, question_id=_question_delete.question_id)
    if not question_model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="데이터를 찾을수 없습니다.")
    if current_user.id != question_model.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="삭제 권한이 없습니다.")
    question_service.delete_question(db=db, question_model=question_model)


@router.post("/vote", status_code=status.HTTP_204_NO_CONTENT)
def question_vote(_question_vote: question_schema.QuestionVote,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    question_model = question_service.get_question(db, question_id=_question_vote.question_id)
    if not question_model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="데이터를 찾을수 없습니다.")
    question_service.vote_question(db, question_model=question_model, db_user=current_user)
