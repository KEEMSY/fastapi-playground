from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from src.domains.sync_example.presentation import no_login_router as sync_example_router_v1, \
    login_router as sync_example_router_v2
from src.domains.async_example.presentation import no_login_router as async_example_router_v1
from src.domains.question import router as question_router
from src.domains.answer import router as answer_router
from src.domains.user import router as user_router
from src.domains.standard.presentation.standard_v1 import router_v1 as standard_router
from src.domains.standard.presentation.standard_v2 import router_v2 as standard_router_v2
from src.domains.notification import router as notification_router
from src.domains.scheduler import router as scheduler_router
from src.exceptions import PLException, BLException, DLException
from src.common.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시
    print("애플리케이션 시작")
    start_scheduler()  # 스케줄러 시작
    yield
    # 종료 시
    stop_scheduler()  # 스케줄러 종료
    print("애플리케이션 종료")

app = FastAPI(lifespan=lifespan)

# Prometheus instrumentation 설정 - 애플리케이션 시작 전에 설정
Instrumentator().instrument(app).expose(app)

origins = [
    "http://localhost:5173",
    "http://localhost:7777",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(sync_example_router_v1.router)
app.include_router(sync_example_router_v2.router)
app.include_router(async_example_router_v1.router)
app.include_router(question_router.router)
app.include_router(answer_router.router)
app.include_router(user_router.router)

# 표준 형식 테스트용 API
app.include_router(standard_router)
app.include_router(standard_router_v2)

# 알림 시스템
app.include_router(notification_router.router)

# 스케줄러 관리
app.include_router(scheduler_router.router)

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(PLException)
async def pl_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "detail": exc.detail})


@app.exception_handler(BLException)
async def bl_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "detail": exc.detail})


@app.exception_handler(DLException)
async def dl_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code,
                        content={"code": exc.code, "detail": exc.detail})


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
