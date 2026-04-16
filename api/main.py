from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.ops import router as ops_router
from api.routes.pokemon import router as pokemon_router
from api.routes.ws_route import router as ws_router
from api.services.ops_service import ensure_ops_bootstrap
from db.connection import close_pool, get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时初始化连接池，关闭时释放。"""
    await get_pool()
    await ensure_ops_bootstrap()
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
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"message": "洛克王国精灵图鉴 API 运行中"}
