#!/usr/bin/env bash
# 自动生成：技能图标备份下载脚本
# 共 464 个图标
set -euo pipefail

DEST_DIR="${1:-./skill_icons_backup}"
mkdir -p "$DEST_DIR"
cd "$DEST_DIR"

# -x 保留远端目录；-nH 去掉主机名层；-nc 已存在则跳过（断点续传）
WGET_OPTS=(-x -nH -nc --tries=3 --timeout=20)

# 一拳
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/一拳.png"
# 三连破
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/三连破.png"
# 不动如山
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/不动如山.png"
# 不可接触
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/不可接触.png"
# 丢冰块
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/丢冰块.png"
# 丰饶
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/丰饶.png"
# 主场优势
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/主场优势.png"
# 主轴
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/主轴.png"
# 乘胜追击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/乘胜追击.png"
# 乘风
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/乘风.png"
# 乱打
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/乱打.png"
# 二律背反
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/二律背反.png"
# 交叉闪电
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/交叉闪电.png"
# 仙人掌刺击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/仙人掌刺击.png"
# 以毒攻毒
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/以毒攻毒.png"
# 以重制重
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/以重制重.png"
# 休息回复
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/休息回复.png"
# 传感器
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/传感器.png"
# 伪造账单
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/伪造账单.png"
# 伺机而动
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/伺机而动.png"
# 俯冲猛击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/俯冲猛击.png"
# 借用
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/借用.png"
# 倾泻
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/倾泻.png"
# 假寐
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/假寐.png"
# 偷师
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/偷师.png"
# 偷袭
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/偷袭.png"
# 充分燃烧
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/充分燃烧.png"
# 先发制人
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/先发制人.png"
# 光之矛
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/光之矛.png"
# 光刃
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/光刃.png"
# 光合作用
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/光合作用.png"
# 光球
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/光球.png"
# 光能聚集
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/光能聚集.png"
# 冥想
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冥想.png"
# 冬至
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冬至.png"
# 冰冻光线
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冰冻光线.png"
# 冰墙
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冰墙.png"
# 冰天雪地
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冰天雪地.png"
# 冰捆缚
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冰捆缚.png"
# 冰晶坠
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冰晶坠.png"
# 冰点
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冰点.png"
# 冰爪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冰爪.png"
# 冰锋横扫
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冰锋横扫.png"
# 冰锥
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冰锥.png"
# 冰雹
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冰雹.png"
# 冲撞
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冲撞.png"
# 冷风
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/冷风.png"
# 击鼓传花
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/击鼓传花.png"
# 刺盾
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/刺盾.png"
# 刺藤
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/刺藤.png"
# 剧毒
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/剧毒.png"
# 力量吞噬
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/力量吞噬.png"
# 力量增效
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/力量增效.png"
# 加固
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/加固.png"
# 加大功率
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/加大功率.png"
# 勾魂
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/勾魂.png"
# 化劲
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/化劲.png"
# 升龙咆哮
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/升龙咆哮.png"
# 午夜噪音
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/午夜噪音.png"
# 压扁
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/压扁.png"
# 双响炮
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/双响炮.png"
# 双星
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/双星.png"
# 双联脉冲
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/双联脉冲.png"
# 反击拳
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/反击拳.png"
# 反弹
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/反弹.png"
# 取念
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/取念.png"
# 叠势
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/叠势.png"
# 叶绿光束
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/叶绿光束.png"
# 后发制人
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/后发制人.png"
# 吓退
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/吓退.png"
# 吞噬
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/吞噬.png"
# 吨位压制
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/吨位压制.png"
# 听桥
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/听桥.png"
# 吹火
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/吹火.png"
# 吹炎
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/吹炎.png"
# 咆哮
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/咆哮.png"
# 啃咬
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/啃咬.png"
# 啄击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/啄击.png"
# 啮合传递
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/啮合传递.png"
# 嗜痛
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/嗜痛.png"
# 嘲弄
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/嘲弄.png"
# 噬心
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/噬心.png"
# 四维降解
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/四维降解.png"
# 回旋踢
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/huixuanti.png"
# 回旋风暴
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/回旋风暴.png"
# 地刺
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/地刺.png"
# 地陷
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/地陷.png"
# 地震
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/地震.png"
# 坍缩
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/坍缩.png"
# 坟场搏击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/坟场搏击.png"
# 垂死反击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/垂死反击.png"
# 埋伏
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/埋伏.png"
# 增程电池
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/增程电池.png"
# 壁垒
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/壁垒.png"
# 复写
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/复写.png"
# 多维击打
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/多维击打.png"
# 大爆炸
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/大爆炸.png"
# 天光
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/天光.png"
# 天旋地转
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/天旋地转.png"
# 天洪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/天洪.png"
# 天火
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/天火.png"
# 孢子
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/孢子.png"
# 孢子爆散
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/孢子爆散.png"
# 富养化
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/富养化.png"
# 寒风吹
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/寒风吹.png"
# 寸拳
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/寸拳.png"
# 导电撞击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/导电撞击.png"
# 尾后针
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/尾后针.png"
# 山火
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/山火.png"
# 岩土暴击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/岩土暴击.png"
# 岩脉崩毁
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/岩脉崩毁.png"
# 崩拳
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/崩拳.png"
# 幻象
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/幻象.png"
# 幽灵爆发
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/幽灵爆发.png"
# 应激反应
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/应激反应.png"
# 引燃
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/引燃.png"
# 引雷
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/引雷.png"
# 强制重启
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/强制重启.png"
# 当头棒喝
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/当头棒喝.png"
# 彗星
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/彗星.png"
# 影袭
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/影袭.png"
# 彼岸之手
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/彼岸之手.png"
# 徒长
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/徒长.png"
# 心灵洞悉
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/心灵洞悉.png"
# 快速移动
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/快速移动.png"
# 念力膨胀
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/念力膨胀.png"
# 怒火
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/怒火.png"
# 怨力打击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/怨力打击.png"
# 恐吓
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/恐吓.png"
# 恶作剧
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/恶作剧.png"
# 恶念交换
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/恶念交换.png"
# 恶意逃离
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/恶意逃离.png"
# 恶能量
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/恶能量.png"
# 惊吓盒子
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/惊吓盒子.png"
# 感染病
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/感染病.png"
# 感电
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/感电.png"
# 截拳
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/截拳.png"
# 扇风
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/扇风.png"
# 打湿
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/打湿.png"
# 打雪仗
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/打雪仗.png"
# 打鼾
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/打鼾.png"
# 扫尾
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/扫尾.png"
# 扬沙
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/扬沙.png"
# 技巧打击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/技巧打击.png"
# 抓挠
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/抓挠.png"
# 折射
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/折射.png"
# 折线冲击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/折线冲击.png"
# 抛石
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/抛石.png"
# 报复
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/报复.png"
# 抽枝
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/抽枝.png"
# 拆卸
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/拆卸.png"
# 拍击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/拍击.png"
# 持续高温
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/持续高温.png"
# 捆缚
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/捆缚.png"
# 捧杀
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/捧杀.png"
# 掠夺
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/掠夺.png"
# 掩护
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/掩护.png"
# 提气
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/提气.png"
# 摇篮曲
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/摇篮曲.png"
# 撒娇
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/撒娇.png"
# 撕咬
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/撕咬.png"
# 撕裂
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/撕裂.png"
# 操控
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/操控.png"
# 放晴
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/放晴.png"
# 散手
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/散手.png"
# 斩断
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/斩断.png"
# 旋转突击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/旋转突击.png"
# 无影脚
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/无影脚.png"
# 无畏之心
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/无畏之心.png"
# 易燃物质
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/易燃物质.png"
# 星云漩涡
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/星云漩涡.png"
# 星星撞击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/星星撞击.png"
# 星轨裂变
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/星轨裂变.png"
# 星链
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/星链.png"
# 晒太阳
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/晒太阳.png"
# 暗突袭
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/暗突袭.png"
# 暗箱操作
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/暗箱操作.png"
# 暴风眼
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/暴风眼.png"
# 暴风雪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/暴风雪.png"
# 月光合奏
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/月光合奏.png"
# 有效预防
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/有效预防.png"
# 杠杆置换
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/杠杆置换.png"
# 极寒领域
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/极寒领域.png"
# 极限撕裂
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/极限撕裂.png"
# 架势
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/架势.png"
# 根吸收
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/根吸收.png"
# 栽赃
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/栽赃.png"
# 械斗
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/械斗.png"
# 棘刺
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/棘刺.png"
# 棘突
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/棘突.png"
# 欺诈契约
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/欺诈契约.png"
# 毒囊
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/毒囊.png"
# 毒孢子
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/毒孢子.png"
# 毒沼
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/毒沼.png"
# 毒泡泡
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/毒泡泡.png"
# 毒液渗透
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/毒液渗透.png"
# 毒针
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/毒针.png"
# 毒雾
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/毒雾.png"
# 气势一击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/气势一击.png"
# 气沉丹田
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/气沉丹田.png"
# 气泡
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/气泡.png"
# 气波
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/气波.png"
# 氧输送
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/氧输送.png"
# 水光冲击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/水光冲击.png"
# 水刃
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/水刃.png"
# 水幕冲击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/水幕冲击.png"
# 水弹
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/水弹.png"
# 水弹枪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/水弹枪.png"
# 水泡盾
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/水泡盾.png"
# 水波术
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/水波术.png"
# 水炮
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/水炮.png"
# 水环
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/水环.png"
# 水花四溅
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/水花四溅.png"
# 汲取
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/汲取.png"
# 沙涌
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/沙涌.png"
# 泡沫
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/泡沫.png"
# 泡沫幻影
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/泡沫幻影.png"
# 泥巴喷射
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/泥巴喷射.png"
# 泥浆
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/泥浆.png"
# 泥浆铠甲
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/泥浆铠甲.png"
# 洗礼
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/洗礼.png"
# 流星火雨
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/流星火雨.png"
# 流沙
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/流沙.png"
# 流火
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/流火.png"
# 消毒法
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/消毒法.png"
# 涌泉
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/涌泉.png"
# 润泽
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/润泽.png"
# 淤泥表皮
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/淤泥表皮.png"
# 淬火
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/淬火.png"
# 湮灭
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/湮灭.png"
# 溃烂触碰
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/溃烂触碰.png"
# 滚雪球
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/猛烈撞击.png"
# 漫反射
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/漫反射.png"
# 潮汐
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/潮汐.png"
# 潮涌
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/潮涌.png"
# 激怒
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/激怒.png"
# 激流
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/激流.png"
# 火云车
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/火云车.png"
# 火焰冲锋
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/火焰冲锋.png"
# 火焰切割
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/火焰切割.png"
# 火焰护盾
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/火焰护盾.png"
# 火焰箭
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/火焰箭.png"
# 火爪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/火爪.png"
# 火苗
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/火苗.png"
# 灵光
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/灵光.png"
# 灵媒
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/灵媒.png"
# 灼伤
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/灼伤.png"
# 灾厄
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/灾厄.png"
# 炎息
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/炎息.png"
# 炎打
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/炎打.png"
# 炎枪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/炎枪.png"
# 炙热波动
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/炙热波动.png"
# 烈焰风暴
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/烈焰风暴.png"
# 热气
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/热气.png"
# 热砂
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/热砂.png"
# 热身
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/热身.png"
# 热身运动
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/热身运动.png"
# 焚毁
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/焚毁.png"
# 焚烧烙印
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/焚烧烙印.png"
# 燃尽
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/燃尽.png"
# 爆冲
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/爆冲.png"
# 爆米花爆破
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/爆米花爆破.png"
# 爆裂飞弹
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/爆裂飞弹.png"
# 牵连
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/牵连.png"
# 球状闪电
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/球状闪电.png"
# 甜心续航
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/甜心续航.png"
# 生日蛋糕
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/生日蛋糕.png"
# 甩水
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/甩水.png"
# 电弧
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/电弧.png"
# 电流
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/电流.png"
# 电磁偏转
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/电磁偏转.png"
# 电离爆破
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/电离爆破.png"
# 疫病吐息
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/疫病吐息.png"
# 疾风刺
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/疾风刺.png"
# 疾风连袭
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/疾风连袭.png"
# 瘴气喷射
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/瘴气喷射.png"
# 盐水浴
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/盐水浴.png"
# 盛开
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/盛开.png"
# 瞬间零度
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/瞬间零度.png"
# 石肤术
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/石肤术.png"
# 石锁
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/石锁.png"
# 砂糖弹球
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/砂糖弹球.png"
# 破绽
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/破绽.png"
# 破罐破摔
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/破罐破摔.png"
# 破防
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/破防.png"
# 硬化
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/硬化.png"
# 硬门
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/硬门.png"
# 碎冰冰
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/碎冰冰.png"
# 碰爪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/碰爪.png"
# 磁干扰
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/磁干扰.png"
# 磁暴
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/磁暴.png"
# 示弱
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/示弱.png"
# 离子火花
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/离子火花.png"
# 离子震荡
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/离子震荡.png"
# 种子弹
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/种子弹.png"
# 种皮爆裂
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/种皮爆裂.png"
# 移花接木
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/移花接木.png"
# 空间压迫
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/空间压迫.png"
# 穿膛
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/穿膛.png"
# 突袭
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/突袭.png"
# 等价交换
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/等价交换.png"
# 筛管奔流
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/筛管奔流.png"
# 粒子对撞
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/粒子对撞.png"
# 精神扰乱
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/精神扰乱.png"
# 纤维化
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/纤维化.png"
# 绵里藏针
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/绵里藏针.png"
# 缠丝劲
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/缠丝劲.png"
# 网缚
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/网缚.png"
# 羽刃
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/羽刃.png"
# 羽化加速
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/羽化加速.png"
# 羽翼庇护
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/羽翼庇护.png"
# 翅刃
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/翅刃.png"
# 翼击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/翼击.png"
# 耀眼
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/耀眼.png"
# 聒噪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/聒噪.png"
# 联动装置
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/联动装置.png"
# 聚盐
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/聚盐.png"
# 肥皂泡
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/肥皂泡.png"
# 背袭
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/背袭.png"
# 能量刃
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/能量刃.png"
# 能量守恒
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/能量守恒.png"
# 能量炮
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/能量炮.png"
# 脉冲光线
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/脉冲光线.png"
# 腐化
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/腐化.png"
# 腐蚀酸液
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/腐蚀酸液.png"
# 花炮
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/花炮.png"
# 花香
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/花香.png"
# 芳香诱引
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/芳香诱引.png"
# 荆棘爪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/荆棘爪.png"
# 落井下毒
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/落井下毒.png"
# 落星
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/落星.png"
# 落石
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/落石.png"
# 落雨
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/落雨.png"
# 落雷
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/落雷.png"
# 蓄势待发
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/蓄势待发.png"
# 蓄水
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/蓄水.png"
# 蓄能轰击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/蓄能轰击.png"
# 藤绞
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/藤绞.png"
# 虚假破产
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/虚假破产.png"
# 虚化
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/虚化.png"
# 虫击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/虫击.png"
# 虫刺
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/虫刺.png"
# 虫结阵
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/虫结阵.png"
# 虫网
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/虫网.png"
# 虫群
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/虫群.png"
# 虫群智慧
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/虫群智慧.png"
# 虫群过境
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/虫群过境.png"
# 虫茧
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/虫茧.png"
# 虫蛊
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/虫蛊.png"
# 虫鸣
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/虫鸣.png"
# 虹光冲击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/虹光冲击.png"
# 蛰针
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/蛰针.png"
# 蜡质膜
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/蜡质膜.png"
# 蝙蝠
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/蝙蝠.png"
# 血气
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/血气.png"
# 裂石
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/裂石.png"
# 见招拆招
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/见招拆招.png"
# 角击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/角击.png"
# 触底强击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/触底强击.png"
# 触电
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/触电.png"
# 许愿星
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/许愿星.png"
# 诋毁
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/诋毁.png"
# 诡刺
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/诡刺.png"
# 贪婪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/贪婪.png"
# 贮藏
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/贮藏.png"
# 贯手
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/贯手.png"
# 赤子之心
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/赤子之心.png"
# 趁火打劫
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/趁火打劫.png"
# 超导
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/超导.png"
# 超导加速
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/超导加速.png"
# 超新星馈赠
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/超新星馈赠.png"
# 超级糖果
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/超级糖果.png"
# 超维投射
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/超维投射.png"
# 跌落
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/跌落.png"
# 践踏
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/践踏.png"
# 跺地
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/跺地.png"
# 轴承支撑
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/轴承支撑.png"
# 过曝
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/过曝.png"
# 过载回路
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/过载回路.png"
# 远程访问
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/远程访问.png"
# 连续毒针
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/连续毒针.png"
# 连续爪击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/连续爪击.png"
# 迫害
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/迫害.png"
# 迫近攻击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/迫近攻击.png"
# 追打
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/追打.png"
# 退化
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/退化.png"
# 逆袭
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/逆袭.png"
# 透射
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/透射.png"
# 速冻
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/速冻.png"
# 遁地
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/遁地.png"
# 酶浓度调整
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/酶浓度调整.png"
# 重击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/重击.png"
# 金属噪音
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/金属噪音.png"
# 针状物
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/针状物.png"
# 钢钻
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/钢钻.png"
# 钢铁洪流
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/钢铁洪流.png"
# 钧势
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/钧势.png"
# 锐利眼神
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/锐利眼神.png"
# 错乱
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/错乱.png"
# 镜像反射
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/镜像反射.png"
# 闪光
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/闪光.png"
# 闪光冲击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/闪光冲击.png"
# 闪击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/闪击.png"
# 闪击折返
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/闪击折返.png"
# 闪燃
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/闪燃.png"
# 防反
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/防反.png"
# 防御
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/防御.png"
# 防御反击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/防御反击.png"
# 阳火增辉
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/阳火增辉.png"
# 阻断
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/阻断.png"
# 降灵
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/降灵.png"
# 除厄
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/除厄.png"
# 陨石
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/陨石.png"
# 隐藏条款
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/隐藏条款.png"
# 隼鳞
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/隼鳞.png"
# 集中
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/集中.png"
# 雪替身
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/雪替身.png"
# 雪球
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/雪球.png"
# 雷暴
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/雷暴.png"
# 雾气环绕
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/雾气环绕.png"
# 震击
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/震击.png"
# 霜冻
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/霜冻.png"
# 霜天
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/霜天.png"
# 霜降
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/霜降.png"
# 鞭打
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/鞭打.png"
# 音波弹
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/音波弹.png"
# 音爆
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/音爆.png"
# 顶端优势
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/顶端优势.png"
# 预备势
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/预备势.png"
# 风吹雪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/风吹雪.png"
# 风墙
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/风墙.png"
# 风矢
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/风矢.png"
# 风起
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/风起.png"
# 风隐
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/风隐.png"
# 飞叶
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/飞叶.png"
# 飞吻
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/飞吻.png"
# 飞断
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/飞断.png"
# 飞羽
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/飞羽.png"
# 飞踢
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/飞踢.png"
# 食腐
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/食腐.png"
# 高温回火
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/高温回火.png"
# 鬼火
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/鬼火.png"
# 魅惑
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/魅惑.png"
# 魔法增效
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/魔法增效.png"
# 魔爪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/魔爪.png"
# 魔能爆
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/魔能爆.png"
# 鸣叫
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/鸣叫.png"
# 鸣沙陷阱
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/鸣沙陷阱.png"
# 鸩毒
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/鸩毒.png"
# 鹰爪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/鹰爪.png"
# 麻痹
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/麻痹.png"
# 黑手
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/黑手.png"
# 鼓劲
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/鼓劲.png"
# 齿轮切开
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/齿轮切开.png"
# 齿轮扭矩
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/齿轮扭矩.png"
# 龙之利爪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/龙之利爪.png"
# 龙卷风
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/龙卷风.png"
# 龙吟
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/龙吟.png"
# 龙吼
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/龙吼.png"
# 龙威
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/龙威.png"
# 龙息环爆
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/龙息环爆.png"
# 龙炮
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/龙炮.png"
# 龙爪
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/龙爪.png"
# 龙血
wget "${WGET_OPTS[@]}" "https://rocom.game-walkthrough.com/skills/龙血.png"

echo "[done] 备份目录：$DEST_DIR"
