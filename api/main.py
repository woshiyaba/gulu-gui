from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.pokemon import router as pokemon_router

app = FastAPI(title="洛克王国精灵图鉴 API", version="1.0.0")

# 允许本地 Vue 开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(pokemon_router)


@app.get("/")
def root():
    return {"message": "洛克王国精灵图鉴 API 运行中"}
