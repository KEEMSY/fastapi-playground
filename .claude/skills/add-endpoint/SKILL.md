---
name: add-endpoint
description: This skill should be used when the user asks to "add endpoint", "create API endpoint", "새 엔드포인트 추가", "API 추가", or wants to add a new route to an existing domain.
version: 1.0.0
---

# Add Endpoint

기존 도메인에 새로운 엔드포인트를 추가할 때 사용합니다. 전체 레이어(router → service → repository)에 일관된 코드를 자동으로 추가합니다.

## 사용 시점

- 기존 도메인에 새 API 추가
- 커스텀 비즈니스 로직 엔드포인트 생성
- 예: "question에 좋아요 수 조회 엔드포인트 추가해줘"

## 실행 플로우

### 1단계: 도메인 선택

```bash
사용 가능한 도메인:
1. question
2. answer
3. user
4. notification

어떤 도메인에 엔드포인트를 추가하시겠습니까?
```

### 2단계: 엔드포인트 정보 수집

```yaml
질문 1: 엔드포인트 이름은?
  입력: like_count  # 스네이크 케이스

질문 2: HTTP 메서드는?
  선택: GET | POST | PUT | DELETE

질문 3: 경로는?
  예시:
    - /api/question/like-count/{id}  # GET용
    - /api/question/like  # POST용
  기본값: /api/{domain}/{endpoint_name}

질문 4: 요청 파라미터는?
  예시:
    - Path: question_id:int
    - Query: start_date:date, end_date:date
    - Body: QuestionLikeCreate
  형식: 위치:파라미터명:타입

질문 5: 응답 모델은?
  선택:
    - 기존 스키마 사용 (예: Question, QuestionList)
    - 새 스키마 생성 (예: LikeCountResponse)
    - 응답 없음 (204 No Content)

질문 6: 인증 필요?
  - Yes: get_current_user_with_async 추가
  - No: 공개 엔드포인트

질문 7: 비즈니스 로직 설명
  자유 입력: "특정 question의 전체 좋아요 수를 집계하여 반환"
```

### 3단계: 스키마 생성 (필요 시)

새 스키마가 필요한 경우 `schemas.py`에 추가:

```python
# src/domains/{domain}/schemas.py에 추가

class LikeCountResponse(BaseModel):
    question_id: int
    like_count: int
    user_voted: bool  # 현재 사용자가 투표했는지
```

### 4단계: 서비스 함수 생성

`service.py`에 비즈니스 로직 추가:

```python
# src/domains/{domain}/service.py에 추가

async def get_like_count(
    db: AsyncSession,
    question_id: int,
    current_user_id: Optional[int] = None
) -> dict:
    """질문의 좋아요 수 조회

    Args:
        db: 데이터베이스 세션
        question_id: 질문 ID
        current_user_id: 현재 사용자 ID (투표 여부 확인용)

    Returns:
        좋아요 수와 사용자 투표 여부
    """
    question = await get_question(db, question_id)
    if not question:
        return None

    like_count = len(question.voter)
    user_voted = False

    if current_user_id:
        user_voted = any(v.id == current_user_id for v in question.voter)

    return {
        "question_id": question_id,
        "like_count": like_count,
        "user_voted": user_voted
    }
```

**컨벤션 적용:**
- ✅ 함수명: `{action}_{detail}` 패턴
- ✅ async/await
- ✅ 타입 힌팅
- ✅ Docstring (Args, Returns)
- ✅ None 체크

### 5단계: 라우터 엔드포인트 추가

`router.py`에 엔드포인트 추가:

```python
# src/domains/{domain}/router.py에 추가

@router.get("/like-count/{question_id}", response_model=question_schema.LikeCountResponse)
async def question_like_count(
    question_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async)
):
    """질문의 좋아요 수 조회"""
    result = await question_service.get_like_count(
        db, question_id=question_id, current_user_id=current_user.id
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="질문을 찾을 수 없습니다"
        )
    return result
```

**컨벤션 적용:**
- ✅ 함수명: `{domain}_{endpoint_name}`
- ✅ Path parameter: `{question_id}` (중괄호 사용)
- ✅ 의존성 주입 순서: db → auth → query params
- ✅ 한글 에러 메시지
- ✅ HTTPException 사용

### 6단계: 코드 삽입 위치 찾기

- **schemas.py**: 파일 끝에 추가
- **service.py**: 기존 함수들 뒤, 파일 끝에 추가
- **router.py**: 마지막 엔드포인트 뒤에 추가

### 7단계: 완료 및 테스트 안내

```markdown
✅ 엔드포인트 추가 완료!

추가된 코드:
- 📄 schemas.py: LikeCountResponse 스키마
- 🔧 service.py: get_like_count() 함수
- 🛣️  router.py: GET /api/question/like-count/{id}

테스트 방법:
1. 서버 재시작 (hot reload 작동하지 않을 수 있음)
2. http://localhost:7777/docs 에서 새 엔드포인트 확인
3. 샘플 요청:
   GET /api/question/like-count/1
   Authorization: Bearer <token>

다음 단계:
- 테스트 코드 생성: /test-gen question like_count
- 통합 테스트: pytest tests/domains/question/test_router.py
```

## 엔드포인트 패턴 템플릿

### GET - 단건 조회
```python
@router.get("/{resource}/{id}", response_model=Schema)
async def {domain}_{resource}(
    id: int,
    db: AsyncSession = Depends(get_async_db)
):
    result = await service.get_{resource}(db, id)
    if not result:
        raise HTTPException(404, detail="리소스를 찾을 수 없습니다")
    return result
```

### GET - 목록 조회
```python
@router.get("/{resource}/list", response_model=SchemaList)
async def {domain}_{resource}_list(
    db: AsyncSession = Depends(get_async_db),
    page: int = 0,
    size: int = 10
):
    total, items = await service.get_{resource}_list(db, page*size, size)
    return {"total": total, "{resource}_list": items}
```

### POST - 생성
```python
@router.post("/{resource}", status_code=status.HTTP_204_NO_CONTENT)
async def {domain}_{resource}_create(
    _data: Schema,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async)
):
    await service.create_{resource}(db, _data, current_user)
```

### PUT - 수정
```python
@router.put("/{resource}", status_code=status.HTTP_204_NO_CONTENT)
async def {domain}_{resource}_update(
    _data: SchemaUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async)
):
    resource = await service.get_{resource}(db, _data.id)
    if not resource:
        raise HTTPException(400, detail="데이터를 찾을 수 없습니다.")
    if current_user.id != resource.user_id:
        raise HTTPException(400, detail="수정 권한이 없습니다.")
    await service.update_{resource}(db, resource, _data)
```

### POST - 액션
```python
@router.post("/{resource}/{action}", status_code=status.HTTP_204_NO_CONTENT)
async def {domain}_{resource}_{action}(
    _data: Schema,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async)
):
    await service.{action}_{resource}(db, _data, current_user)
```

## 주의사항

- **Import 추가**: 새 스키마를 사용하는 경우 import 문 자동 추가
- **코드 포맷팅**: 기존 코드 스타일 유지 (들여쓰기, 줄바꿈)
- **에러 처리**: 적절한 HTTP 상태 코드 사용
- **문서화**: 간단한 docstring 추가 권장

## 고급 기능

### 트랜잭션 처리가 필요한 경우
```python
async def complex_operation(db: AsyncSession, data):
    try:
        # 여러 작업
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise
```

### 이벤트 발행이 필요한 경우
```python
await event_bus.publish(DomainEvent(
    event_type=EventType.CUSTOM_EVENT,
    actor_user_id=current_user.id,
    target_user_id=target_id,
    resource_id=resource_id,
    resource_type="resource_name",
    message="이벤트 메시지",
))
```

### 복잡한 쿼리가 필요한 경우
```python
from sqlalchemy import and_, or_

query = select(Model).where(
    and_(
        Model.field1 == value1,
        or_(
            Model.field2.like(f"%{keyword}%"),
            Model.field3 == value3
        )
    )
)
```
