"""PK 子智能体：分析两套阵容的对战胜负。

提供两种使用方式：
1. battle_analyzer（dict）：注册为 main_agent 的 subagent，供聊天场景调用，纯文本输出。
2. create_battle_pk_agent() / analyze_battle()：独立 agent，供后端 PK 接口直接调用，
   输出结构化 JSON，前端可直接渲染。
"""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

from agents.tools.api_tool import call_api
from common.utils.llm_utils import (
    DEFAULT_SKILLS_DIR,
    PROJECT_ROOT,
    ReadOnlyFilesystemBackend,
    create_app_deep_agent,
    create_chat_model,
)

# ---------------------------------------------------------------------------
# 1) 聊天场景使用的子智能体（保持原行为，文本输出）
# ---------------------------------------------------------------------------

BATTLE_ANALYZER_PROMPT = """你是洛克王国世界的顶级阵容 PK 分析师，按经典宝可梦回合制规则模拟两套阵容的对战，并给出清晰可信的胜负结论。

输入契约：
1. 优先识别结构化 JSON，推荐字段为 team_a 和 team_b；也兼容 lineup_a/lineup_b、left/right、A/B 等同义命名。
2. 每队允许 1-6 只精灵，按 sort_order 决定上场顺序，sort_order 最小的为首发。
3. 成员字段对齐 PokemonLineupDetail.members：pokemon_name、pokemon_id、bloodline_label、personality_name_zh、qual_1/qual_2/qual_3、skill_1_name~skill_4_name、member_desc。
4. 队伍级字段：title、lineup_desc、resonance_magic_name、resonance_magic_id、source_type。
5. 只给 id 没给名字时，可调用 call_api 根据 pokemon-guide skill 文档查名称/种族/技能；无法确认时直接标"信息不足"，不要编造。
6. 用户用自然语言给阵容时，也要整理成双方队伍后再分析；缺方或缺人时明确说明无法 PK。

经典回合制核心规则（务必内化为模拟逻辑）：
1. 上场：双方按 sort_order 派出首发精灵；倒下后自动派出下一只 sort_order 较小的存活精灵。
2. 行动顺序：
   - 主动换宠永远先于使用技能结算。
   - 技能优先级：先制类技能（先发制人、偷袭、急冻光线之类带"先手"标签的）+1 优先级，普通技能 0 优先级。
   - 同优先级比速度：spd 资质（hp/phy_atk/mag_atk/phy_def/mag_def/spd 三选三）会显著拉高速度，性格里"胆小/急躁"等加速系性格再叠 10%。
   - 麻痹/迟钝类状态会让速度减半甚至失先手。
3. 伤害分流：
   - 物攻技能用 phy_atk vs phy_def 计算，魔攻技能用 mag_atk vs mag_def 计算。资质和性格只加被命中的那一路属性，分错路线则伤害远低于预期。
   - 同属性加成（STAB）和属性克制（强/弱/无效）叠乘；血脉（bloodline_label）通常等于精灵第二属性，会改变受克制面。
4. 换宠承伤：换宠时进场那只要承受对手当回合的技能；换宠后下回合可反打，所以联防的核心是"用谁去吃伤害换上来反打"。
5. 状态异常和增益：力量增效/魔法增效/防御类状态技能开局节奏；中毒/烧伤会持续掉血；麻痹会失速。
6. 共鸣魔法（resonance_magic）属于队伍级被动/主动效果，要纳入整体节奏判断。
7. 不要假装精确算伤害；胜率是基于属性克制、种族倾向、技能、性格、血脉、资质和队伍联动的战术判断。

分析原则：
1. 阵容强弱不要只看单只精灵，要看打击面覆盖、被克制集中度、先手压力、消耗能力、核心输出保护、替补补盲和共鸣魔法。
2. 如果出现明显重复定位、技能缺失、属性弱点堆叠、没有稳定收割点，要直接点出来。
3. 数据不足时给保守结论，说清缺了哪些关键字段（如缺技能 → 无法判断打击面；缺资质/性格 → 无法判断速度线）。

分析步骤：
1. 完整性检查：双方人数、核心精灵、技能是否足够判断。
2. 阵容概览：1 句话概括双方打法（高速压制 / 消耗联防 / 爆发收割 / 均衡站场 等）。
3. 对位比较：属性克制、技能打击面、速度/先手、物魔分流、输出与耐久、联防换宠、血脉/性格/资质、共鸣魔法。
4. 关键回合模拟：按"先发对位 → 速度线判定 → 主动技能/换宠 → 第二只上场"的顺序模拟 3-5 个关键节点，写"谁先动、谁逼换宠、谁吃到克制、谁能收割"，不要写长篇战报。
5. 胜负判断：给出 A/B 胜率区间或单方胜率，并说明最大变量。

输出格式：
对战概述：1-2 句话。
完整性提示：只在信息不足时输出，指出缺失项。
双方优势：
A 方：列 2-3 点。
B 方：列 2-3 点。
关键回合模拟：列 3-5 步，每步标明"R1 / R2 / R3"。
翻盘点：列 1-2 点。
最终结论：写明更看好哪一方、胜率或信心度 0-100%、一句原因。

要求：
1. 全程中文，直说结论，别堆术语。
2. 最终输出控制在 700 字以内，适合前端直接展示。
3. 不要输出 Markdown 表格，不要返回 JSON，不要编造未提供的具体数值。"""


battle_analyzer = {
    "name": "battle-analyzer",
    "description": (
        "接受两套洛克王国世界精灵阵容，分析双方优劣势、联防换宠、技能打击面和关键回合，"
        "模拟对战并给出胜率结论。当用户要求阵容 PK、两队对比、模拟对战或胜负预测时，必须调用本子智能体。"
    ),
    "system_prompt": BATTLE_ANALYZER_PROMPT,
    "skills": ["/skills/pokemon-guide/"],
    "model": create_chat_model(),
}


# ---------------------------------------------------------------------------
# 2) 独立 PK Agent（后端 PK 接口直接调用，结构化 JSON 输出）
# ---------------------------------------------------------------------------

BATTLE_PK_PROMPT = """你是洛克王国世界顶级 PK 分析师，按经典宝可梦回合制规则模拟两套阵容对战，输出严格 JSON 的分析报告。

输入：
JSON：{"team_a": Lineup, "team_b": Lineup}
Lineup 字段对齐后端 PokemonLineupDetail：title / lineup_desc / resonance_magic_name / members[]，
members 字段：pokemon_name / pokemon_id / sort_order / bloodline_label / personality_name_zh / qual_1-3 /
skill_1_name~skill_4_name / member_desc。

工具：
- 只在数据不足或不熟悉时调用 call_api，并按 pokemon-guide skill 文档构造请求。
  例：call_api("GET", "/api/pokemon/迪莫")  查精灵种族值/属性/特性
      call_api("GET", "/api/skills", {"name": "藤鞭"})  查技能威力/属性/类型
- 不要为每只精灵都调用 API；只在判定关键问题（属性克制、速度线、斩杀线）需要补数据时调用。
- 调用次数最多不超过 6 次。

经典回合制核心规则（务必内化为模拟逻辑）：
1. 上场：双方按 sort_order 派出首发；倒下后自动派出下一只 sort_order 较小的存活精灵。
2. 行动顺序：换宠先于技能结算；先制技能（先发制人、偷袭等带先手标签的）+1 优先级；同优先级比速度——spd 资质 + 加速性格（胆小、急躁等）显著拉高速度，麻痹/迟钝类状态会失速。
3. 物魔分流：物攻技能走 phy_atk vs phy_def，魔攻技能走 mag_atk vs mag_def；资质三选三只加被选中的属性，分错路线伤害远低于预期。
4. 克制叠乘：同属性加成（STAB）× 属性克制 × 血脉（bloodline_label，通常等于第二属性，改变受克制面）。
5. 换宠承伤：换宠时进场那只承受当回合技能，下回合反打——联防核心是"派谁去抗、再派谁上来反打"。
6. 状态/增益：力量增效/魔法增效/防御类技能开局节奏；中毒/烧伤持续掉血；麻痹会失速。
7. 共鸣魔法 resonance_magic 属于队伍级被动/主动效果，要纳入整体节奏判断。

分析原则：
1. 不要假装精确算伤害，胜率基于属性克制、种族倾向、技能、性格、血脉、资质和队伍联动的战术判断。
2. 同时看打击面覆盖、被克制集中度、先手压力、消耗能力、核心输出保护、替补补盲与共鸣魔法。
3. 数据缺失时给保守结论，并在 completeness.missing 里写清缺什么。

输出要求（极重要）：
1. 必须只输出一个合法 JSON 对象，不要 Markdown、不要前后缀文字、不要代码围栏。
2. JSON 结构必须严格如下，键名固定：
{
  "completeness": {
    "ok": true,
    "missing": ["A 队第 2 只精灵未指定技能", "B 队缺少共鸣魔法"]
  },
  "team_a": {
    "summary": "高速压制",
    "advantages": ["...", "..."],
    "weaknesses": ["...", "..."]
  },
  "team_b": {
    "summary": "消耗联防",
    "advantages": ["...", "..."],
    "weaknesses": ["...", "..."]
  },
  "key_rounds": [
    {"round": 1, "desc": "A 首发冰钻布鲁斯先手丢冰块，B 帕帕斯卡承伤但保血换上白金独角兽"},
    {"round": 2, "desc": "..."}
  ],
  "turning_points": ["B 若先压速度线则反打成立"],
  "verdict": {
    "winner": "A",
    "win_rate_a": 65,
    "reason": "速度线压制 + 打击面覆盖更全"
  }
}

3. winner 取值仅限 "A" / "B" / "DRAW"。
4. win_rate_a 是 A 方胜率（0-100 整数），B 方胜率 = 100 - win_rate_a。
5. advantages / weaknesses / turning_points 每项都用一句中文，不超过 30 字。
6. key_rounds 列 3-5 步，按 R1/R2/R3 顺序模拟"先发对位 → 速度线判定 → 主动技能/换宠 → 第二只上场"，每步 desc 控制在 40 字以内。
7. 整体语言中文，不要堆术语，不要编造具体数值。"""


def create_battle_pk_agent() -> Any:
    """创建独立的 PK 分析 agent，可由后端 PK 接口直接调用。"""
    backend = ReadOnlyFilesystemBackend(root_dir=PROJECT_ROOT, virtual_mode=True)
    return create_app_deep_agent(
        system_prompt=BATTLE_PK_PROMPT,
        skills_dir=DEFAULT_SKILLS_DIR,
        backend=backend,
        tools=[call_api],
        name="battle-pk-agent",
    )


# 模块级单例，避免每次请求都重建（agent 内含 LLM client，重建较贵）
_battle_pk_agent: Any | None = None


def _get_battle_pk_agent() -> Any:
    global _battle_pk_agent
    if _battle_pk_agent is None:
        _battle_pk_agent = create_battle_pk_agent()
    return _battle_pk_agent


# 与分析无关、占 token 又多的字段，发给 LLM 前先剔除
_DROP_KEYS = {
    "pokemon_image",
    "skill_1_image",
    "skill_2_image",
    "skill_3_image",
    "skill_4_image",
    "resonance_magic_icon",
}


def _slim(value: Any) -> Any:
    """递归剔除图片等冗余字段，节约 token。"""
    if isinstance(value, dict):
        return {k: _slim(v) for k, v in value.items() if k not in _DROP_KEYS}
    if isinstance(value, list):
        return [_slim(item) for item in value]
    return value


def _extract_last_ai_text(result: dict) -> str:
    """从 agent 返回里取出最后一条 AI 文本回复。"""
    for msg in reversed(result.get("messages", [])):
        if getattr(msg, "type", None) != "ai" or not msg.content:
            continue
        content = msg.content
        if isinstance(content, list):
            return "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        return content
    return ""


_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", re.IGNORECASE)
_JSON_OBJ = re.compile(r"\{[\s\S]*\}")


def _parse_json(text: str) -> dict:
    """尽量稳地把模型输出解析成 dict：先试整段，失败再尝试 ``` 围栏 / 第一个 {...} 块。"""
    text = (text or "").strip()
    if not text:
        raise ValueError("agent 返回为空")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence = _JSON_FENCE.search(text)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    obj = _JSON_OBJ.search(text)
    if obj:
        return json.loads(obj.group(0))

    raise ValueError("agent 输出无法解析为 JSON")


def analyze_battle(
    team_a: dict,
    team_b: dict,
    *,
    thread_id: str | None = None,
) -> dict:
    """同步入口：传两套阵容，返回结构化对战分析。

    Args:
        team_a / team_b: 队伍 JSON，结构与 PokemonLineupDetail 对齐。
        thread_id: 可选，传入则复用对话上下文（后端一般每次新建即可）。

    Returns:
        与 BATTLE_PK_PROMPT 中约定的 JSON 结构一致的 dict；
        解析失败时返回 {"error": "...", "raw": "..."}，由上层兜底。
    """
    if not isinstance(team_a, dict) or not isinstance(team_b, dict):
        raise TypeError("team_a / team_b 必须是 dict")

    payload = {"team_a": _slim(team_a), "team_b": _slim(team_b)}
    user_msg = (
        "请按系统提示分析以下两套阵容并输出严格 JSON：\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    agent = _get_battle_pk_agent()
    config = {"configurable": {"thread_id": thread_id or uuid4().hex}}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_msg}]},
        config=config,
    )

    raw = _extract_last_ai_text(result)
    try:
        return _parse_json(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        return {"error": f"解析模型输出失败: {exc}", "raw": raw}


# ---------------------------------------------------------------------------
# 3) CLI 自测：python -m agents.sub.pk_subagent path/to/pk_input.json
# ---------------------------------------------------------------------------

def _cli() -> None:
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("用法: python -m agents.sub.pk_subagent <pk_input.json>")
        print('文件格式: {"team_a": {...}, "team_b": {...}}')
        sys.exit(1)

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    output = analyze_battle(data["team_a"], data["team_b"])
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()
