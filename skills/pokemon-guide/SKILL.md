---
name: pokemon-guide
description: 洛克王国精灵图鉴查询技能。提供精灵详情、技能搜索、进化链、体型匹配、地图点位、阵容、PVP对战分析、血脉、共鸣魔法、性格等游戏数据的 API 接口规范。Agent 应通过 call_api 工具按本文档描述的端点发起请求。
---

# Pokemon Guide — 洛克王国精灵图鉴 API

本 Skill 定义了洛克王国精灵图鉴后端的全部 API 接口规范。
Agent 应根据用户问题，选择合适的端点，通过 **call_api** 工具发起请求。

**Base URL：** 由环境变量 `POKEMON_API_BASE_URL` 配置，默认 `http://localhost:8000`
**所有接口均为 GET 请求，路径前缀 `/api`**（除 `POST /api/battle-pk` 外）

---

## 名词解释
- 首领化:对首领血脉的精灵使用，可以使该精灵在本场战斗中进化，部分精灵会激活远古血脉。
- 愿力强化: 可以将精灵的第一个技能替换成愿力冲击，属性则是跟精灵血脉相同，如果敌人同时使用状态技能伤害翻倍
- 血脉: 精灵的被动特性系统，不同血脉提供不同的战斗加成
- 共鸣魔法: 队伍共享的主动技能，每场战斗有使用次数上限
- 性格: 影响精灵种族值，提升一项属性并降低另一项
- 星光对决: 游戏内的 PVP 对战玩法

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
- 询问精灵蛋信息（"XX精灵的蛋是什么？"）
- 查询精灵果实信息
- 查询精灵标记/成就
- 查询血脉信息或血脉效果
- 查询共鸣魔法信息
- 查询性格及其属性加成
- 分析两支队伍的 PVP 对战优劣
- 获取当前推荐的 PVP 阵容
- 查询 Banner/活动轮播图
- 查询精灵筛选器选项（仅异色、排序方式等）

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
| image_yise_url | str | 异色精灵图片 |
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
| shiny_only | bool | `false` | 仅返回有异色形态的精灵 |
| order_by | str | `"no"` | 排序字段：`no`/`total_stats`/`hp`/`atk`/`matk`/`def_val`/`mdef`/`spd` |
| order_dir | str | `"asc"` | 排序方向：`asc`/`desc` |
| filter_code | list[str] | - | 预设筛选器编码（覆盖 shiny_only/order_by/order_dir），来自 `/api/pokemon-filter-options` |
| page | int | `1` | 页码 |
| page_size | int | `30` | 每页数量（1~100） |

返回：`{total, page, page_size, items: [{id, no, name, image_url, image_yise_url, type, type_name, form, form_name, attributes, egg_groups}]}`

---

### 3. 进化链

**`GET /api/pokemon/evolution-chain/{pokemon_name}`**

查询精灵所在的完整进化链，按阶段返回。

调用示例：
```
call_api(method="GET", path="/api/pokemon/evolution-chain/迪莫")
```

返回：`{chain_id, stages: [{sort_order, next_condition, pre_condition, items: [{name, image_url}]}]}`

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

返回：`{total, items: [{name, attr, power, type, source, consume, desc, icon}]}`

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

---

### 12. Banner 轮播图

**`GET /api/banners`**

返回首页或活动页的 Banner 轮播图列表。

调用示例：
```
call_api(method="GET", path="/api/banners")
```

返回：`[{id, title, image_url, link_type, link_param, link_extra, sort_order, is_active}]`

---

### 13. 星光对决最新阵容

**`GET /api/starlight-duel/latest`**

获取星光对决玩法的最新推荐阵容。

调用示例：
```
call_api(method="GET", path="/api/starlight-duel/latest")
```

返回：`{id, title, lineup_desc, source_type, resonance_magic_id, resonance_magic_name, resonance_magic_icon, sort_order, is_active, members: [{id, pokemon_id, pokemon_name, pokemon_image, sort_order, bloodline_dict_id, bloodline_label, personality_id, personality_name_zh, qual_1, qual_2, qual_3, skill_1_id, skill_1_name, skill_1_image, ..., skill_4_id, skill_4_name, skill_4_image, member_desc}]}`

---

### 14. 星光对决阵容详情

**`GET /api/starlight-duel/{lineup_id}`**

根据 ID 查看某套星光对决阵容详情。

调用示例：
```
call_api(method="GET", path="/api/starlight-duel/1")
```

返回：与 `/api/starlight-duel/latest` 结构相同。不存在时返回 `404`。

---

### 15. 精灵阵容列表

**`GET /api/pokemon-lineups`**

分页查询 PVP 精灵阵容，支持按来源类型筛选。

调用示例：
```
call_api(method="GET", path="/api/pokemon-lineups", params={"source_type": "starlight_duel"})
```

查询参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| source_type | str | `""` | 阵容分类筛选 |
| ids | list[int] | `[]` | 按 ID 精确筛选 |

返回：`{items: [阵容详情数组]}`，其中阵容详情结构与星光对决阵容相同。

---

### 16. 精灵阵容详情

**`GET /api/pokemon-lineups/{lineup_id}`**

根据 ID 查看某套阵容详情。

调用示例：
```
call_api(method="GET", path="/api/pokemon-lineups/1")
```

返回：阵容详情对象，不存在时返回 `404`。

---

### 17. 血脉列表

**`GET /api/bloodlines`**

返回所有血脉选项，用于 PVP 配队。

调用示例：
```
call_api(method="GET", path="/api/bloodlines")
```

返回：`[{id, code, label}]`

---

### 18. 共鸣魔法列表

**`GET /api/resonance-magics`**

返回所有共鸣魔法选项。

调用示例：
```
call_api(method="GET", path="/api/resonance-magics")
```

返回：`[{id, name, description, icon_url, max_usage_count}]`

---

### 19. 性格列表

**`GET /api/personalities`**

返回所有性格及其属性加成。

调用示例：
```
call_api(method="GET", path="/api/personalities")
```

返回：`[{id, name, hp_mod_pct, phy_atk_mod_pct, mag_atk_mod_pct, phy_def_mod_pct, mag_def_mod_pct, spd_mod_pct, buff_stat, nerf_stat, is_neutral}]`

buff_stat 为提升的属性名，nerf_stat 为降低的属性名，is_neutral 表示是否为平衡性格。

---

### 20. 精灵蛋

**`GET /api/pokemon-eggs`**

分页查询精灵蛋信息。

调用示例：
```
call_api(method="GET", path="/api/pokemon-eggs", params={"name": "迪莫", "page_size": 10})
```

查询参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | str | `""` | 精灵名称关键词（模糊匹配） |
| page | int | `1` | 页码 |
| page_size | int | `30` | 每页数量（1~100） |

返回：`{total, page, page_size, items: [{id, source_id, name, form, icon, pokemon_source_id, pokemon_id, pokemon_name, item_quality, created_at, updated_at}]}`

---

### 21. 精灵果实

**`GET /api/pokemon-fruits`**

分页查询精灵果实信息。

调用示例：
```
call_api(method="GET", path="/api/pokemon-fruits", params={"name": "迪莫", "page_size": 10})
```

查询参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | str | `""` | 精灵名称关键词（模糊匹配） |
| page | int | `1` | 页码 |
| page_size | int | `30` | 每页数量（1~100） |

返回：`{total, page, page_size, items: [{id, source_id, name, icon, pokemon_source_id, item_quality, created_at, updated_at}]}`

---

### 22. 精灵标记

**`GET /api/pokemon-marks`**

返回所有精灵标记/成就信息。

调用示例：
```
call_api(method="GET", path="/api/pokemon-marks")
```

返回：`[{id, key, zh_name, zh_description, sort_order, image}]`

---

### 23. 精灵筛选选项

**`GET /api/pokemon-filter-options`**

返回预设的筛选选项（如"仅异色"、各种排序方式），可用于 `/api/pokemon` 的 `filter_code` 参数。

调用示例：
```
call_api(method="GET", path="/api/pokemon-filter-options")
```

返回：`[{id, code, label, filter_type, order_by, order_dir, sort_order}]`

filter_type 为 `"shiny"` 或 `"sort"`。将某个选项的 `code` 传入 `/api/pokemon` 的 `filter_code` 参数即可应用该筛选/排序。

---

### 24. 随机精灵模式

**`GET /api/battle-pk/random-pokemon-modes`**

返回 PVP 对战中随机精灵的可用模式。

调用示例：
```
call_api(method="GET", path="/api/battle-pk/random-pokemon-modes")
```

返回：`[{id, code, label, kind, bloodline_code}]`

kind 为 `"any"`（任意精灵）或 `"attr"`（限定属性）。

---

### 25. 战斗 PK 分析

**`POST /api/battle-pk`**

提交两队精灵阵容进行 PVP 对战分析（同步，非流式）。

调用示例：
```
call_api(method="POST", path="/api/battle-pk", body={
  "team_a": {
    "title": "队伍A",
    "members": [
      {
        "pokemon_name": "迪莫",
        "sort_order": 1,
        "bloodline_label": "首领血脉",
        "personality_name_zh": "固执",
        "qual_1": "SS", "qual_2": "SS", "qual_3": "SS",
        "skill_1_name": "光芒斩", "skill_2_name": "光之盾",
        "skill_3_name": "圣光冲击", "skill_4_name": "愈合",
        "member_desc": ""
      }
    ],
    "resonance_magic_id": null,
    "resonance_magic_name": ""
  },
  "team_b": { ... }
})
```

请求体字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| team_a | object | A 队阵容 |
| team_a.title | str | 队伍名称 |
| team_a.lineup_desc | str | 队伍描述 |
| team_a.members | list | 队员列表（最多 6 个） |
| team_a.members[].pokemon_name | str | 精灵名称 |
| team_a.members[].sort_order | int | 排序 |
| team_a.members[].bloodline_label | str | 血脉标签 |
| team_a.members[].personality_name_zh | str | 性格名称 |
| team_a.members[].qual_1/qual_2/qual_3 | str | 品质（如 SS/S/A） |
| team_a.members[].skill_1_name ~ skill_4_name | str | 四个技能名 |
| team_a.members[].member_desc | str | 备注 |
| team_a.resonance_magic_id | int\|null | 共鸣魔法 ID |
| team_a.resonance_magic_name | str | 共鸣魔法名称 |
| team_b | object | B 队阵容（结构同 team_a） |

返回：`{completeness: {ok, missing}, plan: {team_a_order, team_a_order_reason, team_b_order, team_b_order_reason, skill_matchup, ability_impact}, team_a: {summary, advantages, weaknesses}, team_b: {summary, advantages, weaknesses}, key_rounds: [{round, desc}], turning_points, verdict: {winner, win_rate_a, reason}, error, raw}`
