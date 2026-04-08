from db.connection import get_conn

# 按依赖顺序排列，先建被引用的表
_SCHEMAS = [
    # 精灵基础信息
    """
    CREATE TABLE IF NOT EXISTS pokemon (
        id          INT          NOT NULL AUTO_INCREMENT,
        no          VARCHAR(20)  NOT NULL COMMENT '编号，如 NO.003',
        name        VARCHAR(50)  NOT NULL COMMENT '精灵名称',
        image       VARCHAR(255) NOT NULL DEFAULT '' COMMENT '图片相对路径',
        type        VARCHAR(20)  NOT NULL DEFAULT '' COMMENT 'stage1/stage2/final/boss',
        type_name   VARCHAR(20)  NOT NULL DEFAULT '' COMMENT 'Ⅰ阶/最终形态 等',
        form        VARCHAR(20)  NOT NULL DEFAULT '' COMMENT 'original/regional/boss',
        form_name   VARCHAR(20)  NOT NULL DEFAULT '' COMMENT '原始形态/地区形态 等',
        detail_url  VARCHAR(255) NOT NULL DEFAULT '' COMMENT '外部详情链接',
        PRIMARY KEY (id),
        UNIQUE KEY uk_no (no),
        KEY idx_name (name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='精灵基础图鉴';
    """,

    # 精灵属性（一个精灵可有多个属性）
    """
    CREATE TABLE IF NOT EXISTS pokemon_attribute (
        id          INT          NOT NULL AUTO_INCREMENT,
        pokemon_no  VARCHAR(20)  NOT NULL COMMENT '关联 pokemon.no',
        attr_name   VARCHAR(20)  NOT NULL COMMENT '属性名，如 草/火/水',
        attr_image  VARCHAR(255) NOT NULL DEFAULT '' COMMENT '属性图标路径',
        PRIMARY KEY (id),
        KEY idx_pokemon_no (pokemon_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='精灵属性';
    """,

    # 技能库（先建，pokemon_skill 引用它）
    """
    CREATE TABLE IF NOT EXISTS skill (
        id      INT          NOT NULL AUTO_INCREMENT,
        name    VARCHAR(50)  NOT NULL COMMENT '技能名称',
        attr    VARCHAR(20)  NOT NULL DEFAULT '' COMMENT '属性',
        power   INT          NOT NULL DEFAULT 0  COMMENT '威力',
        type    VARCHAR(20)  NOT NULL DEFAULT '' COMMENT '物攻/魔攻/状态/防御',
        consume INT          NOT NULL DEFAULT 0  COMMENT '能量消耗',
        skill_desc TEXT               COMMENT '技能描述',
        icon    VARCHAR(255) NOT NULL DEFAULT '' COMMENT '图标路径',
        PRIMARY KEY (id),
        UNIQUE KEY uk_name (name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='技能库';
    """,

    # 精灵详情（与 pokemon 一对一，以 pokemon_name 关联）
    """
    CREATE TABLE IF NOT EXISTS pokemon_detail (
        id              INT          NOT NULL AUTO_INCREMENT,
        pokemon_name    VARCHAR(50)  NOT NULL COMMENT '关联 pokemon.name',
        hp              INT          NOT NULL DEFAULT 0,
        atk             INT          NOT NULL DEFAULT 0 COMMENT '物攻',
        matk            INT          NOT NULL DEFAULT 0 COMMENT '魔攻',
        def_val         INT          NOT NULL DEFAULT 0 COMMENT '物防（def 是 MySQL 保留字，用 def_val）',
        mdef            INT          NOT NULL DEFAULT 0 COMMENT '魔防',
        spd             INT          NOT NULL DEFAULT 0 COMMENT '速度',
        trait_name      VARCHAR(50)  NOT NULL DEFAULT '' COMMENT '特性名称',
        trait_desc      TEXT                  COMMENT '特性描述',
        obtain_method   VARCHAR(255) NOT NULL DEFAULT '' COMMENT '宠物获取方式',
        strong_against  JSON                  COMMENT '克制的属性列表',
        weak_against    JSON                  COMMENT '被克制的属性列表',
        resist          JSON                  COMMENT '抵抗的属性列表',
        resisted        JSON                  COMMENT '被抵抗的属性列表',
        PRIMARY KEY (id),
        UNIQUE KEY uk_pokemon_name (pokemon_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='精灵详情种族值';
    """,

    # 精灵可学技能（多对多）
    """
    CREATE TABLE IF NOT EXISTS pokemon_skill (
        id           INT         NOT NULL AUTO_INCREMENT,
        pokemon_name VARCHAR(50) NOT NULL COMMENT '关联 pokemon.name',
        skill_name   VARCHAR(50) NOT NULL COMMENT '关联 skill.name',
        sort_order   INT         NOT NULL DEFAULT 0 COMMENT '技能排序',
        PRIMARY KEY (id),
        UNIQUE KEY uk_pokemon_skill (pokemon_name, skill_name),
        KEY idx_pokemon_name (pokemon_name),
        KEY idx_skill_name (skill_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='精灵技能关联';
    """,
]


def init_db() -> None:
    """建表（IF NOT EXISTS，幂等）。"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for ddl in _SCHEMAS:
                cur.execute(ddl)
        conn.commit()
        print("[schema] 数据库表初始化完成")
    finally:
        conn.close()
