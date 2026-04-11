from db.connection import get_conn

# 删表顺序：先删关联表，避免日后加外键时出错
_DROP_ORDER = (
    "pokemon_skill",
    "pokemon_detail",
    "pokemon_attribute",
    "pokemon_egg_group",
    "pokemon",
    "skill",
    "attribute_matchup",
    "attribute_axis",
)

# 按依赖顺序排列，先建被引用的表
_SCHEMAS = [
    # 属性克制矩阵：表头顺序 + 单方「防守属性 × 进攻属性 → 倍率」（双属性在接口层相乘）
    """
    CREATE TABLE IF NOT EXISTS attribute_axis (
        attr_name  VARCHAR(20) NOT NULL COMMENT '属性名，与 pokemon_attribute.attr_name 对齐',
        sort_order INT          NOT NULL COMMENT '表头从左到右顺序，从 1 开始',
        PRIMARY KEY (attr_name),
        UNIQUE KEY uk_attr_axis_sort (sort_order)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='属性表头顺序（与 docs/pets/属性.json 键顺序一致）';
    """,
    """
    CREATE TABLE IF NOT EXISTS attribute_matchup (
        defender_attr VARCHAR(20) NOT NULL COMMENT '受击方（精灵）的某一属性',
        attacker_attr VARCHAR(20) NOT NULL COMMENT '进攻招式属性',
        multiplier      DECIMAL(10, 8) NOT NULL COMMENT '该单方属性下受击倍率：2 / 1 / 0.5',
        PRIMARY KEY (defender_attr, attacker_attr),
        KEY idx_matchup_defender (defender_attr),
        KEY idx_matchup_attacker (attacker_attr)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单方属性受击倍率（由属性.json 生成）';
    """,

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
        KEY idx_name (name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='精灵基础图鉴';
    """,

    # 精灵蛋组（一只精灵多个蛋组，关联 pokemon.id）
    """
    CREATE TABLE IF NOT EXISTS pokemon_egg_group (
        id           INT          NOT NULL AUTO_INCREMENT,
        pokemon_id INT          NOT NULL COMMENT '关联 pokemon.id',
        group_name   VARCHAR(50)  NOT NULL COMMENT '蛋组名称',
        PRIMARY KEY (id),
        UNIQUE KEY uk_pokemon_group (pokemon_id, group_name),
        KEY idx_group_name (group_name),
        CONSTRAINT fk_peg_pokemon FOREIGN KEY (pokemon_id) REFERENCES pokemon (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='精灵蛋组';
    """,

    # 精灵属性（一个精灵可有多个属性）
    """
    CREATE TABLE IF NOT EXISTS pokemon_attribute (
        id          INT          NOT NULL AUTO_INCREMENT,
        pokemon_name VARCHAR(50) NOT NULL COMMENT '关联 pokemon.name',
        attr_name   VARCHAR(20)  NOT NULL COMMENT '属性名，如 草/火/水',
        attr_image  VARCHAR(255) NOT NULL DEFAULT '' COMMENT '属性图标路径',
        PRIMARY KEY (id),
        KEY idx_pokemon_name (pokemon_name)
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

# 将接口中的立绘路径 /pokemon/... 转为前端蛋组精灵目录 /eggs/sprites/...
SQL_NORMALIZE_POKEMON_IMAGES = """
UPDATE pokemon
SET image = CONCAT('/eggs/sprites/', SUBSTRING(image, LENGTH('/pokemon/') + 1))
WHERE image LIKE '/pokemon/%'
"""


def normalize_pokemon_image_paths(cur) -> None:
    """将 image 中 `/pokemon/` 前缀替换为 `/eggs/sprites/`（与建表后迁移逻辑一致）。"""
    cur.execute(SQL_NORMALIZE_POKEMON_IMAGES)


def init_db() -> None:
    """先删表再建表：会清空上述表的全部数据，结构以当前 DDL 为准。"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for name in _DROP_ORDER:
                cur.execute(f"DROP TABLE IF EXISTS `{name}`")
            for ddl in _SCHEMAS:
                cur.execute(ddl)
            normalize_pokemon_image_paths(cur)
        conn.commit()
        print("[schema] 数据库表初始化完成")
    finally:
        conn.close()
