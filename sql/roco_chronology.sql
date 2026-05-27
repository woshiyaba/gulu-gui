-- 洛克纪年 / 洛克大事记
-- 记录某个时间发生的事件：时间 + 标题 + 正文 + 图片（多张）。
-- 后台维护（增删改），前台按时间倒序展示列表并可查看图文详情。

CREATE TABLE IF NOT EXISTS roco_chronology (
    id          SERIAL       PRIMARY KEY,
    event_date  DATE         NOT NULL,                       -- 事件发生时间
    title       VARCHAR(200) NOT NULL DEFAULT '',            -- 标题
    content     TEXT         NOT NULL DEFAULT '',            -- 正文
    images      JSONB        NOT NULL DEFAULT '[]'::jsonb,   -- 图片 URL 数组
    sort_order  INT          NOT NULL DEFAULT 0,             -- 同日排序，越大越靠前
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,          -- 是否对前台可见
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_roco_chronology_date
    ON roco_chronology (event_date DESC, sort_order DESC, id DESC);
