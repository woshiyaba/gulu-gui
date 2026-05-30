-- ============================================================
-- 宠物对话功能
-- 1) pet_prompt        每只宠物（精灵）绑定一段独立的人设 prompt
-- 2) pet_prompt_extra  用户对某只宠物的个性化补充（昵称 / 性格 / 伙伴关系等，可扩展）
-- ============================================================

-- ------------------------------------------------------------
-- 宠物人设 prompt 表：宠物 id ↔ prompt 一对一
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pet_prompt (
    id          SERIAL       PRIMARY KEY,
    pet_id      INT          NOT NULL,                 -- 宠物（精灵）id
    prompt      TEXT         NOT NULL DEFAULT '',      -- 该宠物的独立人设 prompt
    enabled     BOOLEAN      NOT NULL DEFAULT FALSE,    -- 是否启用对话
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_pet_prompt_pet UNIQUE (pet_id)
);

-- ------------------------------------------------------------
-- 用户个性化补充表：同一个用户对同一只宠物只有一条配置
-- 常用字段（昵称）单列存储，其余可扩展字段（性格 / 伙伴关系 / ...）
-- 以键值对形式存进 attributes(JSONB)，便于随时新增字段而无需改表结构。
-- attributes 示例：{"性格": "活泼好动", "伙伴关系": "形影不离的好搭档", "口头禅": "嘿嘿"}
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pet_prompt_extra (
    id          SERIAL       PRIMARY KEY,
    user_id     BIGINT       NOT NULL,                 -- 用户 id
    pet_id      INT          NOT NULL,                 -- 宠物（精灵）id
    nickname    VARCHAR(50)  NOT NULL DEFAULT '',      -- 用户给宠物起的昵称
    attributes  JSONB        NOT NULL DEFAULT '{}'::jsonb, -- 可扩展的补充属性（键值对）
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_pet_prompt_extra_user_pet UNIQUE (user_id, pet_id)
);

CREATE INDEX IF NOT EXISTS idx_pet_prompt_extra_user ON pet_prompt_extra(user_id);

-- ------------------------------------------------------------
-- 宠物对话历史表：按"用户 × 宠物"保存每一条消息
-- ws 断开连接时落库；下次开启对话时回放给前端并加载进 agent 上下文。
-- role: 'user' = 主人，'assistant' = 宠物
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pet_chat_message (
    id          BIGSERIAL    PRIMARY KEY,
    user_id     BIGINT       NOT NULL,                 -- 用户 id
    pet_id      INT          NOT NULL,                 -- 宠物（精灵）id
    role        VARCHAR(16)  NOT NULL,                 -- user / assistant
    content     TEXT         NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pet_chat_message_conv ON pet_chat_message(user_id, pet_id, id);
