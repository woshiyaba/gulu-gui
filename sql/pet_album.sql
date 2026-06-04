-- ============================================================
-- 精灵相册功能
-- 用户上传与某只宠物的合照，保存在数据库中；可标记为"精选"，
-- 精选照片永远排在最前面展示。删除照片时同步从 OSS 删除对象。
-- ============================================================

CREATE TABLE IF NOT EXISTS pet_album (
    id          BIGSERIAL    PRIMARY KEY,
    user_id     BIGINT       NOT NULL,                 -- 用户 id
    pet_id      INT          NOT NULL,                 -- 宠物（精灵）id
    image_url   TEXT         NOT NULL,                 -- 图片访问 URL（OSS 地址）
    is_featured BOOLEAN      NOT NULL DEFAULT FALSE,   -- 是否精选（精选永远排在前面）
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- 按"用户 × 宠物"查询，精选优先、再按时间倒序
CREATE INDEX IF NOT EXISTS idx_pet_album_user_pet
    ON pet_album (user_id, pet_id, is_featured DESC, created_at DESC);
