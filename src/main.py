from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from src.domains.sync_example.presentation import no_login_router as sync_example_router_v1
from src.domains.question import router as question_router
from src.domains.answer import router as answer_router
from src.domains.user import router as user_router
from src.exceptions import PLException, BLException, DLException

app = FastAPI()

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(sync_example_router_v1.router)
app.include_router(question_router.router)
app.include_router(answer_router.router)
app.include_router(user_router.router)


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
