
-- ============================================================
-- 迁移重建：先删表（子表 -> 父表）
-- ============================================================
DROP TABLE IF EXISTS attribute_matchup CASCADE;
DROP TABLE IF EXISTS pokemon_egg_group CASCADE;
DROP TABLE IF EXISTS skill_stone CASCADE;
DROP TABLE IF EXISTS egg_hatch_pet CASCADE;
DROP TABLE IF EXISTS pokemon_skill CASCADE;
DROP TABLE IF EXISTS pet_map_point CASCADE;
DROP TABLE IF EXISTS pokemon_attribute CASCADE;
DROP TABLE IF EXISTS pokemon CASCADE;
DROP TABLE IF EXISTS evolution_chain CASCADE;
DROP TABLE IF EXISTS category CASCADE;
DROP TABLE IF EXISTS skill CASCADE;
DROP TABLE IF EXISTS pokemon_trait CASCADE;
DROP TABLE IF EXISTS sys_dict CASCADE;
DROP TABLE IF EXISTS attribute CASCADE;

-- 属性表
CREATE TABLE attribute (
    id         SERIAL      PRIMARY KEY,
    name       VARCHAR(10) NOT NULL,          -- 属性名：火、水、草 …
    sort_order INT         NOT NULL DEFAULT 0, -- 顺序
    image      VARCHAR(255) NOT NULL DEFAULT '', -- 属性图标路径
    CONSTRAINT uk_attribute_name UNIQUE (name),
    CONSTRAINT uk_attribute_sort UNIQUE (sort_order)
);


-- 通用字典
-- dict_type 区分字典类别，code 是业务编码，label 是显示名
CREATE TABLE sys_dict (
    id        SERIAL      PRIMARY KEY,
    dict_type VARCHAR(30) NOT NULL,           -- 字典类别
    code      VARCHAR(30) NOT NULL,           -- 编码
    label     VARCHAR(30) NOT NULL,           -- 显示
    sort_order INT        NOT NULL DEFAULT 0, -- 排序
    CONSTRAINT uk_sys_dict UNIQUE (dict_type, code)
);

-- 特性表
CREATE TABLE pokemon_trait (
    id          SERIAL       PRIMARY KEY,
    name        VARCHAR(10)  NOT NULL, -- 名称
    description TEXT         NOT NULL DEFAULT '', -- 特性
    sort_order  INT          NOT NULL DEFAULT 0,
    CONSTRAINT uk_trait_name UNIQUE (name)
);

-- 精灵基础信息
CREATE TABLE pokemon (
    id            SERIAL       PRIMARY KEY,
    no            VARCHAR(20)  NOT NULL, -- 编号，如 NO.003
    name          VARCHAR(50)  NOT NULL, -- 名称
    image         VARCHAR(255) NOT NULL DEFAULT '',
    type          VARCHAR(30)  NOT NULL DEFAULT '', -- 阶段编码，如 stage1/stage2/final
    type_name     VARCHAR(30)  NOT NULL DEFAULT '', -- 阶段显示，如 Ⅰ阶/最终形态
    form          VARCHAR(30)  NOT NULL DEFAULT '', -- 形态编码，如 original/regional/boss
    form_name     VARCHAR(30)  NOT NULL DEFAULT '', -- 形态显示，如 原始形态/地区形态
    egg_group     VARCHAR(30)  NOT NULL DEFAULT '', -- 蛋组（冗余存储，供业务直接查询）
    trait_id      INT          NOT NULL,        -- 特性，关联 pokemon_trait.id
    detail_url    VARCHAR(255) NOT NULL DEFAULT '',
    image_lc      VARCHAR(255) NOT NULL DEFAULT '',
    chain_id      INT          DEFAULT NULL,    -- 进化链
    hp            INT          NOT NULL DEFAULT 0,
    atk           INT          NOT NULL DEFAULT 0,
    matk          INT          NOT NULL DEFAULT 0,
    def_val       INT          NOT NULL DEFAULT 0,
    mdef          INT          NOT NULL DEFAULT 0,
    spd           INT          NOT NULL DEFAULT 0,
    total_race    INT          NOT NULL DEFAULT 0,
    obtain_method VARCHAR(255) NOT NULL DEFAULT '',
    -- 外键约束（type/form/egg_group 不再走字典外键，仅冗余存值）
    CONSTRAINT fk_pokemon_trait FOREIGN KEY (trait_id) REFERENCES pokemon_trait(id)
);

-- 宝可梦和属性关联表
CREATE TABLE pokemon_attribute (
    id           SERIAL PRIMARY KEY,
    pokemon_id   INT    NOT NULL,
    attr_id      INT    NOT NULL,              -- 关联 attribute.id
    CONSTRAINT uk_pokemon_attr UNIQUE (pokemon_id, attr_id),
    CONSTRAINT fk_pa_pokemon FOREIGN KEY (pokemon_id)
        REFERENCES pokemon (id) ON DELETE CASCADE,
    CONSTRAINT fk_pa_attr FOREIGN KEY (attr_id)
        REFERENCES attribute (id) ON DELETE CASCADE
);

-- 技能库
-- attr 改用 attribute.id，type 改用 dict_skill_type.id
CREATE TABLE skill (
    id            SERIAL       PRIMARY KEY,
    name          VARCHAR(50)  NOT NULL,
    attr_id       INT          DEFAULT NULL,   -- 关联 attribute.id
    power         INT          NOT NULL DEFAULT 0,
    type          VARCHAR(30)  NOT NULL DEFAULT '', -- 技能类型（物攻/魔攻/状态/防御）
    consume       INT          NOT NULL DEFAULT 0,
    skill_desc    TEXT,
    icon          VARCHAR(255) NOT NULL DEFAULT '',
    CONSTRAINT uk_skill_name UNIQUE (name),
    CONSTRAINT fk_skill_attr FOREIGN KEY (attr_id)
        REFERENCES attribute (id)
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

-- 精灵技能关联（多对多）
CREATE TABLE pokemon_skill (
    id         SERIAL PRIMARY KEY,
    pokemon_id INT    NOT NULL,
    skill_id   INT    NOT NULL,
    type       VARCHAR(20) NOT NULL DEFAULT '原生技能', -- 技能来源：原生技能/学习技能（字典冗余一份，业务表直接存）
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
    CONSTRAINT uk_ehp_pokemon UNIQUE (pokemon_id),
    CONSTRAINT fk_ehp_pokemon FOREIGN KEY (pokemon_id)
        REFERENCES pokemon (id) ON DELETE CASCADE
);

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

-- 精灵蛋组（一只精灵可属于多个蛋组）
CREATE TABLE pokemon_egg_group (
    id           SERIAL      PRIMARY KEY,
    pokemon_id   INT         NOT NULL,
    group_name   VARCHAR(50) NOT NULL,
    CONSTRAINT uk_peg_pokemon_group UNIQUE (pokemon_id, group_name),
    CONSTRAINT fk_peg_pokemon FOREIGN KEY (pokemon_id)
        REFERENCES pokemon (id) ON DELETE CASCADE
);

-- Banner
CREATE TABLE IF NOT EXISTS banner (
    id          SERIAL       PRIMARY KEY,
    title       VARCHAR(100) NOT NULL DEFAULT '',
    image_url   VARCHAR(500) NOT NULL,
    link_type   VARCHAR(50)  NOT NULL DEFAULT '',
    link_param  VARCHAR(255) NOT NULL DEFAULT '',
    sort_order  INT          NOT NULL DEFAULT 0,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- 星光对决
CREATE TABLE IF NOT EXISTS starlight_duel_episode (
    id              SERIAL       PRIMARY KEY,
    episode_number  INT          NOT NULL UNIQUE,
    title           VARCHAR(100) NOT NULL DEFAULT '',
    strategy_text   TEXT         NOT NULL DEFAULT '',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS starlight_duel_pet (
    id          SERIAL PRIMARY KEY,
    episode_id  INT    NOT NULL REFERENCES starlight_duel_episode(id) ON DELETE CASCADE,
    pet_id      INT    NOT NULL REFERENCES pokemon(id),
    sort_order  INT    NOT NULL DEFAULT 1,
    skill_1_id  INT    REFERENCES skill(id),
    skill_2_id  INT    REFERENCES skill(id),
    skill_3_id  INT    REFERENCES skill(id),
    skill_4_id  INT    REFERENCES skill(id),
    UNIQUE (episode_id, sort_order)
);

-- 属性克制矩阵（防守属性 × 进攻属性 → 倍率）
CREATE TABLE attribute_matchup (
    defender_attr_id INT            NOT NULL,
    attacker_attr_id INT            NOT NULL,
    multiplier       NUMERIC(10, 8) NOT NULL,
    PRIMARY KEY (defender_attr_id, attacker_attr_id),
    CONSTRAINT fk_am_defender FOREIGN KEY (defender_attr_id)
        REFERENCES attribute (id) ON DELETE CASCADE,
    CONSTRAINT fk_am_attacker FOREIGN KEY (attacker_attr_id)
        REFERENCES attribute (id) ON DELETE CASCADE
);