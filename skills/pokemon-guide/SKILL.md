---
name: pokemon-guide
description: 洛克王国精灵图鉴查询技能。提供精灵详情、技能搜索、进化链、体型匹配、地图点位等游戏数据的 API 接口规范。Agent 应通过 call_api 工具按本文档描述的端点发起请求。
---

# Pokemon Guide — 洛克王国精灵图鉴 API

本 Skill 定义了洛克王国精灵图鉴后端的全部 API 接口规范。
Agent 应根据用户问题，选择合适的端点，通过 **call_api** 工具发起请求。

**Base URL：** 由环境变量 `POKEMON_API_BASE_URL` 配置，默认 `http://localhost:8000`
**所有接口均为 GET 请求，路径前缀 `/api`**

---

## 名词解释
- 首领化:对首领血脉的精灵使用，可以使该精灵在本场战斗中进化，部分精灵会激活远古血脉。
- 愿力强化: 可以将精灵的第一个技能替换成愿力冲击，属性则是跟精灵血脉相同，如果敌人同时使用状态技能伤害翻倍

## 使用场景

当用户：

- 询问某只精灵的详情（"迪莫的种族值是多少？"）
- 查询精灵的进化链或进化条件
- 按属性、蛋组或种族值筛选/排序精灵
- 查询某个技能的属性、威力、描述
- 想知道某技能石的获取方式
- 输入身高体重，想知道自己和哪只精灵体型相近，如果用户发来两个毫无意义的float类型数据，优先考虑用户在查询相似精灵，数值小的通常为身高 单位m
- 查询精灵出现在地图上的哪些点位
- 当用户询问精灵强度相关的问题时 需要从种族值、技能打击面、属性克制关系和特性效果综合考虑
- pvp配队的时候通常是六只宠物，需要考虑种族值、技能打击面、属性克制关系和特性效果以及可以切换宠物联防等方面

---

## 接口列表

### 1. 精灵详情

**`GET /api/pokemon/{pokemon_name}`**

查询单只精灵的完整详情：基础信息、种族值、特性、属性克制、技能列表。

调用示例：
```
call_api(method="GET", path="/api/pokemon/迪莫")
```

返回字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| no | str | 图鉴编号 |
| name | str | 精灵名称 |
| image_url | str | 精灵图片 |
| attributes | list | 属性列表 `[{attr_name, attr_image}]` |
| egg_groups | list | 蛋组列表 |
| obtain_method | str | 获取方式 |
| stats | object | 种族值 `{hp, atk, matk, def_val, mdef, spd}` |
| trait | object | 特性 `{name, desc}` |
| restrain | object | 属性克制 `{strong_against, weak_against, resist, resisted}` |
| skills | list | 可学习技能列表 |
| defensive_type_chart | object | 防御属性倍率表 |

错误：精灵不存在时返回 `404`。

---

### 2. 精灵列表（分页搜索）

**`GET /api/pokemon`**

分页查询精灵，支持多维度筛选与排序。

调用示例：
```
call_api(method="GET", path="/api/pokemon", params={"name": "皮卡", "order_by": "total_stats", "order_dir": "desc", "page_size": 10})
```

查询参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | str | `""` | 名称关键词（模糊匹配） |
| attr | list[str] | - | 属性多选（AND），重复传参：`{"attr": ["草", "火"]}` |
| egg_group | list[str] | - | 蛋组多选（AND），重复传参 |
| order_by | str | `"no"` | 排序字段：`no`/`total_stats`/`hp`/`atk`/`matk`/`def_val`/`mdef`/`spd` |
| order_dir | str | `"asc"` | 排序方向：`asc`/`desc` |
| page | int | `1` | 页码 |
| page_size | int | `30` | 每页数量（1~100） |

返回：`{total, page, page_size, items: [...]}`

---

### 3. 进化链

**`GET /api/pokemon/evolution-chain/{pokemon_name}`**

查询精灵所在的完整进化链，按阶段返回。

调用示例：
```
call_api(method="GET", path="/api/pokemon/evolution-chain/迪莫")
```

返回：`{chain_id, stages: [{sort_order, next_condition, items: [{name, image_url}]}]}`

错误：精灵不存在时返回 `404`。

---

### 4. 体型匹配

**`GET /api/pokemon/body-match`**

根据身高（m）和体重（kg）查询体型相近的精灵。如果用户未说明具体单位默认身高是m 体重是kg

调用示例：
```
call_api(method="GET", path="/api/pokemon/body-match", params={"height_m": 1.7, "weight_kg": 60.0})
```

查询参数（必填）：

| 参数 | 类型 | 说明 |
|------|------|------|
| height_m | float | 身高（米） |
| weight_kg | float | 体重（千克） |

返回：`{height_m, weight_kg, height_cm, weight_g, total, items: [{pet_name, image_url}]}`

---

### 5. 技能搜索

**`GET /api/skills`**

查询技能列表，支持名称模糊搜索、按类型和属性筛选（条件之间 AND）。

调用示例：
```
call_api(method="GET", path="/api/skills", params={"attr": "火", "skill_type": "物攻"})
```

查询参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | str | `""` | 技能名关键词（模糊匹配） |
| skill_type | str | `""` | 类型：`物攻`/`魔攻`/`状态`/`防御` |
| attr | str | `""` | 属性：`草`/`火`/`水` 等 |

返回：`{total, items: [{name, attr, power, type, consume, desc, icon}]}`

---

### 6. 技能石

**`GET /api/skill-stones`**

查询技能石及获取方式。不传参返回全部。

调用示例：
```
call_api(method="GET", path="/api/skill-stones", params={"skill_name": "藤鞭"})
```

查询参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| skill_name | str | `""` | 技能名关键词（模糊匹配） |

返回：`{total, items: [{skill_name, obtain_method, icon}]}`

---

### 7. 属性列表

**`GET /api/attributes`**

返回所有精灵属性及图标。

调用示例：
```
call_api(method="GET", path="/api/attributes")
```

返回：`[{attr_name, attr_image}]`

---

### 8. 蛋组列表

**`GET /api/egg-groups`**

返回所有蛋组名称。

调用示例：
```
call_api(method="GET", path="/api/egg-groups")
```

返回：`["陆地", "水中1", "精灵", ...]`

---

### 9. 技能类型

**`GET /api/skill-types`**

返回所有技能类型。

调用示例：
```
call_api(method="GET", path="/api/skill-types")
```

返回：`["物攻", "魔攻", "状态", "防御"]`

---

### 10. 精灵分类

**`GET /api/pokemon/categories`**

返回 category 表全量数据。

调用示例：
```
call_api(method="GET", path="/api/pokemon/categories")
```

返回：`[{id, category_id, description, type, category_image_url}]`

---

### 11. 地图点位

**`GET /api/pokemon/map-points`**

返回全部地图出现点位。

调用示例：
```
call_api(method="GET", path="/api/pokemon/map-points")
```

返回：`[{id, source_id, map_id, title, latitude, longitude, category_id, category_image_url}]`
