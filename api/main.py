from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.pokemon import router as pokemon_router
from db.connection import close_pool, get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时初始化连接池，关闭时释放。"""
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="洛克王国精灵图鉴 API", version="1.0.0", lifespan=lifespan)

# 允许本地 Vue 开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(pokemon_router)


@app.get("/")
async def root():
    return {"message": "洛克王国精灵图鉴 API 运行中"}
