-- ============================================================
-- 换蛋广场 + 用户私聊/通用消息
-- 1) change_egg_listing  换蛋挂单：拥有(pokemon_id+tag) / 需求(pokemon_id+tag)
-- 2) change_egg_match    命中记录：双向吻合的两条挂单，去重避免重复通知
-- 3) user_message        用户私聊 / 通用消息：在线 ws 实时下发，离线落库待补发
--
-- 表会在仓储 ensure_*() 内用 CREATE TABLE IF NOT EXISTS 自动建立，
-- 本文件仅作 schema 参考与 tag 字典种子数据。
-- ============================================================

-- ------------------------------------------------------------
-- 换蛋挂单：一条挂单 = 我拥有的蛋组 + 我需求的蛋组
-- own/want 都记录 pokemon_id（无论用户从 pokemon_egg 还是 pokemon 选取）
-- own_tag/want_tag 取自 sys_dict.dict_type='egg_exchange_tag' 的 code
-- status: open=挂牌中 / matched=已匹配 / closed=已关闭
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS change_egg_listing (
    id              BIGSERIAL    PRIMARY KEY,
    user_id         BIGINT       NOT NULL,                 -- 平台用户 id
    game_id         VARCHAR(64)  NOT NULL DEFAULT '',      -- 游戏 id（长串数字）
    own_pokemon_id  INT          NOT NULL,                 -- 拥有的精灵 id（pokemon.id）
    own_tag         VARCHAR(30)  NOT NULL DEFAULT '',      -- 拥有蛋组的 tag code
    want_pokemon_id INT          NOT NULL,                 -- 需求的精灵 id（pokemon.id）
    want_tag        VARCHAR(30)  NOT NULL DEFAULT '',      -- 需求蛋组的 tag code
    status          VARCHAR(16)  NOT NULL DEFAULT 'open',  -- open / matched / closed
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cel_want ON change_egg_listing (want_pokemon_id, want_tag, status);
CREATE INDEX IF NOT EXISTS idx_cel_own  ON change_egg_listing (own_pokemon_id, own_tag, status);
CREATE INDEX IF NOT EXISTS idx_cel_user ON change_egg_listing (user_id, status);

-- ------------------------------------------------------------
-- 命中记录：归一化保证 listing_a_id < listing_b_id，唯一约束防并发重复
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS change_egg_match (
    id           BIGSERIAL  PRIMARY KEY,
    listing_a_id BIGINT     NOT NULL,
    listing_b_id BIGINT     NOT NULL,
    user_a_id    BIGINT     NOT NULL,
    user_b_id    BIGINT     NOT NULL,
    created_at   TIMESTAMP  NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_cem_pair UNIQUE (listing_a_id, listing_b_id)
);

-- ------------------------------------------------------------
-- 用户私聊 / 通用消息：A→B 先落库；B 在线则 ws 实时下发并置 is_delivered，
-- B 不在线则等其上线后补发。系统通知 from_user_id 用 0。
-- msg_type: chat=私聊 / egg_match_notify=换蛋匹配通知
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_message (
    id           BIGSERIAL    PRIMARY KEY,
    from_user_id BIGINT       NOT NULL,                 -- 发送方用户 id（系统通知=0）
    to_user_id   BIGINT       NOT NULL,                 -- 接收方用户 id
    msg_type     VARCHAR(20)  NOT NULL DEFAULT 'chat',  -- chat / egg_match_notify
    content      TEXT         NOT NULL DEFAULT '',
    payload      JSONB,                                 -- 结构化附加数据（可空）
    is_delivered BOOLEAN      NOT NULL DEFAULT FALSE,    -- 是否已通过 ws 下发
    delivered_at TIMESTAMP,
    is_read      BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_um_pending ON user_message (to_user_id, is_delivered);
CREATE INDEX IF NOT EXISTS idx_um_conv    ON user_message (from_user_id, to_user_id, id);

-- ------------------------------------------------------------
-- tag 字典种子（复用 sys_dict，后台可在 /api/ops/dicts 维护）
-- ------------------------------------------------------------
INSERT INTO sys_dict (dict_type, code, label, sort_order)
VALUES
    ('egg_exchange_tag', '大块头', '大块头', 1),
    ('egg_exchange_tag', '小不点', '小不点', 2)
ON CONFLICT (dict_type, code) DO NOTHING;
