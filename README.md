# FastAPI-Playground

## 1. 구조

```text
FastAPI-Playground
├── alembic/(not yet)
├── src
│   ├── auth(not yet)
│   │   ├── router.py
│   │   ├── schemas.py  # pydantic models
│   │   ├── models.py  # db models
│   │   ├── dependencies.py
│   │   ├── config.py  # local configs
│   │   ├── constants.py
│   │   ├── exceptions.py
│   │   ├── service.py
│   │   └── utils.py
│   ├── aws(not yet)
│   │   ├── client.py  # client model for external service communication
│   │   ├── schemas.py
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── exceptions.py
│   │   └── utils.py
│   ├── domains
│   │   └── domainA
│   │       ├── router.py
│   │       ├── schemas.py
│   │       ├── models.py
│   │       ├── dependencies.py
│   │       ├── constants.py
│   │       ├── exceptions.py
│   │       ├── service.py
│   │       └── utils.py
│   ├── config.py  # global configs
│   ├── models.py  # global models
│   ├── exceptions.py  # global exceptions
│   ├── pagination.py  # global module e.g. pagination
│   ├── database.py  # db connection related stuff
│   └── main.py
├── tests/
│   ├── auth
│   ├── aws
│   └── domains
│       ├── domainA
│
├── templates/
│   └── index.html
├── requirements
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── .env
├── .gitignore
├── logging.ini
└── alembic.ini
```

**모든 도메인 디렉토리는 `src` 폴더 안에 생성한다.**

- `src/`: app의 최고 수준이며  common models, configs, constants 등을 포함한다.
- `src/main.py`: FastAPI app을 초기화하는 프로젝트의 루트

**각 패키지에는 자체 `router`, `schemas`, `models` 등이 포함된다.**

- `router.py`: 각 모듈의 모든 엔드포인트가 포함된다.
- `schemas.py`: pydantic 모델이 포함된다.
- `models.py`: db 모델이 포함된다.
- `service.py`: 모듈 별비즈니스 로직이 포함된다.
- `dependencies.py`: 라우터 의존성을 포함한다.
- `constants.py`: 모듈 상수 및 에러 코드를 포함한다.
- `exceptions.py`: 모듈 예외를 포함한다.
- `utils.py`: 모듈 유틸리티를 포함한다. ex) Response normalization, data enrichment etc.

**패키지에서 다른 패키지의 서비스나 종속성 또는 상수가 필요한 경우, 명시적인 모듈 명으로 가져온다.**

```pycon
from src.auth import constants as auth_constants
from src.notifications import service as notification_service
from src.posts.constants import ErrorCode as PostsErrorCode  # in case we have Standard ErrorCode in constants module of each package
```

## 2. 데이터 검증: Pydantic 사용

Pydantic을 활용하여 데이터를 검증하고 변환한다.

- 필수 또는 선택적 필드를 정의한다.
- 정규식, 제한된 허용옵션에 대한 열거형, 길이 유효성 검사, 이메일 유효성 검사 등와 같은 포괄적인 데이터 처리도구 또한 내장되어 있음

```python
from enum import Enum
from pydantic import AnyUrl, BaseModel, EmailStr, Field, constr

class MusicBand(str, Enum):
   AEROSMITH = "AEROSMITH"
   QUEEN = "QUEEN"
   ACDC = "AC/DC"


class UserBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=128)
    username: constr(regex="^[A-Za-z0-9-_]+$", to_lower=True, strip_whitespace=True)
    email: EmailStr
    age: int = Field(ge=18, default=None)  # must be greater or equal to 18
    favorite_band: MusicBand = None  # only "AEROSMITH", "QUEEN", "AC/DC" values are allowed to be inputted
    website: AnyUrl = None
```

## 3. 데이터 검증: DB 모델

Pydantic은 클라이언트 입력 값만 확인할 수 있다. 데이터베이스 레벨의 유효성 검사는 데이터베이스 제약조건을 활용한다.

- 데이터베이스 제약조건을 활용하여, 중복데이터, 존재하지 않는 데이터 등와 같은 데이터베이스 레벨의 유효성 검사를 수행해야 한다.

```python
# dependencies.py
async def valid_post_id(post_id: UUID4) -> Mapping:
    post = await service.get_by_id(post_id)
    if not post:
        raise PostNotFound()

    return post


# router.py
@router.get("/posts/{post_id}", response_model=PostResponse)
async def get_post_by_id(post: Mapping = Depends(valid_post_id)):
    return post


@router.put("/posts/{post_id}", response_model=PostResponse)
async def update_post(
    update_data: PostUpdate,  
    post: Mapping = Depends(valid_post_id), 
):
    updated_post: Mapping = await service.update(id=post["id"], data=update_data)
    return updated_post


@router.get("/posts/{post_id}/reviews", response_model=list[ReviewsResponse])
async def get_post_reviews(post: Mapping = Depends(valid_post_id)):
    post_reviews: list[Mapping] = await reviews_service.get_by_post_id(post["id"])
    return post_reviews
```

## 4. 종속성(Dependencies) 연계

종속성(dependency)는 다른 종속성(dependency)를 사용할 수 있다. 

- 의존성을 계층화하고 재사용성을 높일 수 있다.

```python
# dependencies.py
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

async def valid_post_id(post_id: UUID4) -> Mapping:
    post = await service.get_by_id(post_id)
    if not post:
        raise PostNotFound()

    return post


async def parse_jwt_data(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/token"))
) -> dict:
    try:
        payload = jwt.decode(token, "JWT_SECRET", algorithms=["HS256"])
    except JWTError:
        raise InvalidCredentials()

    return {"user_id": payload["id"]}


async def valid_owned_post(
    post: Mapping = Depends(valid_post_id), 
    token_data: dict = Depends(parse_jwt_data),
) -> Mapping:
    if post["creator_id"] != token_data["user_id"]:
        raise UserNotOwner()

    return post

# router.py
@router.get("/users/{user_id}/posts/{post_id}", response_model=PostResponse)
async def get_user_post(post: Mapping = Depends(valid_owned_post)):
    return post
```

## 5. 종속성(dependencies)을 분리하고 재사용한다.

FastAPI는 기본적으로 요청범위 내에서 종속성 결과를 캐시한다.

- 종속성은 여러번 재사용될 수 있으며, 다시 계산 되지 않는다.
- 서비스 get_post_by_id를 호출하는 종속성이 있는 경우 이 종속성을 호출할 때마다 DB를 방문하지 않는다.(첫번째 함수 호출만 가능하다.)

이를 기반으로, 여러 개의 작은 기능에 대한 종속성을 쉽게 분리할 수 있다.

- valid_owned_post, valid_active_creator, get_user_post 메서드에서 parse_jwt_data를 세 번 사용하고 있지만, 실제로는 첫 번째 호출에서 단 한번만 호출된다.

```python
# dependencies.py
from fastapi import BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

async def valid_post_id(post_id: UUID4) -> Mapping:
    post = await service.get_by_id(post_id)
    if not post:
        raise PostNotFound()

    return post


async def parse_jwt_data(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/token"))
) -> dict:
    try:
        payload = jwt.decode(token, "JWT_SECRET", algorithms=["HS256"])
    except JWTError:
        raise InvalidCredentials()

    return {"user_id": payload["id"]}


async def valid_owned_post(
    post: Mapping = Depends(valid_post_id), 
    token_data: dict = Depends(parse_jwt_data),
) -> Mapping:
    if post["creator_id"] != token_data["user_id"]:
        raise UserNotOwner()

    return post


async def valid_active_creator(
    token_data: dict = Depends(parse_jwt_data),
):
    user = await users_service.get_by_id(token_data["user_id"])
    if not user["is_active"]:
        raise UserIsBanned()
    
    if not user["is_creator"]:
       raise UserNotCreator()
    
    return user
        

# router.py
@router.get("/users/{user_id}/posts/{post_id}", response_model=PostResponse)
async def get_user_post(
    worker: BackgroundTasks,
    post: Mapping = Depends(valid_owned_post),
    user: Mapping = Depends(valid_active_creator),
):
    """Get post that belong the active user."""
    worker.add_task(notifications_service.send_email, user["id"])
    return post
```

---
### 참고 자료
- [fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices?tab=readme-ov-file#11-sqlalchemy-set-db-keys-naming-convention)
- [점프 투 FastAPI](https://wikidocs.net/book/8531)