# Ops 系统 — 精灵性格（Personality）维护模块设计

> 目标：在现有 Ops 后台（`/api/ops/*` + `front/pc-front/src/views/ops/*`）中，
> 增加对 `personality` 表（30 条固定字典）的**查询 + 编辑**能力，
> 保持与 Banner / Dict / SkillStone 等模块同构，最小化学习成本。

---

## 1. 需求边界

### 1.1 数据特点
- `personality` 是**字典型数据**，量小（固定 30 条），几乎不新增。
- `id` 由业务侧显式分配（1–30），不使用 `SERIAL`。
- 数据来源：`docs/pets/personalities.json` + `scripts/import_personalities.py` 初始化。
- 外部引用：未来玩家精灵实例（`pokemon_instance` 之类）的 `personality_id` 外键。

### 1.2 功能范围
| 能力 | 开放 | 说明 |
| --- | :-: | --- |
| 列表 + 筛选 | ✅ | 按中/英文模糊；按"+10% 项 / -10% 项"筛选 |
| 详情查看 | ✅ | 六维修正值一览 |
| 修改名称 / 修正值 | ✅ | `editor` 及以上 |
| 新增 | ✅（admin） | 仅管理员，防止误增；强制指定 id |
| 删除 | ⚠️ 仅 admin + 强校验 | 有外键引用时拒绝 |
| 导入（从 JSON 重置） | ✅（admin） | 触发 `import_personalities.py` 语义的接口，幂等重建 |

### 1.3 不做的事
- 不做软删除（字典级数据直接物理删除）。
- 不做多语言（当前只有 `zh` + 英文 key，和 JSON 一致）。
- 不做版本化历史（由 `ops_audit_log` 统一承接审计）。

---

## 2. 数据库层

### 2.1 表定义（已在 `sql/wikiroco.sql` 与 `scripts/import_personalities.py` 落地）

```sql
CREATE TABLE personality (
    id              SMALLINT     PRIMARY KEY,     -- 1..30，业务分配
    name_en         VARCHAR(32)  NOT NULL,
    name_zh         VARCHAR(16)  NOT NULL,
    hp_mod_pct      NUMERIC(3,2) NOT NULL DEFAULT 0,
    phy_atk_mod_pct NUMERIC(3,2) NOT NULL DEFAULT 0,
    mag_atk_mod_pct NUMERIC(3,2) NOT NULL DEFAULT 0,
    phy_def_mod_pct NUMERIC(3,2) NOT NULL DEFAULT 0,
    mag_def_mod_pct NUMERIC(3,2) NOT NULL DEFAULT 0,
    spd_mod_pct     NUMERIC(3,2) NOT NULL DEFAULT 0,
    CONSTRAINT uk_personality_en UNIQUE (name_en),
    CONSTRAINT uk_personality_zh UNIQUE (name_zh)
);
```

### 2.2 约束与校验（在 service 层做，避免写 CHECK 约束锁死）

- 每项 `*_mod_pct` 取值须 ∈ `{-0.10, 0.00, 0.10}`；
- 保存时**强建议**（非强制）校验：恰好一项 `0.10` + 恰好一项 `-0.10`，其余 `0`；
  - 不通过时返回可跳过的警告（`warnings: []`），避免堵死非标数据。
- `name_en` 限定 `^[A-Za-z]{2,32}$`；`name_zh` 限定 2–8 个字符。

---

## 3. 后端分层（FastAPI）

严格对齐 `banner_*` 模块的结构。

```
api/
├── schemas/personality.py            (新增)
├── repositories/personality_repository.py  (新增)
├── services/personality_service.py   (新增)
└── routes/ops.py                     (追加 7 个路由)
```

### 3.1 Schema `api/schemas/personality.py`

```python
from pydantic import BaseModel, Field, conint

Pct = float   # 校验放到 service 层

class PersonalityItem(BaseModel):
    id: int
    name_en: str
    name_zh: str
    hp_mod_pct: Pct = 0.0
    phy_atk_mod_pct: Pct = 0.0
    mag_atk_mod_pct: Pct = 0.0
    phy_def_mod_pct: Pct = 0.0
    mag_def_mod_pct: Pct = 0.0
    spd_mod_pct: Pct = 0.0
    # 便于前端展示，由 service 填
    buff_stat: str | None = None       # "spd" / "phy_atk" / ...
    nerf_stat: str | None = None
    is_neutral: bool = False            # 是否全 0（保留字段）

class PersonalityListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 100
    items: list[PersonalityItem] = Field(default_factory=list)

class PersonalityUpsertRequest(BaseModel):
    # 创建时必填，更新时忽略（走 path 参数）
    id: conint(ge=1, le=999) | None = None
    name_en: str
    name_zh: str
    hp_mod_pct: Pct = 0.0
    phy_atk_mod_pct: Pct = 0.0
    mag_atk_mod_pct: Pct = 0.0
    phy_def_mod_pct: Pct = 0.0
    mag_def_mod_pct: Pct = 0.0
    spd_mod_pct: Pct = 0.0

class PersonalityResetResponse(BaseModel):
    inserted: int
    source: str   # 'json'
```

### 3.2 Repository `api/repositories/personality_repository.py`

对齐 `banner_repository.py`：全异步 `psycopg` 连接池。

```python
STAT_COLS = (
    "hp_mod_pct", "phy_atk_mod_pct", "mag_atk_mod_pct",
    "phy_def_mod_pct", "mag_def_mod_pct", "spd_mod_pct",
)
ALL_COLS = ("id", "name_en", "name_zh", *STAT_COLS)

async def list_personalities(
    keyword: str = "",
    buff_stat: str = "",
    nerf_stat: str = "",
    page: int = 1,
    page_size: int = 100,
) -> tuple[int, list[dict]]: ...

async def get_personality_by_id(pid: int) -> dict | None: ...

async def create_personality(payload: dict) -> dict: ...
    # INSERT ... RETURNING *；冲突时抛 UniqueViolation

async def update_personality(pid: int, payload: dict) -> dict | None: ...

async def delete_personality(pid: int) -> bool: ...

async def bulk_upsert_personalities(rows: list[dict]) -> int: ...
    # 用于 /reset 从 JSON 全量重建
```

筛选 SQL 关键片段：

```sql
-- keyword: 中/英文模糊
WHERE (%s = '' OR name_zh ILIKE '%%'||%s||'%%' OR name_en ILIKE '%%'||%s||'%%')
  AND (%s = '' OR <buff_col> = 0.10)
  AND (%s = '' OR <nerf_col> = -0.10)
ORDER BY id
```

`buff_stat` / `nerf_stat` 需白名单映射，避免拼接时 SQL 注入。

### 3.3 Service `api/services/personality_service.py`

```python
from api.services.ops_service import ensure_role
from api.repositories import personality_repository, ops_repository

ALLOWED_MODS = {-0.10, 0.00, 0.10}
STATS = ("hp", "phy_atk", "mag_atk", "phy_def", "mag_def", "spd")

def _derive_buff_nerf(row: dict) -> dict:
    # 填充 buff_stat / nerf_stat / is_neutral
    ...

def _validate_mods(payload: dict) -> list[str]:
    # 返回警告列表（service 不强拦，除非明显非法）
    # 1) 每项必须 ∈ ALLOWED_MODS
    # 2) 建议：恰好一项 0.10 + 恰好一项 -0.10
    ...

async def list_personalities_for_ops(user, **kwargs): ensure_role(user, {"viewer","editor","admin"}) ...

async def create_personality_for_ops(user, payload):
    ensure_role(user, {"admin"})
    _validate_mods(payload)   # 非法值直接 400
    item = await personality_repository.create_personality(payload)
    await ops_repository.create_audit_log(
        user_id=user["id"], resource_type="personality",
        resource_id=str(item["id"]), action="create",
        before_json=None, after_json=item,
    )
    return _derive_buff_nerf(item)

async def update_personality_for_ops(user, pid, payload):
    ensure_role(user, {"editor", "admin"})
    before = await personality_repository.get_personality_by_id(pid)
    if not before: raise HTTPException(404, "性格不存在")
    _validate_mods(payload)
    item = await personality_repository.update_personality(pid, payload)
    await ops_repository.create_audit_log(...)
    return _derive_buff_nerf(item)

async def delete_personality_for_ops(user, pid):
    ensure_role(user, {"admin"})
    # TODO: 若未来有引用外键，先查 pokemon_instance 是否使用
    ...

async def reset_personalities_from_json(user) -> dict:
    ensure_role(user, {"admin"})
    # 从 docs/pets/personalities.json 加载并 upsert（全量覆盖）
    ...
```

### 3.4 Routes（追加到 `api/routes/ops.py`）

命名与顺序参考"技能石"段落：

```python
# ---------- 性格维护 ----------

@router.get("/personalities", response_model=PersonalityListResponse)
async def list_ops_personalities(
    keyword: str = Query(""),
    buff_stat: str = Query(""),   # hp/phy_atk/mag_atk/phy_def/mag_def/spd
    nerf_stat: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),   # 总共 30 条，默认一次拉完
    current_user: dict = Depends(get_current_ops_user),
):
    return await personality_service.list_personalities_for_ops(
        current_user, keyword=keyword,
        buff_stat=buff_stat, nerf_stat=nerf_stat,
        page=page, page_size=page_size,
    )

@router.get("/personalities/{pid}", response_model=PersonalityItem)
async def get_ops_personality(pid: int, current_user=Depends(get_current_ops_user)):
    return await personality_service.get_personality_for_ops(current_user, pid)

@router.post("/personalities", response_model=PersonalityItem)
async def create_ops_personality(
    payload: PersonalityUpsertRequest,
    current_user=Depends(get_current_ops_user),
):
    return await personality_service.create_personality_for_ops(current_user, payload.model_dump())

@router.put("/personalities/{pid}", response_model=PersonalityItem)
async def update_ops_personality(
    pid: int,
    payload: PersonalityUpsertRequest,
    current_user=Depends(get_current_ops_user),
):
    return await personality_service.update_personality_for_ops(current_user, pid, payload.model_dump())

@router.delete("/personalities/{pid}", status_code=204)
async def delete_ops_personality(pid: int, current_user=Depends(get_current_ops_user)):
    await personality_service.delete_personality_for_ops(current_user, pid)
    return Response(status_code=204)

@router.post("/personalities/reset", response_model=PersonalityResetResponse)
async def reset_ops_personalities(current_user=Depends(get_current_ops_user)):
    """从 docs/pets/personalities.json 全量覆盖（admin）。"""
    return await personality_service.reset_personalities_from_json(current_user)
```

### 3.5 权限矩阵

| 操作 | viewer | editor | admin |
| --- | :-: | :-: | :-: |
| GET 列表 / 详情 | ✅ | ✅ | ✅ |
| PUT 更新 | ❌ | ✅ | ✅ |
| POST 新增 | ❌ | ❌ | ✅ |
| DELETE 删除 | ❌ | ❌ | ✅ |
| POST /reset | ❌ | ❌ | ✅ |

### 3.6 审计日志

沿用 `ops_repository.create_audit_log`，`resource_type = "personality"`，动作 `create / update / delete / reset`。`reset` 的 `after_json` 记录 `{inserted: N, source: "json"}` 即可。

---

## 4. 前端（`front/pc-front`）

### 4.1 新增文件

- `src/api/ops.ts`：追加
  ```ts
  export const listOpsPersonalities = (params) => http.get('/api/ops/personalities', { params })
  export const getOpsPersonality    = (id) => http.get(`/api/ops/personalities/${id}`)
  export const updateOpsPersonality = (id, body) => http.put(`/api/ops/personalities/${id}`, body)
  export const createOpsPersonality = (body) => http.post('/api/ops/personalities', body)
  export const deleteOpsPersonality = (id) => http.delete(`/api/ops/personalities/${id}`)
  export const resetOpsPersonalities = () => http.post('/api/ops/personalities/reset')
  ```
- `src/views/ops/OpsPersonalitiesView.vue`：新增页面。
- 在 `OpsLayoutView.vue` 的侧边菜单加一项「性格管理」，路由路径 `/ops/personalities`。
- 路由表（`router/index.ts` 或同级 ops 子路由文件）注册该视图。

### 4.2 页面 UX（参考 `OpsDictsView.vue` / `OpsBannersView.vue`）

- 顶部筛选条：中/英文关键字、buff 六维下拉、nerf 六维下拉、「重置为 JSON」按钮（admin 可见）。
- 主体：`el-table`（或同项目使用的表格组件），列：
  - ID / 中文名 / 英文名 / **buff 项**（高亮 +10%）/ **nerf 项**（灰色 -10%）/ 其余六维修正数值（紧凑展示）/ 操作。
- 编辑：行内点击「编辑」→ 抽屉 Drawer：
  - 姓名字段；
  - **六维修正用统一的 3 档 radio / segmented**：`-10% / 0 / +10%`（而不是自由输入 float，避免脏数据）；
  - 实时计算并预览 "主加 / 主减"；
  - 提交前前端也复用同一份规则做校验，提示但不强拦。
- 新增（admin）：弹窗必须手填 `id`（1–999）。
- 删除（admin）：二次确认，未来有引用时展示"被 N 个精灵实例使用"。

### 4.3 国际化 / 文案

- 六维字段统一用项目已有缩写：`HP / 物攻 / 魔攻 / 物防 / 魔防 / 速度`。
- "buff_stat / nerf_stat" 对前端只暴露中文标签，内部 code 用 `hp / phy_atk / mag_atk / phy_def / mag_def / spd`。

---

## 5. 对外（公共）接口

性格字典在 C 端（图鉴/计算器）也需要，只读接口建议另外加在 `api/routes/pokemon.py`：

```python
@router.get("/personalities", response_model=list[PersonalityItem])
async def list_personalities_public():
    return await personality_service.list_personalities_public()
```

前端计算器页面可直接拉取，无需鉴权。

---

## 6. 测试 & 上线步骤

1. `uv run python scripts/import_personalities.py --dry-run` 验证数据，再去掉 `--dry-run` 正式写入。
2. `uv run python -m compileall api` 保证无语法错。
3. `uv run uvicorn api.main:app --reload --port 8000` 启动后：
   - `GET /api/ops/personalities`（带 token）返回 30 条；
   - `PUT /api/ops/personalities/1` 改名，核对 `ops_audit_log` 有一条 update 记录。
4. 前端 `npm run type-check && npm run build` 通过。
5. 生产环境执行顺序：
   1. 执行 SQL：`sql/wikiroco.sql` 的 `personality` DDL（或直接跑 `import_personalities.py --only pg`）；
   2. 发布后端；
   3. 发布前端。

---

## 7. 未来扩展

- `pokemon_instance.personality_id` 外键落地后，删除/修改要检查引用。
- 若新增 6 个"全中性"性格（Hardy / Docile / Serious* / Bashful / Quirky / 自定义），id 用 31–36。
- 可在 ops 页增加**一键导出当前库 → JSON**，保证 `docs/pets/personalities.json` 与库一致。
