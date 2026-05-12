# 洛克王国精灵图鉴 API 接口文档

**Base URL（开发）：** `http://localhost:8000`  
**所有接口均为 GET 请求，前缀 `/api`**（除 `POST /api/battle-pk` 外）

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
      "source": "初始",
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
| shiny_only | bool | `false` | 仅返回有异色形态的精灵 |
| order_by | str | `"no"` | 排序字段：`no`/`total_stats`/`hp`/`atk`/`matk`/`def_val`/`mdef`/`spd` |
| order_dir | str | `"asc"` | 排序方向：`asc`/`desc` |
| filter_code | list[str] | `null` | 预设筛选器编码（覆盖 shiny_only/order_by/order_dir），重复传参。编码来自 `/api/pokemon-filter-options` |
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
      "id": 1,
      "no": "001",
      "name": "妙蛙种子",
      "image_url": "https://...",
      "image_yise_url": "https://...",
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
      "pre_condition": "",
      "items": [{ "name": "皮丘", "image_url": "https://..." }]
    },
    {
      "sort_order": 2,
      "next_condition": "持有雷之石",
      "pre_condition": "等级25",
      "items": [{ "name": "皮卡丘", "image_url": "https://..." }]
    },
    {
      "sort_order": 3,
      "next_condition": "",
      "pre_condition": "持有雷之石",
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
| id | int | 主键 |
| no | str | 图鉴编号 |
| name | str | 精灵名称 |
| image_url | str | 普通形态图片 |
| image_yise_url | str | 异色形态图片 |
| type | str | 系别代码 |
| type_name | str | 系别中文名 |
| form | str | 形态代码 |
| form_name | str | 形态中文名 |
| attributes | list | 属性列表 `[{attr_name, attr_image}]` |
| egg_groups | list | 蛋组列表 |
| obtain_method | str | 获取方式 |
| stats | object | 种族值 `{hp, atk, matk, def_val, mdef, spd}` |
| trait | object | 特性 `{name, desc}` |
| restrain | object | 属性克制关系 `{strong_against, weak_against, resist, resisted}` |
| skills | list | 技能列表，同 `/api/skills` 的 item 结构，额外包含 `source` 字段 |
| defensive_type_chart | object | 防御属性倍率表 |

**响应示例：**
```json
{
  "id": 25,
  "no": "025",
  "name": "皮卡丘",
  "image_url": "https://...",
  "image_yise_url": "https://...",
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
  "skills": [
    {
      "name": "电击",
      "attr": "电",
      "power": 40,
      "type": "魔攻",
      "source": "初始",
      "consume": 30,
      "desc": "发出电流攻击对手",
      "icon": "https://..."
    }
  ],
  "defensive_type_chart": {
    "defender_attrs": ["电"],
    "cells": [
      { "attacker_attr": "地面", "multiplier": 2.0, "label": "2×", "bucket": "weak" }
    ]
  }
}
```

---

## 12. Banner 轮播图

### `GET /api/banners`

返回首页或活动页的 Banner 轮播图列表。

**响应示例：**
```json
[
  {
    "id": 1,
    "title": "星光对决",
    "image_url": "https://...",
    "link_type": "lineup",
    "link_param": "1",
    "link_extra": "",
    "sort_order": 1,
    "is_active": true
  }
]
```

---

## 13. 星光对决最新阵容

### `GET /api/starlight-duel/latest`

获取星光对决玩法的最新推荐阵容。

**响应示例：**
```json
{
  "id": 1,
  "title": "星光对决推荐阵容",
  "lineup_desc": "当前版本强势阵容",
  "source_type": "starlight_duel",
  "resonance_magic_id": null,
  "resonance_magic_name": "",
  "resonance_magic_icon": "",
  "sort_order": 1,
  "is_active": true,
  "members": [
    {
      "id": 1,
      "pokemon_id": 100,
      "pokemon_name": "迪莫",
      "pokemon_image": "https://...",
      "sort_order": 1,
      "bloodline_dict_id": 1,
      "bloodline_label": "首领血脉",
      "personality_id": 3,
      "personality_name_zh": "固执",
      "qual_1": "SS",
      "qual_2": "SS",
      "qual_3": "SS",
      "skill_1_id": 10,
      "skill_1_name": "光芒斩",
      "skill_1_image": "https://...",
      "skill_2_id": 20,
      "skill_2_name": "光之盾",
      "skill_2_image": "https://...",
      "skill_3_id": 30,
      "skill_3_name": "圣光冲击",
      "skill_3_image": "https://...",
      "skill_4_id": 40,
      "skill_4_name": "愈合",
      "skill_4_image": "https://...",
      "member_desc": ""
    }
  ]
}
```

---

### `GET /api/starlight-duel/{lineup_id}`

根据 ID 查看某套星光对决阵容详情。结构与 `/latest` 相同。

**错误响应：** `404 { "detail": "阵容不存在" }`

---

## 14. 精灵阵容

### `GET /api/pokemon-lineups`

分页查询 PVP 精灵阵容。

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| source_type | str | `""` | 阵容分类筛选 |
| ids | list[int] | `[]` | 按 ID 精确筛选 |

**响应：** `{ items: [阵容详情数组] }`，阵容详情结构与星光对决阵容相同。

---

### `GET /api/pokemon-lineups/{lineup_id}`

根据 ID 查看某套阵容详情。

**错误响应：** `404 { "detail": "阵容不存在" }`

---

## 15. 血脉列表

### `GET /api/bloodlines`

返回所有血脉选项。

**响应示例：**
```json
[
  { "id": 1, "code": "leader", "label": "首领血脉" },
  { "id": 2, "code": "ancient", "label": "远古血脉" }
]
```

---

## 16. 共鸣魔法列表

### `GET /api/resonance-magics`

返回所有共鸣魔法选项。

**响应示例：**
```json
[
  {
    "id": 1,
    "name": "愿力冲击",
    "description": "将第一个技能替换为愿力冲击，属性与精灵血脉相同",
    "icon_url": "https://...",
    "max_usage_count": 2
  }
]
```

---

## 17. 性格列表

### `GET /api/personalities`

返回所有性格及其种族值修正。

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 性格 ID |
| name | str | 性格名称 |
| hp_mod_pct | float | HP 修正百分比 |
| phy_atk_mod_pct | float | 物攻修正百分比 |
| mag_atk_mod_pct | float | 魔攻修正百分比 |
| phy_def_mod_pct | float | 物防修正百分比 |
| mag_def_mod_pct | float | 魔防修正百分比 |
| spd_mod_pct | float | 速度修正百分比 |
| buff_stat | str\|null | 提升的属性名 |
| nerf_stat | str\|null | 降低的属性名 |
| is_neutral | bool | 是否为平衡性格（无修正） |

**响应示例：**
```json
[
  {
    "id": 1,
    "name": "固执",
    "hp_mod_pct": 1.0,
    "phy_atk_mod_pct": 1.1,
    "mag_atk_mod_pct": 0.9,
    "phy_def_mod_pct": 1.0,
    "mag_def_mod_pct": 1.0,
    "spd_mod_pct": 1.0,
    "buff_stat": "phy_atk",
    "nerf_stat": "mag_atk",
    "is_neutral": false
  }
]
```

---

## 18. 精灵蛋

### `GET /api/pokemon-eggs`

分页查询精灵蛋信息。

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | str | `""` | 精灵名称关键词（模糊匹配） |
| page | int | `1` | 页码（≥1） |
| page_size | int | `30` | 每页数量（1~100） |

**响应示例：**
```json
{
  "total": 5,
  "page": 1,
  "page_size": 30,
  "items": [
    {
      "id": 1,
      "source_id": 1001,
      "name": "迪莫",
      "form": "normal",
      "icon": "https://...",
      "pokemon_source_id": 100,
      "pokemon_id": 1,
      "pokemon_name": "迪莫",
      "item_quality": 3,
      "created_at": "2026-01-01T00:00:00",
      "updated_at": "2026-01-01T00:00:00"
    }
  ]
}
```

---

## 19. 精灵果实

### `GET /api/pokemon-fruits`

分页查询精灵果实信息。

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | str | `""` | 精灵名称关键词（模糊匹配） |
| page | int | `1` | 页码（≥1） |
| page_size | int | `30` | 每页数量（1~100） |

**响应示例：**
```json
{
  "total": 3,
  "page": 1,
  "page_size": 30,
  "items": [
    {
      "id": 1,
      "source_id": 2001,
      "name": "迪莫",
      "icon": "https://...",
      "pokemon_source_id": 100,
      "item_quality": 2,
      "created_at": "2026-01-01T00:00:00",
      "updated_at": "2026-01-01T00:00:00"
    }
  ]
}
```

---

## 20. 精灵标记

### `GET /api/pokemon-marks`

返回所有精灵标记/成就。

**响应示例：**
```json
[
  {
    "id": 1,
    "key": "legendary",
    "zh_name": "传说精灵",
    "zh_description": "传说级别的稀有精灵",
    "sort_order": 1,
    "image": "https://..."
  }
]
```

---

## 21. 精灵筛选选项

### `GET /api/pokemon-filter-options`

返回预设的筛选器选项，其 `code` 可用于 `/api/pokemon` 的 `filter_code` 参数。

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| code | str | 编码（传入 `/api/pokemon` 的 filter_code） |
| label | str | 显示名称 |
| filter_type | str | `"shiny"`（仅异色）或 `"sort"`（排序方式） |
| order_by | str | 对应的排序字段 |
| order_dir | str | 对应的排序方向 |
| sort_order | int | 显示排序 |

**响应示例：**
```json
[
  { "id": 1, "code": "shiny", "label": "仅异色", "filter_type": "shiny", "order_by": "", "order_dir": "", "sort_order": 1 },
  { "id": 2, "code": "total_desc", "label": "种族值从高到低", "filter_type": "sort", "order_by": "total_stats", "order_dir": "desc", "sort_order": 2 }
]
```

---

## 22. 随机精灵模式

### `GET /api/battle-pk/random-pokemon-modes`

返回 PVP 对战中随机精灵的可用模式选项。

**响应示例：**
```json
[
  { "id": 1, "code": "any", "label": "任意精灵", "kind": "any", "bloodline_code": null },
  { "id": 2, "code": "fire_random", "label": "火系随机", "kind": "attr", "bloodline_code": "fire" }
]
```

---

## 23. 战斗 PK 分析

### `POST /api/battle-pk`

提交两队精灵阵容，进行同步 PVP 对战分析。

**请求体：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| team_a | object | 是 | A 队阵容 |
| team_a.title | str | 否 | 队伍名称 |
| team_a.lineup_desc | str | 否 | 队伍描述 |
| team_a.source_type | str | 否 | 来源分类 |
| team_a.resonance_magic_id | int\|null | 否 | 共鸣魔法 ID |
| team_a.resonance_magic_name | str | 否 | 共鸣魔法名称 |
| team_a.members | list | 是 | 队员列表（最多 6 个） |
| team_a.members[].pokemon_id | int\|null | 否 | 精灵 ID |
| team_a.members[].pokemon_name | str | 是 | 精灵名称 |
| team_a.members[].sort_order | int | 是 | 排序 |
| team_a.members[].bloodline_dict_id | int\|null | 否 | 血脉字典 ID |
| team_a.members[].bloodline_label | str | 否 | 血脉标签 |
| team_a.members[].personality_id | int\|null | 否 | 性格 ID |
| team_a.members[].personality_name_zh | str | 否 | 性格中文名 |
| team_a.members[].qual_1 | str | 否 | 品质 1 |
| team_a.members[].qual_2 | str | 否 | 品质 2 |
| team_a.members[].qual_3 | str | 否 | 品质 3 |
| team_a.members[].skill_1_id ~ skill_4_id | int\|null | 否 | 技能 ID |
| team_a.members[].skill_1_name ~ skill_4_name | str | 否 | 技能名称 |
| team_a.members[].member_desc | str | 否 | 备注 |
| team_b | object | 是 | B 队阵容（结构同 team_a） |

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| completeness | object | 阵容完整度 `{ok, missing}` |
| plan | object | 出战计划 `{team_a_order, team_a_order_reason, team_b_order, team_b_order_reason, skill_matchup, ability_impact}` |
| team_a | object | A 队分析 `{summary, advantages, weaknesses}` |
| team_b | object | B 队分析 `{summary, advantages, weaknesses}` |
| key_rounds | list | 关键回合 `[{round, desc}]` |
| turning_points | list[str] | 转折点 |
| verdict | object | 判定 `{winner ("DRAW"/"A"/"B"), win_rate_a (int), reason}` |
| error | str | 错误信息 |
| raw | str | 原始分析文本 |

**请求示例：**
```json
{
  "team_a": {
    "title": "队伍A",
    "members": [
      {
        "pokemon_name": "迪莫",
        "sort_order": 1,
        "bloodline_label": "首领血脉",
        "personality_name_zh": "固执",
        "qual_1": "SS",
        "qual_2": "SS",
        "qual_3": "SS",
        "skill_1_name": "光芒斩",
        "skill_2_name": "光之盾",
        "skill_3_name": "圣光冲击",
        "skill_4_name": "愈合",
        "member_desc": ""
      }
    ],
    "resonance_magic_id": null,
    "resonance_magic_name": ""
  },
  "team_b": {
    "title": "队伍B",
    "members": [
      {
        "pokemon_name": "喵喵",
        "sort_order": 1,
        "bloodline_label": "普通血脉",
        "personality_name_zh": "开朗",
        "qual_1": "S",
        "qual_2": "S",
        "qual_3": "S",
        "skill_1_name": "抓击",
        "skill_2_name": "电光一闪",
        "skill_3_name": "咬住",
        "skill_4_name": "吼叫",
        "member_desc": ""
      }
    ],
    "resonance_magic_id": null,
    "resonance_magic_name": ""
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
