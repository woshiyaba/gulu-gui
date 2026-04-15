-- ============================================================
-- 洛克王国精灵图鉴 — PostgreSQL 表结构 (v2)
-- 生成日期: 2026-04-15
-- ============================================================
--
-- 设计要点：
-- 1. 所有关联表用 INTEGER 外键，不再用 VARCHAR name 关联
-- 2. 属性、阶段/形态、技能类型、蛋组全部抽为字典表，业务表存 ID
-- 3. 移除 pokemon_detail 中冗余的 JSON 克制列
-- 4. 补齐 category / skill_stone / egg_hatch_pet 的 DDL
-- ============================================================

-- 删表（先子表后主表）
DROP TABLE IF EXISTS pet_map_point       CASCADE;
DROP TABLE IF EXISTS pokemon_skill       CASCADE;
DROP TABLE IF EXISTS pokemon_detail      CASCADE;
DROP TABLE IF EXISTS pokemon_attribute   CASCADE;
DROP TABLE IF EXISTS pokemon_egg_group   CASCADE;
DROP TABLE IF EXISTS evolution_chain     CASCADE;
DROP TABLE IF EXISTS egg_hatch_pet       CASCADE;
DROP TABLE IF EXISTS skill_stone         CASCADE;
DROP TABLE IF EXISTS attribute_matchup   CASCADE;
DROP TABLE IF EXISTS category            CASCADE;
DROP TABLE IF EXISTS skill               CASCADE;
DROP TABLE IF EXISTS pokemon             CASCADE;
DROP TABLE IF EXISTS dict_attribute      CASCADE;
DROP TABLE IF EXISTS dict_skill_type     CASCADE;
DROP TABLE IF EXISTS dict_egg_group      CASCADE;
DROP TABLE IF EXISTS sys_dict            CASCADE;

-- ============================================================
-- 字典表
-- ============================================================

-- 属性字典（火/水/草 …）
-- 同时承担原 attribute_axis 的排序职责
CREATE TABLE dict_attribute (
    id         SERIAL      PRIMARY KEY,
    name       VARCHAR(20) NOT NULL,          -- 属性名：火、水、草 …
    sort_order INT         NOT NULL DEFAULT 0, -- 克制矩阵表头顺序
    image      VARCHAR(255) NOT NULL DEFAULT '', -- 属性图标路径
    CONSTRAINT uk_dict_attr_name UNIQUE (name),
    CONSTRAINT uk_dict_attr_sort UNIQUE (sort_order)
);

-- 技能类型字典（物攻/魔攻/状态/防御）
CREATE TABLE dict_skill_type (
    id   SERIAL      PRIMARY KEY,
    name VARCHAR(20) NOT NULL,                -- 类型名：物攻、魔攻、状态、防御
    CONSTRAINT uk_dict_skill_type_name UNIQUE (name)
);

-- 蛋组字典
CREATE TABLE dict_egg_group (
    id   SERIAL      PRIMARY KEY,
    name VARCHAR(50) NOT NULL,                -- 蛋组名：两栖组、动物组 …
    CONSTRAINT uk_dict_egg_group_name UNIQUE (name)
);

-- 通用字典（阶段 type / 形态 form）
-- dict_type 区分字典类别，code 是业务编码，label 是显示名
CREATE TABLE sys_dict (
    id        SERIAL      PRIMARY KEY,
    dict_type VARCHAR(30) NOT NULL,           -- 字典类别：pokemon_type / pokemon_form
    code      VARCHAR(30) NOT NULL,           -- 编码：stage1 / original …
    label     VARCHAR(30) NOT NULL,           -- 显示名：Ⅰ阶 / 原始形态 …
    sort_order INT        NOT NULL DEFAULT 0, -- 排序
    CONSTRAINT uk_sys_dict UNIQUE (dict_type, code)
);

-- ============================================================
-- 字典初始数据
-- ============================================================

-- 属性（18 种，sort_order 与克制矩阵表头顺序一致）
INSERT INTO dict_attribute (name, sort_order) VALUES
    ('火', 1),  ('水', 2),  ('草', 3),  ('光', 4),
    ('恶', 5),  ('幽', 6),  ('普通', 7),  ('地', 8),
    ('冰', 9),  ('龙', 10), ('电', 11), ('毒', 12),
    ('虫', 13), ('武', 14), ('翼', 15), ('萌', 16),
    ('机械', 17), ('幻', 18);

-- 技能类型
INSERT INTO dict_skill_type (name) VALUES
    ('物攻'), ('魔攻'), ('状态'), ('防御');

-- 蛋组
INSERT INTO dict_egg_group (name) VALUES
    ('两栖组'), ('动物组'), ('大地组'), ('天空组'),
    ('妖精组'), ('巨灵组'), ('拟人组'), ('无孵蛋组'),('无法孵蛋组'),
    ('昆虫组'), ('机械组'), ('植物组'), ('海洋组'),
    ('软体组'), ('魔力组'), ('龙组');

-- 阶段 (pokemon_type)
INSERT INTO sys_dict (dict_type, code, label, sort_order) VALUES
    ('pokemon_type', 'stage1',         'Ⅰ阶',     1),
    ('pokemon_type', 'stage2',         'Ⅱ阶',     2),
    ('pokemon_type', 'final',          '最终形态',  3),
    ('pokemon_type', 'boss_evolution', '首领进化',  4);

-- 形态 (pokemon_form)
INSERT INTO sys_dict (dict_type, code, label, sort_order) VALUES
    ('pokemon_form', 'original', '原始形态', 1),
    ('pokemon_form', 'regional', '地区形态', 2),
    ('pokemon_form', 'boss',     '首领形态', 3);

-- ============================================================
-- 业务表
-- ============================================================

-- 精灵基础信息
-- type / form 存 sys_dict.id，不再需要 type_name / form_name
CREATE TABLE pokemon (
    id         SERIAL       PRIMARY KEY,
    no         VARCHAR(20)  NOT NULL,                -- 编号，如 NO.003
    name       VARCHAR(50)  NOT NULL,                -- 精灵名称
    image      VARCHAR(255) NOT NULL DEFAULT '',     -- 图片相对路径
    type_id    INT          DEFAULT NULL,            -- 阶段，关联 sys_dict.id (pokemon_type)
    form_id    INT          DEFAULT NULL,            -- 形态，关联 sys_dict.id (pokemon_form)
    detail_url VARCHAR(255) NOT NULL DEFAULT '',     -- 外部详情链接
    image_lc   VARCHAR(255) NOT NULL DEFAULT '',     -- 洛克素材侧图片文件名
    CONSTRAINT fk_pokemon_type FOREIGN KEY (type_id) REFERENCES sys_dict (id),
    CONSTRAINT fk_pokemon_form FOREIGN KEY (form_id) REFERENCES sys_dict (id)
);

CREATE INDEX idx_pokemon_name ON pokemon (name);

-- 属性克制矩阵（防守属性 × 进攻属性 → 倍率）
-- 改用 dict_attribute.id 关联
CREATE TABLE attribute_matchup (
    defender_attr_id INT            NOT NULL, -- 受击方属性 dict_attribute.id
    attacker_attr_id INT            NOT NULL, -- 进攻招式属性 dict_attribute.id
    multiplier       NUMERIC(10, 8) NOT NULL, -- 受击倍率：2/1/0.5
    PRIMARY KEY (defender_attr_id, attacker_attr_id),
    CONSTRAINT fk_matchup_defender FOREIGN KEY (defender_attr_id)
        REFERENCES dict_attribute (id) ON DELETE CASCADE,
    CONSTRAINT fk_matchup_attacker FOREIGN KEY (attacker_attr_id)
        REFERENCES dict_attribute (id) ON DELETE CASCADE
);

-- 精灵属性（一个精灵可有多个属性）
-- 改用 dict_attribute.id 关联，attr_image 不再需要（已在 dict_attribute.image 中）
CREATE TABLE pokemon_attribute (
    id           SERIAL PRIMARY KEY,
    pokemon_id   INT    NOT NULL,
    attr_id      INT    NOT NULL,              -- 关联 dict_attribute.id
    CONSTRAINT uk_pokemon_attr UNIQUE (pokemon_id, attr_id),
    CONSTRAINT fk_pa_pokemon FOREIGN KEY (pokemon_id)
        REFERENCES pokemon (id) ON DELETE CASCADE,
    CONSTRAINT fk_pa_attr FOREIGN KEY (attr_id)
        REFERENCES dict_attribute (id) ON DELETE CASCADE
);

-- 精灵蛋组（一只精灵多个蛋组）
-- 改用 dict_egg_group.id 关联
CREATE TABLE pokemon_egg_group (
    id            SERIAL PRIMARY KEY,
    pokemon_id    INT    NOT NULL,
    egg_group_id  INT    NOT NULL,             -- 关联 dict_egg_group.id
    CONSTRAINT uk_pokemon_egg_group UNIQUE (pokemon_id, egg_group_id),
    CONSTRAINT fk_peg_pokemon FOREIGN KEY (pokemon_id)
        REFERENCES pokemon (id) ON DELETE CASCADE,
    CONSTRAINT fk_peg_egg_group FOREIGN KEY (egg_group_id)
        REFERENCES dict_egg_group (id) ON DELETE CASCADE
);

-- 技能库
-- attr 改用 dict_attribute.id，type 改用 dict_skill_type.id
CREATE TABLE skill (
    id            SERIAL       PRIMARY KEY,
    name          VARCHAR(50)  NOT NULL,
    attr_id       INT          DEFAULT NULL,   -- 关联 dict_attribute.id
    power         INT          NOT NULL DEFAULT 0,
    skill_type_id INT          DEFAULT NULL,   -- 关联 dict_skill_type.id
    consume       INT          NOT NULL DEFAULT 0,
    skill_desc    TEXT,
    icon          VARCHAR(255) NOT NULL DEFAULT '',
    CONSTRAINT uk_skill_name UNIQUE (name),
    CONSTRAINT fk_skill_attr FOREIGN KEY (attr_id)
        REFERENCES dict_attribute (id),
    CONSTRAINT fk_skill_type FOREIGN KEY (skill_type_id)
        REFERENCES dict_skill_type (id)
);

-- 进化链
-- pokemon_name 保留为基础名，因为链成员可能还未入库 pokemon 表
CREATE TABLE evolution_chain (
    id                  SERIAL       PRIMARY KEY,
    chain_id            INT          NOT NULL,         -- 进化链编号，同链共享
    sort_order          SMALLINT     NOT NULL,         -- 在链中的顺序，从 1 开始
    pokemon_name        VARCHAR(50)  NOT NULL,         -- 基础名（不含形态后缀）
    evolution_condition VARCHAR(255) NOT NULL DEFAULT '',
    CONSTRAINT uk_chain_step UNIQUE (chain_id, sort_order)
);

CREATE INDEX idx_evo_pokemon_name ON evolution_chain (pokemon_name);

-- 精灵详情（与 pokemon 一对一）
CREATE TABLE pokemon_detail (
    id            SERIAL       PRIMARY KEY,
    pokemon_id    INT          NOT NULL,
    chain_id      INT          DEFAULT NULL,   -- 关联 evolution_chain.chain_id
    hp            INT          NOT NULL DEFAULT 0,
    atk           INT          NOT NULL DEFAULT 0,
    matk          INT          NOT NULL DEFAULT 0,
    def_val       INT          NOT NULL DEFAULT 0,
    mdef          INT          NOT NULL DEFAULT 0,
    spd           INT          NOT NULL DEFAULT 0,
    trait_name    VARCHAR(50)  NOT NULL DEFAULT '',
    trait_desc    TEXT,
    obtain_method VARCHAR(255) NOT NULL DEFAULT '',
    CONSTRAINT uk_detail_pokemon UNIQUE (pokemon_id),
    CONSTRAINT fk_detail_pokemon FOREIGN KEY (pokemon_id)
        REFERENCES pokemon (id) ON DELETE CASCADE
);

-- 精灵技能关联（多对多）
CREATE TABLE pokemon_skill (
    id         SERIAL PRIMARY KEY,
    pokemon_id INT    NOT NULL,
    skill_id   INT    NOT NULL,
    sort_order INT    NOT NULL DEFAULT 0,
    CONSTRAINT uk_pokemon_skill UNIQUE (pokemon_id, skill_id),
    CONSTRAINT fk_ps_pokemon FOREIGN KEY (pokemon_id)
        REFERENCES pokemon (id) ON DELETE CASCADE,
    CONSTRAINT fk_ps_skill FOREIGN KEY (skill_id)
        REFERENCES skill (id) ON DELETE CASCADE
);

-- 蛋孵化宠物数据
CREATE TABLE egg_hatch_pet (
    id             SERIAL  PRIMARY KEY,
    pokemon_id     INT     NOT NULL,
    is_leader_form BOOLEAN NOT NULL DEFAULT FALSE,
    hatch_data     INT     NOT NULL DEFAULT 0,       -- 孵化时间（秒）
    weight_low     INT     NOT NULL DEFAULT 0,       -- 体重下限（g）
    weight_high    INT     NOT NULL DEFAULT 0,       -- 体重上限（g）
    height_low     INT     NOT NULL DEFAULT 0,       -- 身高下限（cm）
    height_high    INT     NOT NULL DEFAULT 0,       -- 身高上限（cm）
    CONSTRAINT fk_ehp_pokemon FOREIGN KEY (pokemon_id)
        REFERENCES pokemon (id) ON DELETE CASCADE
);

CREATE INDEX idx_ehp_pokemon ON egg_hatch_pet (pokemon_id);

-- 技能石获取方式
CREATE TABLE skill_stone (
    id            SERIAL       PRIMARY KEY,
    skill_id      INT          NOT NULL,
    obtain_method VARCHAR(255) NOT NULL DEFAULT '',
    CONSTRAINT uk_skill_stone UNIQUE (skill_id),
    CONSTRAINT fk_ss_skill FOREIGN KEY (skill_id)
        REFERENCES skill (id) ON DELETE CASCADE
);

-- 地图分类
CREATE TABLE category (
    id                 SERIAL       PRIMARY KEY,
    category_id        BIGINT       NOT NULL,
    description        VARCHAR(255) NOT NULL DEFAULT '',
    type               VARCHAR(50)  NOT NULL DEFAULT '',
    category_image_url VARCHAR(255) NOT NULL DEFAULT '',
    CONSTRAINT uk_category_id UNIQUE (category_id)
);

-- 地图点位
CREATE TABLE pet_map_point (
    id          SERIAL          PRIMARY KEY,
    source_id   BIGINT          NOT NULL,
    map_id      INT             NOT NULL,
    title       VARCHAR(100)    NOT NULL DEFAULT '',
    latitude    NUMERIC(18, 15) NOT NULL,
    longitude   NUMERIC(18, 15) NOT NULL,
    category_id BIGINT          NOT NULL,
    CONSTRAINT uk_source_id UNIQUE (source_id)
);

CREATE INDEX idx_pmp_map_id       ON pet_map_point (map_id);
CREATE INDEX idx_pmp_category_id  ON pet_map_point (category_id);
CREATE INDEX idx_pmp_map_category ON pet_map_point (map_id, category_id);
