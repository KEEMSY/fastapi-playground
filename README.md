# FastAPI-Playground

## 1. 구조

```text
FastAPI-Playground
├── alembic/
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

```python
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

## 6. REST를 준수한다.

RESTful API를 설계하면, 종속성(dependency)을 더 쉽게 재사용 할 수 있다. 다음 코드에서 유일한 주의사항은 경로에 동일한 변수 이름을 사용하는 것이다.

- `GET /courses/:course_id`
- `GET /courses/:course_id/chapters/:chapter_id/lessons`
- `GET /chapters/:chapter_id`

의미론적인 중복인 경우, 중복을 제거하여 REST를 설계하는 것이 좋다.

- `GET /profiles/:profile_id` 와 `GET /creators/:creator_id` 에서 모두 `profile_id`의 존재 여부를 확인하는 GET 엔드포인트이다.
- 이 경우 `GET /creators/:creator_id` 엔드포인트에서 `profile_id`를 사용하고, 두 종속성을 연결하는 것이 좋다.

 ```python
# src.profiles.dependencies
async def valid_profile_id(profile_id: UUID4) -> Mapping:
    profile = await service.get_by_id(profile_id)
    if not profile:
        raise ProfileNotFound()

    return profile

# src.creators.dependencies
async def valid_creator_id(profile: Mapping = Depends(valid_profile_id)) -> Mapping:
    if not profile["is_creator"]:
       raise ProfileNotCreator()

    return profile

# src.profiles.router.py
@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_user_profile_by_id(profile: Mapping = Depends(valid_profile_id)):
    """Get profile by id."""
    return profile

# src.creators.router.py
@router.get("/creators/{profile_id}", response_model=ProfileResponse)
async def get_user_profile_by_id(
     creator_profile: Mapping = Depends(valid_creator_id)
):
    """Get creator's profile by id."""
    return creator_profile
```

## 7. route를 async로 작성한다.

내부적으로 FastAPI는 비동기 및 동기화 I/O 작업을 모두 효과적으로 처리할 수 있다.

- 스레드 풀에서 sync routes 를 실행하며 I/O작업을 차단해도 이벤트 루프의 작업 실행이 중단 되지 않는다.
- FastAPI는 논블로킹 I/O 작업만 수행하도록 사용자를 신회한다.
- 비동기 경로 내에서 블로킹 작업을 실행하는 경우, 해당 차단 작업이 완료될 때까지, 이벤트 루프가 다음 작업을 실행할 수 없음에 주의한다.

```python
import asyncio
import time

@router.get("/terrible-ping")
async def terrible_catastrophic_ping():
    time.sleep(10) # I/O blocking operation for 10 seconds
    pong = service.get_pong()  # I/O blocking operation to get pong from DB
    
    return {"pong": pong}

@router.get("/good-ping")
def good_ping():
    time.sleep(10) # I/O blocking operation for 10 seconds, but in another thread
    pong = service.get_pong()  # I/O blocking operation to get pong from DB, but in another thread
    
    return {"pong": pong}

@router.get("/perfect-ping")
async def perfect_ping():
    await asyncio.sleep(10) # non-blocking I/O operation
    pong = await service.async_get_pong()  # non-blocking I/O db call

    return {"pong": pong}
```

### `GET /terrible-ping`

서버의 이벤트 루프와 대기열의 모든 작업은 `time.sleep(10)`이 완료될 때 까지 대기한다.

- 서버는 `time.sleep(10)`이 I/O 작업이 아니라고 생각하므로 완료될 때까지 기다린다.
- 서버는 기다리는 동안 새로운 요청을 받아들이지 않는다.(블로킹)
- 서버는 응답을 반환한 뒤 새로운 요청을 받아들인다.

### `GET /good-ping`

서버는 전체 `/good_ping`에 대한 처리를 스레드 풀로 보내는 경우

- `good-ping`이 실행되는 동안 이벤트 루프는 대기열에서 다른 작업을 선택하고 작업한다.
  - 메인 스레드(FastAPI 앱)와는 별개로 작업자 스레드는 `time.sleep(10)`이 완료되고 `service.get_pong()`이 완료될 때까지 기다린다.
  - 동기화 작업은 기본 스레드가 아닌 side 스레드만 차단한다.
  - `good_ping`이 작업을 마치면, 서버는 클라이언트에게 응답을 반환한다.

### `GET /perfect-ping`

이벤트 루프는 대기열에서 다음 작업을 선택하고 작업 할 수 있다.(ex. 다른 요청을 처리, db 쿼리 등)

- asyncio.sleep(10)이 완료되면 서버는 `service.async_get_pong()`을 호출한다. 그리고 이벤트 루프는 대기열에서 다음 작업을 선택하고 작업한다.
- service.async_get_pong()이 완료되면, 서버는 클라이언트에게 응답을 반환한다.

주의해야할 사항으로, 논블로킹 대기 가능 작업 혹은 스레드 풀을 통한 작업은 I/O 집약적인 작업(ex. db 쿼리, 외부 API 호출 등)에 대해 사용해야 한다.

- CPU 집약적인 작업(ex. 계산, 압축, 데이터처리, 비디오 트랜스 코딩 등)은 CPU가 작업을 완료하기 위해 기다려야한다.
- 하지만 I/O 집약적인 작업은 대기할 필요가 없다. 따라서 논블로킹 작업을 사용하여 다른 작업을 수행할 수 있다.
- GIL 때문에 다른 스레드에서 CPU 집약적인 작업을 실행하는 것도 효과적이지 않다. GIL은 한번에 하나의 스레드만 작동하도록 허용하기 때문이다.
- 즉, CPU 집약적인 작업을 최적화 하기 위해서는 해당 작업을 다른 프로레스의 Worker 에게 보내야 한다.

## 8. BaseModel을 활용하여 CustomModel을 사용한다.

BaseModel 에서는 datetime format 또는 super method 추가 등 서브클래스들을 위한 기능들이 지원된다.

```python
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, model_validator


def convert_datetime_to_gmt(dt: datetime) -> str:
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


class CustomModel(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: convert_datetime_to_gmt},
        populate_by_name=True,
    )

    @model_validator(mode="before")
    @classmethod
    def set_null_microseconds(cls, data: dict[str, Any]) -> dict[str, Any]:
        datetime_fields = {
            k: v.replace(microsecond=0)
            for k, v in data.items()
            if isinstance(k, datetime)
        }

        return {**data, **datetime_fields}

    def serializable_dict(self, **kwargs):
        """Return a dict which contains only serializable fields."""
        default_dict = self.model_dump()

        return jsonable_encoder(default_dict)
```

- 모든 날짜 형식에서 마이크로 초를 0으로 떨어트린다.
- 모든 날짜 / 시간 필드를 명시적인 시간대를 사용하여 표준 형식으로 직렬화 한다.

## 9. 문서화

API를 public 으로 하지 않는 이상, 기본적으로 표시되지 않는다. 선택된 환경에서만 명시적으로 API 문서를 명시할 수 있다.

```python
from fastapi import FastAPI
from starlette.config import Config

config = Config(".env")  # parse .env file for env variables

ENVIRONMENT = config("ENVIRONMENT")  # get current env name
SHOW_DOCS_ENVIRONMENT = ("local", "staging")  # explicit list of allowed envs

app_configs = {"title": "My Cool API"}
if ENVIRONMENT not in SHOW_DOCS_ENVIRONMENT:
   app_configs["openapi_url"] = None  # set url for docs as null

app = FastAPI(**app_configs)
```

이해하기 쉬운 문서를 작성하기 위해 `response_model`, `status_code`, `description` 등을 설정한다.

- 모델 혹은 상태가 다양할 경우, 다른 응답 모델을 추가하는 것이 좋다.

```python
from fastapi import APIRouter, status

router = APIRouter()

@router.post(
    "/endpoints",
    response_model=DefaultResponseModel,  # default response pydantic model 
    status_code=status.HTTP_201_CREATED,  # default status code
    description="Description of the well documented endpoint",
    tags=["Endpoint Category"],
    summary="Summary of the Endpoint",
    responses={
        status.HTTP_200_OK: {
            "model": OkResponse, # custom pydantic model for 200 response
            "description": "Ok Response",
        },
        status.HTTP_201_CREATED: {
            "model": CreatedResponse,  # custom pydantic model for 201 response
            "description": "Creates something from user request ",
        },
        status.HTTP_202_ACCEPTED: {
            "model": AcceptedResponse,  # custom pydantic model for 202 response
            "description": "Accepts request and handles it later",
        },
    },
)
async def documented_route():
    pass
```

## 10. configs 를 위해 Pydantic의 BaseSettings를 사용한다.

`Pydantic`의 `BaseSettings` 클래스를 사용하여 설정을 구성한다.

- `환경변수`를 parse 하고, 유효성 검사 등 설정을 관리할 수 있다.
- [공식문서](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

```python
from pydantic import AnyUrl, PostgresDsn
from pydantic_settings import BaseSettings  # pydantic v2

class AppSettings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "app_"

    DATABASE_URL: PostgresDsn
    IS_GOOD_ENV: bool = True
    ALLOWED_CORS_ORIGINS: set[AnyUrl]
```

## 11. SQLAlchemy: DB Key의 명명규칙을 명시적으로 설정한다.

`SQLAlchemy`는 이러한 명명 규칙을 자동으로 생성하지만, 데이터베이스의 명명 규칙에 맞추어 명시적으로 설정하는 것이 좋다.

- `SQLAlchemy` `MetaData` 객체 사용하여 테이블 정의와 관계 정의한다.
- 명명 규칙을 적용함으로써, 생성되는 데이터베이스 키 이름이 예측 가능하고, 데이터베이스 스키마에 대한 일관성을 유지한다.
- 데이터베이스 마이그레이션 또는 스키마 변경 시 발생할 수 있는 혼란을 최소화한다.

```python
from sqlalchemy import MetaData

POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}
metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)
```

## 12. Migrations 을 할 때에는 Alembic을 사용한다.

`Migration` 은 static, revertable 이어야 한다.

-  descriptive 한 names & slugs을 활용하여 migration을 관리한다.
- *date_slug*.py 패턴을 활용한다., e.g. 2022-08-24_post_content_idx.py

```text
# alembic.ini
file_template = %%(year)d-%%(month).2d-%%(day).2d_%%(slug)s
```

## 13. DB 명명 규칙을 설정한다.

- `lower_case_snake_case` 을 사용한다.
- 단수형(ex. post, post_like, user_playlist) 을 사용한다.
- 유사한 테이블을 그룹화하고, 테이블 이름에 접미사(pre_fix)를 추가한다.(ex. post, post_like, post_comment, payment_account, payment_bill)
- `_at`: 날짜/시간 접미사
- `_date`: 날짜 접미사

## 14. 테스트 클라이언트는 비동기 설정한다.

DB를 사용하여 통합 테스트를 작성할 경우, 향후 이벤트 루프 오류가 발생할 가능성이 높으므로, 비동기 테스트 클라이언트를 활용한다.

- 관련하여, `async_asgi_testclient` 또는 `httpx` 라이브러리를 활용한다.

```python
import pytest
from async_asgi_testclient import TestClient

from src.main import app  # inited FastAPI app


@pytest.fixture
async def client():
    host, port = "127.0.0.1", "5555"
    scope = {"client": (host, port)}

    async with TestClient(
        app, scope=scope, headers={"X-User-Fingerprint": "Test"}
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_create_post(client: TestClient):
    resp = await client.post("/posts")

    assert resp.status_code == 201
```

## 15. BackgroundTasks 를 활용하여, 백그라운드 작업을 처리한다.

`BackgroundTasks`는 블로킹 작업과 논블로킹 IO작업을 같은 방식으로 다룰 수 있다.

- sync 작업은 스레드 풀에서 이뤄지며, async 작업은 이후 awited 된다.(async 작업은 이벤트루프에서 이뤄진다.)

```python
from fastapi import APIRouter, BackgroundTasks
from pydantic import UUID4

from src.notifications import service as notifications_service


router = APIRouter()


@router.post("/users/{user_id}/email")
async def send_user_email(worker: BackgroundTasks, user_id: UUID4):
    """Send email to user"""
    worker.add_task(notifications_service.send_email, user_id)  # send email after responding client
    return {"status": "ok"}
```

## 16. Typing을 활용하여, 코드를 명확하게 작성한다.

`FastAPI`에서는 `Pydantic`을 지원하고, 대부분의 IDE에서는 타입 힌트 사용을 장려 한다.

- `Union`, `Optional`, `List`, `Dict`, `Class` 등을 사용하여 코드를 명확하게 작성한다.

## 17. 파일은 여러개의 chunk로 저장한다.

사용자가 작은 파일들을 보낼거라고 기대하지 말자.

- 클라이언트가 서버에 파일, 특히 대용량 파일을 업로드할 때 전체 파일을 메모리에 로드하려고 시도하면 서버 리소스에 부담을 주고, 업로드가 실패하거나 비효율성을 초래한다.
- 파일을 여러 청크로 나누어 저장하면, 서버 리소스를 효율적으로 사용할 수 있으며, 서버의 응답성을 유지할 수 있다.


```python
import aiofiles
from fastapi import UploadFile

DEFAULT_CHUNK_SIZE = 1024 * 1024 * 50  # 50 megabytes

async def save_video(video_file: UploadFile):
   async with aiofiles.open("/file/path/name.mp4", "wb") as f:
     while chunk := await video_file.read(DEFAULT_CHUNK_SIZE):
         await f.write(chunk)
```

## 18. 동적 Pydantic 모델을 사용할 때에는 주의한다.

여러 유형을 허용할 수 있는 필드로 모델을 정의할 때(Python의 `Union` 또는 `|` 표기법 사용), `Pydantic`은 입력 데이터를 올바른 유형과 일치시키려고 시도한다. 

- 첫 번째 유형부터 시작하여 데이터를 맞추려고 시도하며, 오류를 발생시키지 않고 데이터를 첫 번째 유형으로 강제 변환할 수 있는 경우 `Pydantic`은 해당 유형을 선택하며 때로는 의도하지 않은 결과를 초래할 수 있다.

```python
from pydantic import BaseModel


class Article(BaseModel):
   text: str | None
   extra: str | None


class Video(BaseModel):
   video_id: int
   text: str | None
   extra: str | None

   
class Post(BaseModel):
   content: Article | Video

   
post = Post(content={"video_id": 1, "text": "text"})
print(type(post.content))
# OUTPUT: Article
# Article is very inclusive and all fields are optional, allowing any dict to become valid
```

### 해결책

1. 모델을 작성할 때, `Extra.forbid` 사용한다.

`Extra.forbid` 은 모델에 명시적으로 정의되지 않은 추가 필드를 금지하도록 모델을 구성한다.

- 알려진 필드만 허용되므로 입력 데이터를 기반으로 모델 유형을 잘못 식별하는 위험이 줄어든다.

```python
from pydantic import BaseModel, Extra

class Article(BaseModel):
   text: str | None
   extra: str | None
   
   class Config:
        extra = Extra.forbid
       

class Video(BaseModel):
   video_id: int
   text: str | None
   extra: str | None
   
   class Config:
        extra = Extra.forbid

   
class Post(BaseModel):
   content: Article | Video
```

2. 스마트 유니온을 사용한다.(Pydantic 버전 1.9 이상 및 2.0 미만에서 사용 가능)

`smart_union`은 입력 데이터를 기반으로 유니온에서 사용해야 하는 유형을 보다 지능적으로 결정한다. 

- 간단한 클래스 유형(예: `int` 또는 `bool`)을 사용하는 경우에만 동작한다.(클래스를 지정할 경우 동작하지 않는다.)

```python
##############################
# without smart_union
##############################
from pydantic import BaseModel


class Post(BaseModel):
   field_1: bool | int
   field_2: int | str
   content: Article | Video

p = Post(field_1=1, field_2="1", content={"video_id": 1})
print(p.field_1)
# OUTPUT: True
print(type(p.field_2))
# OUTPUT: int
print(type(p.content))
# OUTPUT: Article

##############################
# with smart_union
##############################
class Post(BaseModel):
   field_1: bool | int
   field_2: int | str
   content: Article | Video

   class Config:
      smart_union = True


p = Post(field_1=1, field_2="1", content={"video_id": 1})
print(p.field_1)
# OUTPUT: 1
print(type(p.field_2))
# OUTPUT: str
print(type(p.content))
# OUTPUT: Article, because smart_union doesn't work for complex fields like classes
```

3. 필드 유형 순서를 지정한다.

가장 실용적인 해결방법으로, Union의 유형을 가장 구체적인(또는 엄격한) 것부터 가장 적은 것 순으로 정렬한다.

- `Pydantic`은 가장 구체적인 유형을 먼저 일치시키려고 시도하며 이는 복잡한 필드의 유형을 올바르게 식별하는 데 도움이 된다.

```python
class Post(BaseModel):
   content: Video | Article
```

## 19. SQL을 우선적으로 하고, 다음 Pydantic을 사용한다.

일반적으로 DB는 CPython이 수행하는 것보다 훨씬 빠르고 깔끔하게 데이터를 처리한다.

- 복잡한 `JOIN`과 간단한 데이터 조작은 모두 `SQL`로 수행하는 것이 좋다.
- `SQL`을 사용하여 데이터를 가져와 구조화 한 뒤, `Pydantic`을 사용하여 데이터를 변환한다.
- 이를 통해 데이터는 더 빠르게 처리되고, FE에 일관된 인터페이스를 제공할 수 있다.

```python
# src.posts.service
from typing import Mapping

from pydantic import UUID4
from sqlalchemy import desc, func, select, text
from sqlalchemy.sql.functions import coalesce

from src.database import database, posts, profiles, post_review, products

async def get_posts(
    creator_id: UUID4, *, limit: int = 10, offset: int = 0
) -> list[Mapping]: 
    select_query = (
        select(
            (
                posts.c.id,
                posts.c.type,
                posts.c.slug,
                posts.c.title,
                func.json_build_object(
                   text("'id', profiles.id"),
                   text("'first_name', profiles.first_name"),
                   text("'last_name', profiles.last_name"),
                   text("'username', profiles.username"),
                ).label("creator"),
            )
        )
        .select_from(posts.join(profiles, posts.c.owner_id == profiles.c.id))
        .where(posts.c.owner_id == creator_id)
        .limit(limit)
        .offset(offset)
        .group_by(
            posts.c.id,
            posts.c.type,
            posts.c.slug,
            posts.c.title,
            profiles.c.id,
            profiles.c.first_name,
            profiles.c.last_name,
            profiles.c.username,
            profiles.c.avatar,
        )
        .order_by(
            desc(coalesce(posts.c.updated_at, posts.c.published_at, posts.c.created_at))
        )
    )
    
    return await database.fetch_all(select_query)

# src.posts.schemas
import orjson
from enum import Enum

from pydantic import BaseModel, UUID4, validator


class PostType(str, Enum):
    ARTICLE = "ARTICLE"
    COURSE = "COURSE"

   
class Creator(BaseModel):
    id: UUID4
    first_name: str
    last_name: str
    username: str


class Post(BaseModel):
    id: UUID4
    type: PostType
    slug: str
    title: str
    creator: Creator

    @validator("creator", pre=True)  # before default validation
    def parse_json(cls, creator: str | dict | Creator) -> dict | Creator:
       if isinstance(creator, str):  # i.e. json
          return orjson.loads(creator)

       return creator
    
# src.posts.router
from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/creators/{creator_id}/posts", response_model=list[Post])
async def get_creator_posts(creator: Mapping = Depends(valid_creator_id)):
   posts = await service.get_posts(creator["id"])

   return posts
```

집계된 데이터 양식이 간단한 `JSON`인 경우, `Pydantic`의 `Json`을 사용하는 것을 고려할 수 있다.

- `Pydantic`의 `Json 필드`는 `raw JSON` 보다 먼저 로딩된다.

```python
from pydantic import BaseModel, Json

class A(BaseModel):
    numbers: Json[list[int]]
    dicts: Json[dict[str, int]]

valid_a = A(numbers="[1, 2, 3]", dicts='{"key": 1000}')  # becomes A(numbers=[1,2,3], dicts={"key": 1000})
invalid_a = A(numbers='["a", "b", "c"]', dicts='{"key": "str instead of int"}')  # raises ValueError
```

## 20. URLs에 대한 hosts를 검증한다.

`Pydantic`을 활용하여 신뢰할 수 있는 소스의 `URL`만 허용 되도록 한다.

- 화이트 리스트(허용된 호스트 집합(예: "mysite.com", "mysite.org"))를 정의한다.
- 사용자 정의 `AnyUrl` 클래스를 생성하고, `validate_host` 메서드를 재정의하여 추가 유효성 검사 논리를 도입한다.
- 사용자 정의 `URL` 유형은 `Pydantic` 모델(예: `Profile`)에서 `URL`을 허용하는 필드를 검증하는 데 사용되어 허용 목록에 있는 호스트의 `URL`만 허용되도록 한다.

```python
from pydantic import AnyUrl, BaseModel

ALLOWED_MEDIA_URLS = {"mysite.com", "mysite.org"}

class CompanyMediaUrl(AnyUrl):
    @classmethod
    def validate_host(cls, parts: dict) -> tuple[str, str, str, bool]:  # pydantic v1
       """Extend pydantic's AnyUrl validation to whitelist URL hosts."""
        host, tld, host_type, rebuild = super().validate_host(parts)
        if host not in ALLOWED_MEDIA_URLS:
            raise ValueError(
                "Forbidden host url. Upload files only to internal services."
            )

        return host, tld, host_type, rebuild


class Profile(BaseModel):
    avatar_url: CompanyMediaUrl  # only whitelisted urls for avatar
```

이 방식을 통해 보안, 유연성, 단순성 측면에서 장점이 있다.

- 승인되지 않은 호스트의 사용을 방지하여, 보안을 강화할 수 있다.
- 유효성 검사 논리를 변경하지 않고도 화이트리스트를 쉽게 업데이트 할 수 있다.

## 21. 커스텀 Pydantic validator에서 ValueError를 사용한다.

```python
# src.profiles.schemas
from pydantic import BaseModel, validator

class ProfileCreate(BaseModel):
    username: str
    
    @validator("username")  # pydantic v1
    def validate_bad_words(cls, username: str):
        if username  == "me":
            raise ValueError("bad username, choose another")
        
        return username


# src.profiles.routes
from fastapi import APIRouter

router = APIRouter()


@router.post("/profiles")
async def get_creator_posts(profile_data: ProfileCreate):
   pass
```

## 22. FastAPI는 Pydantic 객체를 Dict > Pydantic object > JSON 으로 변환한다.

`FastAPI`는 먼저 해당 `pydantic 개체`를 `jsonable_encoder`를 사용하여 `dict`로 변환한 다음 `response_model`을 사용하여 데이터의 유효성을 검사, 그리고 개체를 `JSON`으로 직렬화한다.

- `response_model`과 일치하는 `Pydantic` 객체를 반환 할 수 없음에 주의한다.

```python
from fastapi import FastAPI
from pydantic import BaseModel, root_validator

app = FastAPI()


class ProfileResponse(BaseModel):
    @root_validator
    def debug_usage(cls, data: dict):
        print("created pydantic model")

        return data

    def dict(self, *args, **kwargs):
        print("called dict")
        return super().dict(*args, **kwargs)


@app.get("/", response_model=ProfileResponse)
async def root():
    return ProfileResponse()

'''
Logs Output:
[INFO] [2022-08-28 12:00:00.000000] created pydantic model
[INFO] [2022-08-28 12:00:00.000010] called dict
[INFO] [2022-08-28 12:00:00.000020] created pydantic model
[INFO] [2022-08-28 12:00:00.000030] called dict
'''
```

## 23. sync SDK을 사용해야한다면, thread pool을 사용한다.

동기 라이브러리 또는 `SDK`가 비동기 애플리케이션 내에서 사용되는 경우 이벤트 루프를 보류하여 `FastAPI`의 이점을 무효화 할 수 있다.

- 외부 서비스와 상호작용하기 위해 라이브러리를 사용해야하고, 비동기적이지 않은 경우, 외부 worker thread에서 HTTP 요청을 수행하는 것이 좋다.
- `run_in_threadpool` 함수를 사용하여 외부 서비스와 상호작용하는 동기 코드를 비동기 코드로 변환한다.
  - `run_in_threadpool`: 스레드 풀에서 동기 함수 실행을 예약하는 `Starlette`(FastAPI가 구축된 경량 ASGI 프레임워크)의 유틸리티 함수, 이 스레드 풀은 비동기 이벤트 루프에 의해 관리되므로 비동기 작업을 차단하지 않고 동기 함수를 실행할 수 있다.
- `SyncAPIClient`: 외부 서비스와 상호 작용하는 데 사용되는 가상의 동기 클라이언트 라이브러리로, 일반적으로 비동기 애플리케이션에서 이벤트 루프를 차단한다.

```python
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from my_sync_library import SyncAPIClient 

app = FastAPI()


@app.get("/")
async def call_my_sync_library():
    my_data = await service.get_my_data()

    client = SyncAPIClient()
    await run_in_threadpool(client.make_request, data=my_data)
```

## 24. Linters를 사용한다.

`Linter`를 사용하면 코드 형식을 통일하고, 잠재적인 버그를 찾아내고, 코드의 가독성을 높일 수 있다.

- `Black`, `Ruff`를 사용하는 것을 추천한다.
- `pre-commit hooks`를 사용하는 방법도 좋은 방법이지만, `script`를 사용하는 것만으로도 충분하다.

```shell
#!/bin/sh -e
set -x

ruff --fix
black src tests
```

---
### 참고 자료
- [fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices?tab=readme-ov-file#11-sqlalchemy-set-db-keys-naming-convention)
- [점프 투 FastAPI](https://wikidocs.net/book/8531)