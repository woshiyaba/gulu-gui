-- lkgc 蛋组映射表
-- lkgc 接口返回的 egg_type_list 数值 → 中文蛋组名
-- 用法同 lkgc_skill_type，作为字典表供业务代码 join 使用

CREATE TABLE IF NOT EXISTS lkgc_egg_group (
    id   SERIAL       PRIMARY KEY,
    name VARCHAR(30)  NOT NULL
);

INSERT INTO lkgc_egg_group (id, name) VALUES
    (  1, '巨灵组'),
    (  2, '两栖组'),
    (  3, '昆虫组'),
    (  4, '天空组'),
    (  5, '动物组'),
    (  6, '妖精组'),
    (  7, '植物组'),
    (  8, '拟人组'),
    (  9, '软体组'),
    ( 10, '大地组'),
    ( 11, '魔力组'),
    ( 12, '海洋组'),
    ( 13, '龙组'),
    ( 14, '机械组'),
    (999, '无法孵蛋组')
ON CONFLICT (id) DO NOTHING;
