from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.ai_pk import router as ai_pk_router
from api.routes.file_upload import router as file_upload_router
from api.routes.ops import router as ops_router
from api.routes.pokemon import router as pokemon_router
from api.routes.third import router as third_router
from api.routes.wx import router as wx_router
from api.routes.ws_route import router as ws_router
from api.services.ai_pk_service import ensure_ai_pk_tables
from api.services.ops_service import ensure_ops_bootstrap
from api.services.wx_service import ensure_wx_auth_tables
from db.connection import close_pool, get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时初始化连接池，关闭时释放。"""
    await get_pool()
    await ensure_ops_bootstrap()
    await ensure_wx_auth_tables()
    await ensure_ai_pk_tables()
    yield
    await close_pool()


app = FastAPI(title="洛克王国精灵图鉴 API", version="1.0.0", lifespan=lifespan)

# 允许本地 Vue 开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pokemon_router)
app.include_router(ops_router)
app.include_router(wx_router)
app.include_router(third_router)
app.include_router(ai_pk_router)
app.include_router(file_upload_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"message": "洛克王国精灵图鉴 API 运行中"}
