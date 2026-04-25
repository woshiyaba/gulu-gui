# Ops 进化链改造设计（基于 `pokemon_evolution_chain`）

## 1. 背景与目标

当前 Ops 的进化链维护仍是线性 `steps[]`（`sort_order`）模型，无法完整表达分支与汇合。  
本次改造目标是以 `pokemon_evolution_chain` 边表为唯一真值，保留现有「卡片拖拽手感好」的优点，同时支持非专业运维可快速完成维护。

本设计必须满足以下业务规则：

1. 当一个精灵尚未加入任何进化链时，直接拖到画布可新建一条链。  
2. 进化关系通过拉线箭头建立，卡片可自由拖动。  
3. 支持分支与汇合：一个 pokemon 可有多条出边，也可有多条入边。  
4. 删除某链全部节点时，视为删除整条链。

---

## 2. 数据模型约定

以 `pokemon_evolution_chain` 为主（见 `docs/design/pokemon_evolution_chain.md`）：

- `chain_id`: 图编号。
- `pre_pokemon_id`: 前置节点，可为 `NULL`（链首）。
- `pokemon_id`: 当前节点。
- `pre_evolution_condition`: `pre_pokemon_id -> pokemon_id` 边条件。

补充约定：

- 一条链至少保留一条记录（单节点链：`pre_pokemon_id = NULL`）。
- 同一 `(chain_id, pre_pokemon_id, pokemon_id)` 不可重复。
- 允许：
  - `pre_pokemon_id` 相同、`pokemon_id` 不同（分支）；
  - `pokemon_id` 相同、`pre_pokemon_id` 不同（汇合）。

---

## 3. Ops 功能拆分

将「进化链维护」从精灵编辑弹窗中抽离为独立能力：

- 新入口：`Ops > 进化链维护`（建议新路由，如 `/ops/evolution-chains`）。
- 精灵编辑页保留只读摘要 +「前往进化链维护」按钮。
- 支持两种进入方式：
  - 按 `chain_id` 打开已有链；
  - 按 `pokemon_id` 打开，若该精灵无链则进入「新建链草稿态」。

---

## 4. 交互设计（运维友好）

## 4.1 画布与卡片

- 保留现有卡片视觉与拖拽反馈（沿用 `OpsPokemonView.vue` 的卡片样式和动画节奏）。
- 卡片可自由拖动，仅改变布局坐标，不改变进化关系。
- 关系变更只能通过「拉线箭头」或按钮向导完成，避免误改。

## 4.2 关系创建（核心）

- 从源卡片拖出连接点到目标卡片，生成 `源 -> 目标` 边。
- 创建后立即弹出轻量表单填写 `pre_evolution_condition`（可为空）。
- 提供两个低门槛按钮，避免只靠拖线：
  - `给它增加一种进化去向`（创建出边）；
  - `增加一个前置来源`（创建入边）。

## 4.3 新链创建（对应规则 1）

- 当当前精灵无 `chain_id`：
  - 拖入空画布后创建新 `chain_id` 草稿；
  - 自动写入根记录：`(chain_id, NULL, pokemon_id)`；
  - 画布显示单节点，提示继续「拉线新增关系」。

## 4.4 分支/汇合（对应规则 3）

- 分支：允许一个节点拉出多条箭头到不同目标。
- 汇合：允许多个节点箭头指向同一目标节点。
- 保存前做校验：
  - 禁止自环（`A -> A`）；
  - 禁止重复边；
  - 禁止产生环（检测到闭环则阻止保存并提示具体路径）。

## 4.5 删除语义（对应规则 4）

- 删除单节点：
  - 若删除后该 `chain_id` 仍有节点，自动删除关联边并保留链。
  - 若删除后节点数为 0，则执行「删除整条链」。
- 删除整链：
  - 清空该 `chain_id` 的全部边记录；
  - 同步将关联精灵的 `pokemon.chain_id`（及 `pokemon_detail.chain_id` 若仍使用）置空。

---

## 5. 后端改造方案（Ops）

## 5.1 新响应结构（替代线性 `steps`）

建议新增 Graph DTO：

- `nodes`: `[{ pokemon_id, pokemon_name, image_url, x, y, is_root }]`
- `edges`: `[{ pre_pokemon_id, pokemon_id, pre_evolution_condition }]`
- `chain_id`

兼容期可保留老接口，但新页面只使用 Graph DTO。

## 5.2 API 建议

- `GET /api/ops/evolution-chains/{chain_id}`：取完整图。
- `GET /api/ops/evolution-chains/by-pokemon/{pokemon_id}`：按精灵打开（无链返回空草稿）。
- `POST /api/ops/evolution-chains`：新建链（可带根节点）。
- `PUT /api/ops/evolution-chains/{chain_id}`：全量保存（nodes + edges）。
- `DELETE /api/ops/evolution-chains/{chain_id}`：删整链。
- `POST /api/ops/evolution-chains/{chain_id}/validate`：可选，做环检测/重复边检测。

## 5.3 保存策略

采用「全量覆盖保存」简化运维心智：

1. 前端提交当前节点与边快照。  
2. 后端事务内：
   - 校验合法性（无环、无重复边、节点存在）；
   - 重写 `pokemon_evolution_chain` 当前 `chain_id` 数据；
   - 重算并回写 `pokemon.chain_id` 归属。  
3. 返回最新图数据。

---

## 6. 前端改造方案（Ops）

## 6.1 页面拆分

- 新建页面：`front/pc-front/src/views/ops/OpsEvolutionChainView.vue`。
- 从 `OpsPokemonView.vue` 中抽取可复用能力：
  - 卡片渲染；
  - 拖拽反馈样式；
  - 精灵搜索选择器（用于新增节点/拉线目标）。

## 6.2 交互细节（保证“好手感”）

- 拉线时显示动态箭头预览和吸附高亮。
- 成功建边后轻提示「已建立：A -> B」。
- 所有危险操作（删节点、删整链）二次确认。
- 提供「撤销上一步」和「放弃改动」。

## 6.3 低门槛文案

- 将“节点/边”文案替换为运维可读词：
  - 节点 -> `精灵卡片`
  - 出边 -> `进化去向`
  - 入边 -> `前置来源`
- 错误提示给出操作建议，例如：
  - `这条连接会形成循环，请检查“X -> Y -> Z -> X”。`

---

## 7. 删除整链判定规则（落库规则）

在保存前后统一执行：

- `node_count(chain_id) == 0` 等价于删除链；
- 删除链后保证：
  - `pokemon_evolution_chain` 中无该 `chain_id`；
  - `pokemon`（及可选 `pokemon_detail`）中无该 `chain_id` 引用。

---

## 8. 分阶段实施

- P1（必须）：图接口 + 独立页面 + 拉线建关系 + 新建链 + 分支/汇合 + 删空即删链。
- P2：布局优化（自动排布/对齐）、批量操作、快捷键、操作审计。
- P3：高级能力（版本回滚、差异对比、批量导入校验）。

---

## 9. 验收用例（覆盖 4 条业务规则）

1. 无链精灵拖入空画布，保存后生成新 `chain_id` 与根记录。  
2. 卡片任意拖动不改关系；仅拉线才新增/修改关系。  
3. 同一精灵可成功创建 2+ 出边；同一精灵可成功接收 2+ 入边。  
4. 删除链内最后一个节点后，链数据与 `chain_id` 归属全部清理。  

