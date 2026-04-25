# `pokemon_evolution_chain` 表设计与数据迁移说明

本文描述进化关系由「线性链表」升级为「有向无环图（DAG）」后的**新表设计**，以及从旧表 **`evolution_chain`** 迁往 **`pokemon_evolution_chain`** 的**迁移规则与操作顺序**。实现应用代码、迁移脚本时请以此为准。

---

## 1. 背景与目标

### 1.1 旧模型（`evolution_chain`）

- 同一 `chain_id` 下用 **`sort_order`** 表达一条**全序链**。
- 每行存 **`pokemon_name`**（基础名）与 **`evolution_condition`**、可选 **`pre_evolution_condition`** 等，无法直接表达「一分支」「多合一」等图结构。

### 1.2 新模型（`pokemon_evolution_chain`）

- 每行表示一条**有向关系**（可理解为「入图 / 进化」的一条记录）：**`pre_pokemon_id` → `pokemon_id`**。
- **`pre_pokemon_id` 允许为 NULL**：表示**链首 / 无前置**（图中没有更前的精灵）；此时 `pokemon_id` 为该链的**起点形态**。这样一条链在表中是**完整**的：既有「根」行，也有后续 `pre` 非空的进化边。
- **`pre_evolution_condition`**：表示**从 `pre_pokemon_id` 进化到 `pokemon_id` 所需条件**（挂在该条记录上；命名与旧表成员行上的 `evolution_condition` 区分）。链首行通常为空串，除非业务在首阶源数据上写了说明。
- 同一逻辑图内所有行共享 **`chain_id`**；整体上为 **DAG**（由业务与迁移保证无环，数据库层可不强制）。

---

## 2. 表设计：`pokemon_evolution_chain`

### 2.1 表名

| 项目     | 说明 |
|----------|------|
| 新表名   | **`pokemon_evolution_chain`** |
| 旧表名   | **`evolution_chain`**（线性成员表，迁移后可保留备份或废弃） |

新表与旧表**并存阶段**：应用应只读写新表；旧表仅作迁移源或备份。

### 2.2 字段定义（建议）

| 列名 | 类型（MySQL 示例） | 空 | 说明 |
|------|-------------------|-----|------|
| `id` | `INT AUTO_INCREMENT` | NOT NULL | 主键 |
| `chain_id` | `INT` | NOT NULL | 同一张进化图内的边共享同一编号 |
| `pre_pokemon_id` | `INT` | **NULL 允许** | 进化前精灵 `pokemon.id`；**NULL = 无前置（链首）**；非 NULL = 从该精灵进化到 `pokemon_id` |
| `pokemon_id` | `INT` | NOT NULL | 进化后精灵，对应 `pokemon.id` |
| `pre_evolution_condition` | `VARCHAR(255)` | NOT NULL，默认 `''` | **从 `pre_pokemon_id` 到 `pokemon_id` 这一条边上的条件文案**（勿与旧表 `evolution_chain.evolution_condition` 混名） |

### 2.3 约束与索引（建议）

- **主键**：`PRIMARY KEY (id)`  
- **防重复**：`UNIQUE (chain_id, pre_pokemon_id, pokemon_id)`  
  - 链首行形如 `(chain_id, NULL, 根pokemon_id)`，每个 `chain_id` 下**至多一条**根行（迁移脚本保证）。  
  - PostgreSQL 默认下 UNIQUE 对 **NULL** 的判定与版本有关；若需严格禁止多条 `(chain_id, NULL, 同一 pokemon_id)`，可改用 **部分唯一索引** `UNIQUE (chain_id, pokemon_id) WHERE pre_pokemon_id IS NULL` 等（按需迭代）。  
- **外键**（推荐）：  
  - `pre_pokemon_id` → `pokemon(id)` ON DELETE CASCADE（或 RESTRICT，按产品删宠策略）  
  - `pokemon_id` → `pokemon(id)` ON DELETE CASCADE  
- **查询索引**：  
  - `INDEX idx_chain_pre (chain_id, pre_pokemon_id)` — 从某节点出发的出边  
  - `INDEX idx_chain_post (chain_id, pokemon_id)` — 指向某节点的入边  

### 2.4 与 `pokemon.chain_id` 的关系

- **`pokemon.chain_id`**：表示该精灵属于哪一张进化图（与旧语义一致）。  
- **`pokemon_evolution_chain`**：描述图内的**边 + 链首入图行**（`pre_pokemon_id IS NULL`）。单节点链在表中仍可有**一行** `(chain_id, NULL, 该精灵)`。

二者配合使用：**归属 + 拓扑**。

### 2.5 建表示例（MySQL）

```sql
CREATE TABLE IF NOT EXISTS pokemon_evolution_chain (
    id                  INT          NOT NULL AUTO_INCREMENT,
    chain_id            INT          NOT NULL COMMENT '同一张进化图内边共享 chain_id',
    pre_pokemon_id      INT          NULL DEFAULT NULL COMMENT '进化前 pokemon.id；NULL=链首无前置',
    pokemon_id          INT          NOT NULL COMMENT '进化后 pokemon.id',
    pre_evolution_condition VARCHAR(255) NOT NULL DEFAULT '' COMMENT '从 pre_pokemon_id 进化到 pokemon_id 的条件',
    PRIMARY KEY (id),
    UNIQUE KEY uk_pec_edge (chain_id, pre_pokemon_id, pokemon_id),
    KEY idx_pec_chain_pre (chain_id, pre_pokemon_id),
    KEY idx_pec_chain_post (chain_id, pokemon_id),
    CONSTRAINT fk_pec_pre FOREIGN KEY (pre_pokemon_id) REFERENCES pokemon (id) ON DELETE CASCADE,
    CONSTRAINT fk_pec_post FOREIGN KEY (pokemon_id) REFERENCES pokemon (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='精灵进化有向边（DAG）';
```

PostgreSQL 可将 `INT AUTO_INCREMENT` 改为 `SERIAL`，唯一约束与索引语法略作调整即可。

---

## 3. 数据迁移文档

### 3.1 迁移源与目标

| 角色 | 表名 | 说明 |
|------|------|------|
| 源表 | `evolution_chain`（旧结构） | 含 `chain_id`, `sort_order`, `pokemon_name`, `evolution_condition`，可选 **`pre_evolution_condition`**（成员行上，语义与「进入本阶」相关）等 |
| 目标表 | **`pokemon_evolution_chain`** | 边表；边上条件列名为 **`pre_evolution_condition`**，见上文 |

**重要**：若迁移脚本仍向表名 **`evolution_chain`** 写入或 `DROP evolution_chain`，而产品与文档约定的新表名为 **`pokemon_evolution_chain`**，则会出现「脚本跑了但读写仍指向旧表名」或「新表从未被创建」的现象。后续自动化脚本应**显式 `INSERT INTO pokemon_evolution_chain`**，且**不要**在未确认的情况下 `DROP` 业务仍在使用的表。

### 3.2 迁移范围（线性 → 边 + 链首）

经 **3.3** 合并后，仅对每个**主** `chain_id`（分量内 id 最小者）保留下来的线性行做下列展开；表中 `chain_id` 均为合并后的主 id。

对其中每个主链，将行按 **`sort_order` 升序**排序，得到序列：

\[
R_1, R_2, \ldots, R_n
\]

**（A）链首入图行（必写，保证整条链在表内完整）**

对每个 \(n \ge 1\)，生成**一条** `pre_pokemon_id = NULL` 的行：

| 目标列 | 取值规则 |
|--------|----------|
| `chain_id` | 与源行相同 |
| `pre_pokemon_id` | **NULL**（表示无前置） |
| `pokemon_id` | 见 **3.4**：由 \(R_1.\texttt{pokemon\_name}\) 解析得到 `pokemon.id` |
| `pre_evolution_condition` | 见 **3.6**（链首） |

**（B）相邻进化边**

对每一对相邻行 **\((R_{k-1}, R_k)\)**，\(k \ge 2\)，再生成**一条**目标行：

| 目标列 | 取值规则 |
|--------|----------|
| `chain_id` | 与源行相同 |
| `pre_pokemon_id` | 见 **3.4**：由 \(R_{k-1}.\texttt{pokemon\_name}\) 解析得到 `pokemon.id`（**非 NULL**） |
| `pokemon_id` | 见 **3.4**：由 \(R_k.\texttt{pokemon\_name}\) 解析得到 `pokemon.id` |
| `pre_evolution_condition` | 见 **3.5** |

若 \(n = 1\)（仅一阶），仍会有**（A）**一行 `(chain_id, NULL, 唯一形态)`，无 **（B）**。

### 3.3 一精灵一条链：源数据多链去重（迁移脚本）

业务约定：**每只精灵（`pokemon.id`）只属于一条进化图**（一个 `chain_id`）。源表 `evolution_chain` 若因历史原因出现「同一只精灵出现在多条 `chain_id`」或「两条链通过共用精灵连在一起」，迁移时按以下规则**合并并去掉多余源链**：

1. 将每条源 `chain_id` 的成员解析为 `pokemon.id`（解析失败的不参与构图）。  
2. 若某 `pokemon.id` 同时出现在多个 `chain_id` 中，则在「`chain_id` 图」上连边；求**连通分量**。  
3. 每个分量内保留 **`chain_id` 最小**的一条作为**主链**：仅该 `chain_id` 的线性行参与生成 `pokemon_evolution_chain`；分量内其余 `chain_id` 的线性行**整链丢弃**（不写入边表）。  
4. 写回 **`pokemon.chain_id` / `pokemon_detail.chain_id`** 时，一律使用**合并后的主 `chain_id`**（即该精灵所在分量的最小 `chain_id`），保证库内一精灵只挂一条链。

**注意**：若被丢弃的源链上有**主链线性数据里不存在的**成员，这些成员不会出现在新边表中，但仍会按名称尝试把 `chain_id` 写成主链 id（见 **3.7** 同步归属）。若业务需要保留「分叉」结构，应在源数据中拆分为不共用 `pokemon.id` 的形态或调整链设计，而不是依赖重复 `chain_id`。

### 3.4 `pokemon_name` → `pokemon.id`（与历史导入/图鉴一致）

链上存的是**基础名**（可能不含形态括号「（」后缀）。解析规则：

1. **精确匹配**：`SELECT MIN(id) FROM pokemon WHERE name = :基础名`；若存在则采用该 `id`。  
2. **形态匹配**：否则 `SELECT MIN(id) FROM pokemon WHERE name LIKE CONCAT(:基础名, '（', '%')`（或等价写法）；若存在则采用该 `id`。  
3. **失败**：若两步均无结果，**跳过该边**，记录日志（含 `chain_id`、`sort_order`、未解析的 `pokemon_name`），便于补数据后重跑或手工修。

**说明**：同一基础名多形态时取 **`MIN(id)`** 与历史脚本策略一致；若业务后续改为「代表形态」表，可再迭代解析规则。

### 3.5 目标列 `pre_evolution_condition`（相邻进化边，\(k \ge 2\)）

对 **\(R_{k-1} \to R_k\)**（\(R_k\) 为子节点，对应新表中的 `pokemon_id`）。**目标表列名**为 **`pre_evolution_condition`**，数据来自旧表两列之一（勿与目标列名混淆）：

1. **优先**：若源表存在列 **`pre_evolution_condition`**，且 \(R_k\) 上该字段**去首尾空格后非空**，则  
   **`pre_evolution_condition = R_k.pre_evolution_condition`**。

2. **否则**：  
   **`pre_evolution_condition = R_{k-1}.evolution_condition`**  
   （兼容旧数据把「再进化」条件写在前一阶成员行的 `evolution_condition` 上的场景。）

3. 若仍无内容，则 **`pre_evolution_condition = ''`**。

### 3.6 链首行 `pre_evolution_condition`（\(R_1\)，`pre_pokemon_id` 为 NULL）

- **固定写入 `''`（空字符串）**。  
- 不从源表 `pre_evolution_condition` / `evolution_condition` 继承，避免把“进化边条件”误挂到无前置的链首记录上。

### 3.7 推荐执行顺序（生产）

1. **全库备份**（逻辑或物理）。  
2. **创建空表** `pokemon_evolution_chain`（执行 §2.5 DDL，若不存在）。  
3. **从源表只读**生成边数据，**批量 `INSERT` 到 `pokemon_evolution_chain`**（可先写入临时表校验行数、唯一约束、抽样对比）。  
4. **同步归属**：对本次涉及的 `chain_id`，先清空 `pokemon` / `pokemon_detail` 上对应旧 `chain_id`，再按源表 `(chain_id, pokemon_name)` 写回（与 `scripts/migrate_evolution_chain_to_dag.py` 一致）。  
5. **应用切换**：读写进化关系改为 `pokemon_evolution_chain`；图查询（邻接表 / 拓扑）按新表实现。  
6. **源表处理**：确认无回滚需求后，将 `evolution_chain` **重命名备份**或选用脚本参数 `--archive-linear-source` 自动归档，避免与迁移脚本再次混淆。

不建议在首次上线新表时立刻 `DROP evolution_chain`，除非所有读路径已切换且备份已保留。

### 3.8 迁移后验收（建议清单）

- [ ] **合并后**每个主 `chain_id` 下行数 = 该主链线性成员数 \(n\)：**1** 条链首 + **(n−1)** 条进化边（无解析失败、且已按 **3.3** 丢弃非主源链）。  
- [ ] `SELECT COUNT(*) FROM pokemon_evolution_chain` 与迁移日志中「成功插入」条数一致。  
- [ ] 随机抽样若干 `chain_id`，对比旧顺序与新边的前后 `pokemon_id` 是否与旧 `pokemon_name` 解析结果一致。  
- [ ] 抽样检查 **`pre_evolution_condition`**：源表子阶 **`pre_evolution_condition`** 非空时是否优先体现在边上。  
- [ ] 唯一约束无冲突；外键无悬挂 `pokemon_id`。

### 3.9 与旧迁移脚本不一致之处（排错说明）

若曾使用向 **`evolution_chain`** 写入 DAG 结构、或 **`DROP evolution_chain`** 的脚本，而产品文档与接口已改为 **`pokemon_evolution_chain`**，则会出现：

- 新表 **`pokemon_evolution_chain` 始终为空**；或  
- 应用仍查询 **`evolution_chain`**，看不到新数据；或  
- 旧表被删除导致历史对比困难。

**修正方向**：迁移目标表名统一为 **`pokemon_evolution_chain`**；应用与 SQL 初始化（如 `db/schema.py`、`wikiroco.sql`）同步增加该表定义，并逐步废弃对旧线性 `evolution_chain` 的依赖。

---

## 4. 后续工作（非本文 DDL）

- 更新 **`pokemon_repository` / `ops_repository`** 等：读链、运营维护边、搜索图等改为查询 **`pokemon_evolution_chain`**，API 字段与 **`pre_evolution_condition`** 对齐。  
- 更新 **`import_evolution_chains.py`** 或新导入管道：写入 **`pokemon_evolution_chain`** 而非旧表。  
- 提供可重复执行的迁移脚本（Python 或 SQL），**目标表固定为 `pokemon_evolution_chain`**，并在 README 或 CI 中引用本文档 §3。  
  仓库内参考实现：`scripts/migrate_evolution_chain_to_dag.py`（**PostgreSQL**，`config.PG_CONFIG` / `psycopg2`；只读线性源表，写入 `pokemon_evolution_chain` 并同步 `chain_id`；默认不删除源表，可选 `--archive-linear-source` 归档）。

---

文档版本：新表边上条件列名为 **`pre_evolution_condition`**；修订时请与仓库内 DDL、迁移脚本保持一致。
