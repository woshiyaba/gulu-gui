-- ============================================================
-- 用户反馈功能
-- 用户在小程序「更多」页提交反馈（内容 + 可选联系方式 + 可选分类），
-- 保存在数据库中供后台查看与处理。status 标记处理进度。
-- 建表语句不随应用自动执行，需手动建表。
-- ============================================================

CREATE TABLE IF NOT EXISTS user_feedback (
    id            BIGSERIAL    PRIMARY KEY,
    user_id       BIGINT,                                  -- 提交用户 id（匿名时为空）
    content       TEXT         NOT NULL,                   -- 反馈内容
    contact       VARCHAR(128),                            -- 联系方式（可选）
    feedback_type VARCHAR(32),                             -- 反馈分类（可选，如 bug/建议/其他）
    status        VARCHAR(16)  NOT NULL DEFAULT 'pending', -- 处理状态：pending / handled
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- 后台按时间倒序查看，可按状态过滤
CREATE INDEX IF NOT EXISTS idx_user_feedback_status_created
    ON user_feedback (status, created_at DESC);
