# 洛克王国精灵图鉴 API 接口文档

**Base URL（开发）：** `http://localhost:8000`  
**所有接口均为 GET 请求，前缀 `/api`**

---

## 1. 属性列表

### `GET /api/attributes`

返回所有不重复的精灵属性，含属性图标。

**响应示例：**
```json
[
  { "attr_name": "草", "attr_image": "https://..." },
  { "attr_name": "火", "attr_image": "https://..." }
]
```

---

## 2. 蛋组列表

### `GET /api/egg-groups`

返回所有不重复蛋组名称，用于筛选繁殖相关精灵。

**响应示例：**
```json
["陆地", "水中1", "精灵"]
```

---

## 3. 精灵分类（category）

### `GET /api/pokemon/categories`

返回 category 表全量数据，含 category_id 及其图标地址。

**响应示例：**
```json
[
  {
    "id": 1,
    "category_id": 101,
    "description": "野生精灵",
    "type": "wild",
    "category_image_url": "https://..."
  }
]
```

---

## 4. 地图点位

### `GET /api/pokemon/map-points`

返回全部地图出现点位，已补全 category_id 对应图标地址。

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| source_id | int | 原始 ID |
| map_id | int | 所属地图 ID |
| title | str | 点位标题 |
| latitude | float | 纬度 |
| longitude | float | 经度 |
| category_id | int | 分类 ID |
| category_image_url | str | 分类图标 URL |

---

## 5. 技能石

### `GET /api/skill-stones`

按技能名查询技能石；不传参则返回全部。

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| skill_name | str | `""` | 技能名关键词（模糊匹配），空则返回全部 |

**响应示例：**
```json
{
  "total": 2,
  "items": [
    { "skill_name": "藤鞭", "obtain_method": "商城购买", "icon": "https://..." }
  ]
}
```

---

## 6. 技能类型

### `GET /api/skill-types`

返回所有不重复的技能类型。

**响应示例：**
```json
["物攻", "魔攻", "状态", "防御"]
```

---

## 7. 技能列表

### `GET /api/skills`

查询技能列表，支持名称模糊搜索、按类型和属性筛选，条件之间为 AND。

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | str | `""` | 技能名关键词（模糊匹配） |
| skill_type | str | `""` | 技能类型：物攻/魔攻/状态/防御 |
| attr | str | `""` | 技能属性：草/火/水 等 |

**响应示例：**
```json
{
  "total": 10,
  "items": [
    {
      "name": "藤鞭",
      "attr": "草",
      "power": 45,
      "type": "物攻",
      "consume": 15,
      "desc": "用藤蔓抽打对手",
      "icon": "https://..."
    }
  ]
}
```

---

## 8. 精灵列表（分页）

### `GET /api/pokemon`

分页查询精灵，支持多维度筛选与排序；所有筛选条件之间为 AND。

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | str | `""` | 精灵名称关键词（模糊匹配） |
| attr | list[str] | `null` | 属性多选（AND，需同时命中），重复传参：`attr=草&attr=火` |
| egg_group | list[str] | `null` | 蛋组多选（AND），重复传参 |
| order_by | str | `"no"` | 排序字段：`no`/`total_stats`/`hp`/`atk`/`matk`/`def_val`/`mdef`/`spd` |
| order_dir | str | `"asc"` | 排序方向：`asc`/`desc` |
| page | int | `1` | 页码（≥1） |
| page_size | int | `30` | 每页数量（1~100） |

**响应示例：**
```json
{
  "total": 300,
  "page": 1,
  "page_size": 30,
  "items": [
    {
      "no": "001",
      "name": "妙蛙种子",
      "image_url": "https://...",
      "type": "grass",
      "type_name": "草系",
      "form": "normal",
      "form_name": "普通",
      "attributes": [{ "attr_name": "草", "attr_image": "https://..." }],
      "egg_groups": ["陆地", "怪物"]
    }
  ]
}
```

---

## 9. 体型匹配

### `GET /api/pokemon/body-match`

根据用户输入的身高和体重，查询区间内可命中的精灵。

**查询参数（必填）：**

| 参数 | 类型 | 说明 |
|------|------|------|
| height_m | float | 身高，单位 m（>0） |
| weight_kg | float | 体重，单位 kg（>0） |

**响应示例：**
```json
{
  "height_m": 1.7,
  "weight_kg": 60.0,
  "height_cm": 170,
  "weight_g": 60000,
  "total": 3,
  "items": [
    { "pet_name": "皮卡丘", "image_url": "https://..." }
  ]
}
```

---

## 10. 进化链

### `GET /api/pokemon/evolution-chain/{pokemon_name}`

查询某只精灵所在的完整进化链，按阶段返回每层的所有形态。

**路径参数：**

| 参数 | 说明 |
|------|------|
| pokemon_name | 精灵名称，如 `皮卡丘` |

**错误响应：** `404 { "detail": "精灵不存在" }`

**响应示例：**
```json
{
  "chain_id": 5,
  "stages": [
    {
      "sort_order": 1,
      "next_condition": "等级25",
      "items": [{ "name": "皮丘", "image_url": "https://..." }]
    },
    {
      "sort_order": 2,
      "next_condition": "持有雷之石",
      "items": [{ "name": "皮卡丘", "image_url": "https://..." }]
    },
    {
      "sort_order": 3,
      "next_condition": "",
      "items": [{ "name": "雷丘", "image_url": "https://..." }]
    }
  ]
}
```

---

## 11. 精灵详情

### `GET /api/pokemon/{pokemon_name}`

查询单只精灵的完整详情：基础信息、种族值、特性、属性克制、技能列表。

**路径参数：**

| 参数 | 说明 |
|------|------|
| pokemon_name | 精灵名称，如 `皮卡丘` |

**错误响应：** `404 { "detail": "精灵不存在" }`

**响应字段（在 PokemonListItem 基础上扩展）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| obtain_method | str | 获取方式 |
| stats | object | 种族值 `{hp, atk, matk, def_val, mdef, spd}` |
| trait | object | 特性 `{name, desc}` |
| restrain | object | 属性克制关系 `{strong_against, weak_against, resist, resisted}` |
| skills | list | 技能列表，同 `/api/skills` 的 item 结构 |
| defensive_type_chart | object | 防御属性倍率表 |

**响应示例：**
```json
{
  "no": "025",
  "name": "皮卡丘",
  "image_url": "https://...",
  "type": "electric",
  "type_name": "电系",
  "form": "normal",
  "form_name": "普通",
  "attributes": [{ "attr_name": "电", "attr_image": "https://..." }],
  "egg_groups": ["野兽"],
  "obtain_method": "野外捕捉",
  "stats": { "hp": 35, "atk": 55, "matk": 50, "def_val": 40, "mdef": 50, "spd": 90 },
  "trait": { "name": "静电", "desc": "接触时有30%概率令对方麻痹" },
  "restrain": {
    "strong_against": ["水", "飞行"],
    "weak_against": ["地面"],
    "resist": ["电", "飞行", "钢"],
    "resisted": ["地面"]
  },
  "skills": [...],
  "defensive_type_chart": {
    "defender_attrs": ["电"],
    "cells": [
      { "attacker_attr": "地面", "multiplier": 2.0, "label": "2×", "bucket": "weak" }
    ]
  }
}
```

---

## 接口路由顺序说明

FastAPI 按声明顺序匹配路由。以下路由需**先于** `GET /api/pokemon/{pokemon_name}` 注册，否则会被捕获为精灵名：

- `GET /api/pokemon/categories`
- `GET /api/pokemon/map-points`
- `GET /api/pokemon/body-match`
- `GET /api/pokemon/evolution-chain/{pokemon_name}`
