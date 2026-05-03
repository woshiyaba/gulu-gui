"""PK 子智能体：分析两套阵容的对战胜负。

提供两种使用方式：
1. battle_analyzer（dict）：注册为 main_agent 的 subagent，供聊天场景调用，纯文本输出。
2. create_battle_pk_agent() / analyze_battle()：独立 agent，供后端 PK 接口直接调用，
   输出结构化 JSON，前端可直接渲染。
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any
from uuid import uuid4

from agents.tools.api_tool import call_api
from common.utils.json_parser import extract_json_object
from common.utils.llm_utils import (
    DEFAULT_SKILLS_DIR,
    PROJECT_ROOT,
    ReadOnlyFilesystemBackend,
    create_app_deep_agent,
    create_chat_model,
)
from common.utils.writer import stream_agent_collect

# ---------------------------------------------------------------------------
# 1) 聊天场景使用的子智能体（保持原行为，文本输出）
# ---------------------------------------------------------------------------

BATTLE_ANALYZER_PROMPT = """你是洛克王国世界的顶级阵容 PK 分析师，按经典宝可梦回合制规则模拟两套阵容的对战，并给出清晰可信的胜负结论。

输入契约：
1. 优先识别结构化 JSON，推荐字段为 team_a 和 team_b；也兼容 lineup_a/lineup_b、left/right、A/B 等同义命名。
2. 每队允许 1-6 只精灵。玩家提交的 sort_order 仅作参考，最优出场顺序必须由你根据对位、速度线、克制关系重新决定。
3. 成员字段对齐 PokemonLineupDetail.members：pokemon_name、pokemon_id、bloodline_label、personality_name_zh、qual_1/qual_2/qual_3、skill_1_name~skill_4_name、member_desc。
4. 队伍级字段：title、lineup_desc、resonance_magic_name、resonance_magic_id、source_type。
5. 技能的真实威力 / 属性 / 效果 / 优先级必须通过 pokemon-guide 的 skill API 查询确认，禁止凭印象编造数值或效果；只给 id 没给名字时也要查名称、种族、技能、特性。
6. 用户用自然语言给阵容时，也要整理成双方队伍后再分析；缺方或缺人时明确说明无法 PK。

⚠️ 必须遵守的判断口径：
- 出场顺序：玩家提交的顺序往往不是最优，你要重新排序并写明理由。
- 克制计算：只看精灵本体属性 + 技能属性 + 共鸣魔法等机制；血脉（bloodline_label）不计入属性克制。
- 技能数据：必须从 API 取真实数值，未查到不要瞎编，缺数据就标"信息不足"。
- 特性 / 共鸣魔法 与 技能的应对关系是胜负关键，必须重点分析。

经典回合制核心规则（务必内化为模拟逻辑）：
1. 上场：按你重排后的最优顺序派出首发；倒下后按你的换宠策略派出下一只存活精灵。
2. 行动顺序：
   - 主动换宠永远先于使用技能结算。
   - 技能优先级：先制类技能（先发制人、偷袭、急冻光线之类带"先手"标签的）+1 优先级，普通技能 0 优先级。
   - 同优先级比速度：spd 资质（hp/phy_atk/mag_atk/phy_def/mag_def/spd 三选三）会显著拉高速度，性格里"胆小/急躁"等加速系性格再叠 10%。
   - 麻痹/迟钝类状态会让速度减半甚至失先手。
3. 伤害分流：
   - 物攻技能用 phy_atk vs phy_def 计算，魔攻技能用 mag_atk vs mag_def 计算。资质和性格只加被命中的那一路属性，分错路线则伤害远低于预期。
   - 同属性加成（STAB）和属性克制（强/弱/无效）叠乘；血脉不参与克制运算。
4. 换宠承伤：换宠时进场那只要承受对手当回合的技能；换宠后下回合可反打，所以联防的核心是"用谁去吃伤害换上来反打"。
5. 状态异常和增益：力量增效/魔法增效/防御类状态技能开局节奏；中毒/烧伤会持续掉血；麻痹会失速。
6. 共鸣魔法（resonance_magic）属于队伍级被动/主动效果，要纳入整体节奏判断。
7. 不要假装精确算伤害；胜率是基于属性克制、种族倾向、技能、性格、资质、特性和队伍联动的战术判断。

分析原则：
1. 阵容强弱不要只看单只精灵，要看打击面覆盖、被克制集中度、先手压力、消耗能力、核心输出保护、替补补盲、特性与共鸣魔法。
2. 如果出现明显重复定位、技能缺失、属性弱点堆叠、没有稳定收割点，要直接点出来。
3. 数据不足时给保守结论，说清缺了哪些关键字段（如缺技能 API 数据 → 无法判断打击面；缺资质/性格 → 无法判断速度线）。

执行流程（严格分两阶段，先计划再模拟）：
阶段 A — 计划：
  1. 先把双方精灵 / 技能 / 特性的真实数据通过 API 查清，再开始判断。
  2. 基于真实数据为双方各重排最优出场顺序（可与玩家 sort_order 不同），写明每队排序理由（首发对位、速度线、收割点）。
  3. 列出双方核心技能的应对关系（谁克谁、谁能反打、谁会被针对），并标出关键特性 / 共鸣魔法的影响。
阶段 B — 模拟：
  按阶段 A 的最优顺序与策略，模拟 3-5 个关键节点（谁先动、谁逼换宠、谁吃克制、谁能收割），不要写长篇战报。

输出格式：
对战概述：1-2 句话。
完整性提示：只在信息不足时输出，指出缺失项。
最优出场顺序：
  A 方：精灵1 → 精灵2 → ...（理由 1 句话）
  B 方：精灵1 → 精灵2 → ...（理由 1 句话）
关键应对关系：列 3-5 条（技能克制、特性反制、共鸣魔法影响）。
双方优势：
  A 方：列 2-3 点。
  B 方：列 2-3 点。
关键回合模拟：列 3-5 步，每步标明"R1 / R2 / R3"。
翻盘点：列 1-2 点。
最终结论：写明更看好哪一方、胜率或信心度 0-100%、一句原因。

要求：
1. 全程中文，直说结论，别堆术语。
2. 最终输出控制在 800 字以内，适合前端直接展示。
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

⚠️ 必须遵守的关键口径：
1. 玩家传入的 sort_order 不一定最优，必须由你重新分析最优出场顺序（首发对位、速度线、属性克制、收割点等）。
2. 属性克制只看精灵本体属性 + 技能属性 + 共鸣魔法等机制；血脉（bloodline_label）不计入克制计算。
3. 技能的威力 / 属性 / 效果 / 优先级 / 命中必须通过 call_api 查询确认，禁止凭印象编造数值或效果。
4. 特性 与 技能的应对关系是胜负关键，必须重点分析；共鸣魔法作为队伍级特性同等对待。

工具使用（必须先查全资料 → 再做模拟）：
- call_api("GET", "/api/pokemon/<名字>") 查精灵属性 / 种族值 / 特性
- call_api("GET", "/api/skills", {"name": "<技能名>"}) 查技能威力 / 属性 / 类型 / 效果 / 优先级
- 在阶段 A（计划）中把双方所有精灵 + 不同技能的真实数据全部查清，再开始模拟。
- 调用预算：通常 10-25 次；最多 30 次。命中后不要重复查同一对象。
- 查不到时在 completeness.missing 标明，并给保守结论，不要瞎编。

经典回合制规则（务必内化为模拟逻辑）：
1. 上场：按你重排后的最优顺序派出首发；倒下后按你的换宠策略派出下一只。
2. 行动顺序：换宠先于技能结算；先制技能（带先手标签）+1 优先级；同优先级比速度——spd 资质 + 加速性格（胆小、急躁等）显著拉高速度，麻痹/迟钝失速。
3. 物魔分流：物攻技能走 phy_atk vs phy_def，魔攻技能走 mag_atk vs mag_def；资质三选三只加被选中的属性，分错路线伤害远低于预期。
4. 克制叠乘：STAB（同属性加成）× 属性克制（仅看本体属性）。血脉不参与克制运算。
5. 换宠承伤：换宠时进场那只承受当回合技能，下回合反打——联防核心是"派谁去抗、再派谁上来反打"。
6. 状态/增益：力量增效/魔法增效/防御类技能开局节奏；中毒/烧伤持续掉血；麻痹失速。
7. 共鸣魔法 resonance_magic 属于队伍级被动/主动效果，纳入整体节奏判断。

执行流程（严格分两阶段）：
阶段 A — 计划（plan）：
  1. 调用 call_api 把双方所有精灵 + 技能 + 特性的真实数据查清。
  2. 基于真实数据，为双方各排出最优出场顺序（可与玩家 sort_order 不同），写明排序理由。
  3. 列出双方核心技能的应对关系矩阵（谁克谁、谁能反打、谁会被针对）。
  4. 标出每方的核心特性 / 共鸣魔法对节奏的影响。
阶段 B — 模拟（simulate）：
  按阶段 A 的最优顺序和策略，模拟 3-5 个关键回合，给出胜负判断。

分析原则：
1. 不要假装精确算伤害；胜率基于属性克制、种族倾向、技能、性格、资质、特性、共鸣魔法和队伍联动的战术判断。
2. 同时看打击面覆盖、被克制集中度、先手压力、消耗能力、核心输出保护、替补补盲、特性与共鸣魔法。
3. 数据缺失时给保守结论，并在 completeness.missing 里写清缺什么。

输出要求（极重要）：
1. 必须只输出一个合法 JSON 对象，不要 Markdown、不要前后缀文字、不要代码围栏。
2. 顶层必须同时包含以下 7 个键，缺一不可：completeness / plan / team_a / team_b / key_rounds / turning_points / verdict。
3. plan 是必填对象，至少要包含 team_a_order / team_a_order_reason / team_b_order / team_b_order_reason / skill_matchup / ability_impact 六个键。即使一方只有 1 只精灵，team_a_order / team_b_order 也至少要有 1 个元素；reason 至少要写 1 句话；skill_matchup / ability_impact 至少各 1 条，没有就写"无明显影响"。
4. JSON 结构必须严格如下，键名固定：
{
  "completeness": {
    "ok": true,
    "missing": ["A 队第 2 只精灵未指定技能", "B 队某技能 API 未返回数据"]
  },
  "plan": {
    "team_a_order": ["精灵1", "精灵2", "精灵3"],
    "team_a_order_reason": "...",
    "team_b_order": ["精灵1", "精灵2", "精灵3"],
    "team_b_order_reason": "...",
    "skill_matchup": [
      "A 冰钻 克 B 帕帕斯卡（草系被冰系双倍）",
      "B 帕帕斯卡 特性 抵消 A 状态消耗"
    ],
    "ability_impact": [
      "A 共鸣魔法 提速 抢先手",
      "B 主特性 反伤 削弱 A 物攻收割"
    ]
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
    {"round": 1, "desc": "A 首发冰钻布鲁斯先手丢冰块，B 帕帕斯卡承伤换上白金独角兽"},
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
6. key_rounds 列 3-5 步，每步 desc 控制在 40 字以内。
7. plan.team_a_order / team_b_order 使用精灵中文名数组；reason 一句话不超过 40 字。
8. plan.skill_matchup / ability_impact 各列 2-5 条核心应对关系，每条不超过 40 字。
9. 整体语言中文，不要堆术语，不要编造具体数值。"""


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


async def analyze_battle2(
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
    result = await stream_agent_collect(agent, user_msg, thread_id=thread_id or uuid4().hex, node_name="pk")
    return extract_json_object(result)


async def stream_analyze_battle(
        team_a: dict,
        team_b: dict,
        *,
        user_id: str,
        task_id: str,
        thread_id: str | None = None,
) -> tuple[dict, str]:
    """流式入口：传两套阵容 + user_id + task_id，过程中通过 ws 推送 token，
    最终返回 (parsed_dict, raw_text)。

    解析失败时返回 ({"error": "...", "raw": raw}, raw)，由调用方决定如何持久化。
    """
    if not isinstance(team_a, dict) or not isinstance(team_b, dict):
        raise TypeError("team_a / team_b 必须是 dict")

    payload = {"team_a": _slim(team_a), "team_b": _slim(team_b)}
    user_msg = (
            "请按系统提示分析以下两套阵容并输出严格 JSON：\n"
            + json.dumps(payload, ensure_ascii=False)
    )

    agent = _get_battle_pk_agent()
    raw = await stream_agent_collect(
        agent,
        user_msg,
        thread_id=thread_id or uuid4().hex,
        node_name="pk",
        user_id=user_id,
        task_id=task_id,
    )
    try:
        return extract_json_object(raw), raw
    except Exception as exc:
        return {"error": f"解析模型输出失败: {exc}", "raw": raw}, raw


# ---------------------------------------------------------------------------
# 3) CLI 自测：python -m agents.sub.pk_subagent path/to/pk_input.json
# ---------------------------------------------------------------------------

def _cli() -> None:
    import sys
    from pathlib import Path
    msg = """
{
    "team_a": {
        "title": "^虫^且^队",
        "lineup_desc": "BY^：^哔^哩^哔^哩^：^俱^心^哀^意",
        "source_type": "user_pk",
        "resonance_magic_id": 2,
        "resonance_magic_name": "^进^化^之^力",
        "members": [
            {
                "pokemon_id": 289,
                "pokemon_name": "^铠^甲^虫",
                "sort_order": 1,
                "bloodline_dict_id": 47,
                "bloodline_label": "^翼",
                "personality_id": 13,
                "personality_name_zh": "^害^羞",
                "qual_1": "hp",
                "qual_2": "phy_def",
                "qual_3": "mag_def",
                "skill_1_id": null,
                "skill_1_name": "^飞^断",
                "skill_2_id": null,
                "skill_2_name": "^虫^结^阵",
                "skill_3_id": null,
                "skill_3_name": "^吓^退",
                "skill_4_id": null,
                "skill_4_name": "^啃^咬",
                "member_desc": ""
            },
            {
                "pokemon_id": 303,
                "pokemon_name": "^食^尘^短^绒",
                "sort_order": 2,
                "bloodline_dict_id": 47,
                "bloodline_label": "^翼",
                "personality_id": 9,
                "personality_name_zh": "^平^和",
                "qual_1": "hp",
                "qual_2": "phy_def",
                "qual_3": "spd",
                "skill_1_id": null,
                "skill_1_name": "^地^刺",
                "skill_2_id": null,
                "skill_2_name": "^虫^结^阵",
                "skill_3_id": null,
                "skill_3_name": "^飞^断",
                "skill_4_id": null,
                "skill_4_name": "^虫^群^过^境",
                "member_desc": ""
            },
            {
                "pokemon_id": 324,
                "pokemon_name": "^陨^星^虫",
                "sort_order": 3,
                "bloodline_dict_id": 47,
                "bloodline_label": "^翼",
                "personality_id": 2,
                "personality_name_zh": "^开^朗",
                "qual_1": "hp",
                "qual_2": "phy_atk",
                "qual_3": "spd",
                "skill_1_id": null,
                "skill_1_name": "^虫^群",
                "skill_2_id": null,
                "skill_2_name": "^吓^退",
                "skill_3_id": null,
                "skill_3_name": "^羽^翼^庇^护",
                "skill_4_id": null,
                "skill_4_name": "^假^寐",
                "member_desc": ""
            },
            {
                "pokemon_id": 106,
                "pokemon_name": "^花^衣^蝶",
                "sort_order": 4,
                "bloodline_dict_id": 37,
                "bloodline_label": "^火",
                "personality_id": 9,
                "personality_name_zh": "^平^和",
                "qual_1": "hp",
                "qual_2": "phy_def",
                "qual_3": "mag_def",
                "skill_1_id": null,
                "skill_1_name": "^虫^群^智^慧",
                "skill_2_id": null,
                "skill_2_name": "^虫^结^阵",
                "skill_3_id": null,
                "skill_3_name": "^晒^太^阳",
                "skill_4_id": null,
                "skill_4_name": "^虫^群",
                "member_desc": ""
            },
            {
                "pokemon_id": 39,
                "pokemon_name": "^化^蝶^（^平^常^的^样^子^）",
                "sort_order": 5,
                "bloodline_dict_id": 44,
                "bloodline_label": "^毒",
                "personality_id": 29,
                "personality_name_zh": "^聪^明",
                "qual_1": "mag_atk",
                "qual_2": "mag_def",
                "qual_3": "spd",
                "skill_1_id": null,
                "skill_1_name": "^破^罐^破^摔",
                "skill_2_id": null,
                "skill_2_name": "^毒^孢^子",
                "skill_3_id": null,
                "skill_3_name": "^晒^太^阳",
                "skill_4_id": null,
                "skill_4_name": "^棘^刺",
                "member_desc": ""
            },
            {
                "pokemon_id": 89,
                "pokemon_name": "^花^魁^蜂^后",
                "sort_order": 6,
                "bloodline_dict_id": 53,
                "bloodline_label": "^首^领",
                "personality_id": 2,
                "personality_name_zh": "^开^朗",
                "qual_1": "hp",
                "qual_2": "phy_atk",
                "qual_3": "spd",
                "skill_1_id": null,
                "skill_1_name": "^热^身^运^动",
                "skill_2_id": null,
                "skill_2_name": "^虫^群",
                "skill_3_id": null,
                "skill_3_name": "^有^效^预^防",
                "skill_4_id": null,
                "skill_4_name": "^快^速^移^动",
                "member_desc": ""
            }
        ]
    },
    "team_b": {
        "title": "^火^神^圣^剑^队",
        "lineup_desc": "",
        "source_type": "user_pk",
        "resonance_magic_id": 2,
        "resonance_magic_name": "^进^化^之^力",
        "members": [
            {
                "pokemon_id": 7,
                "pokemon_name": "^火^神",
                "sort_order": 1,
                "bloodline_dict_id": 53,
                "bloodline_label": "^首^领",
                "personality_id": 2,
                "personality_name_zh": "^开^朗",
                "qual_1": "hp",
                "qual_2": "phy_atk",
                "qual_3": "spd",
                "skill_1_id": null,
                "skill_1_name": "^吹^火",
                "skill_2_id": null,
                "skill_2_name": "^暗^突^袭",
                "skill_3_id": null,
                "skill_3_name": "^火^云^车",
                "skill_4_id": null,
                "skill_4_name": "^山^火",
                "member_desc": ""
            },
            {
                "pokemon_id": 157,
                "pokemon_name": "^圣^羽^翼^王",
                "sort_order": 2,
                "bloodline_dict_id": 41,
                "bloodline_label": "^冰",
                "personality_id": 2,
                "personality_name_zh": "^开^朗",
                "qual_1": "spd",
                "qual_2": "phy_atk",
                "qual_3": "hp",
                "skill_1_id": null,
                "skill_1_name": "^水^刃",
                "skill_2_id": null,
                "skill_2_name": "^闪^击",
                "skill_3_id": null,
                "skill_3_name": "^力^量^增^效",
                "skill_4_id": null,
                "skill_4_name": "^光^之^矛",
                "member_desc": ""
            },
            {
                "pokemon_id": 295,
                "pokemon_name": "^寂^灭^骨^龙",
                "sort_order": 3,
                "bloodline_dict_id": 37,
                "bloodline_label": "^火",
                "personality_id": 1,
                "personality_name_zh": "^固^执",
                "qual_1": "hp",
                "qual_2": "phy_atk",
                "qual_3": "spd",
                "skill_1_id": null,
                "skill_1_name": "^电^弧",
                "skill_2_id": null,
                "skill_2_name": "^隼^鳞",
                "skill_3_id": null,
                "skill_3_name": "^吓^退",
                "skill_4_id": null,
                "skill_4_name": "^幻^象",
                "member_desc": ""
            },
            {
                "pokemon_id": 267,
                "pokemon_name": "^帕^帕^斯^卡",
                "sort_order": 4,
                "bloodline_dict_id": 43,
                "bloodline_label": "^电",
                "personality_id": 1,
                "personality_name_zh": "^固^执",
                "qual_1": "hp",
                "qual_2": "phy_atk",
                "qual_3": "spd",
                "skill_1_id": null,
                "skill_1_name": "^钢^铁^洪^流",
                "skill_2_id": null,
                "skill_2_name": "^轴^承^支^撑",
                "skill_3_id": null,
                "skill_3_name": "^超^级^糖^果",
                "skill_4_id": null,
                "skill_4_name": "^倾^泻",
                "member_desc": ""
            },
            {
                "pokemon_id": 362,
                "pokemon_name": "^岚^鸟^（^春^天^的^样^子^）",
                "sort_order": 5,
                "bloodline_dict_id": 41,
                "bloodline_label": "^冰",
                "personality_id": 2,
                "personality_name_zh": "^开^朗",
                "qual_1": "hp",
                "qual_2": "phy_def",
                "qual_3": "spd",
                "skill_1_id": null,
                "skill_1_name": "^龙^卷^风",
                "skill_2_id": null,
                "skill_2_name": "^水^刃",
                "skill_3_id": null,
                "skill_3_name": "^冰^爪",
                "skill_4_id": null,
                "skill_4_name": "^筛^管^奔^流",
                "member_desc": ""
            },
            {
                "pokemon_id": 291,
                "pokemon_name": "^圣^剑-X",
                "sort_order": 6,
                "bloodline_dict_id": 53,
                "bloodline_label": "^首^领",
                "personality_id": 1,
                "personality_name_zh": "^固^执",
                "qual_1": "hp",
                "qual_2": "phy_atk",
                "qual_3": "mag_def",
                "skill_1_id": null,
                "skill_1_name": "^轴^承^支^撑",
                "skill_2_id": null,
                "skill_2_name": "^齿^轮^扭^矩",
                "skill_3_id": null,
                "skill_3_name": "^齿^轮^切^开",
                "skill_4_id": null,
                "skill_4_name": "^啮^合^传^递",
                "member_desc": ""
            }
        ]
    }
}
"""
    data = json.loads(msg)
    output = analyze_battle(data["team_a"], data["team_b"])
    print(json.dumps(output, ensure_ascii=False, indent=2))


async def _cli2():
    import sys
    from pathlib import Path
    msg = """
    {
        "team_a": {
            "title": "^虫^且^队",
            "lineup_desc": "BY^：^哔^哩^哔^哩^：^俱^心^哀^意",
            "source_type": "user_pk",
            "resonance_magic_id": 2,
            "resonance_magic_name": "^进^化^之^力",
            "members": [
                {
                    "pokemon_id": 289,
                    "pokemon_name": "^铠^甲^虫",
                    "sort_order": 1,
                    "bloodline_dict_id": 47,
                    "bloodline_label": "^翼",
                    "personality_id": 13,
                    "personality_name_zh": "^害^羞",
                    "qual_1": "hp",
                    "qual_2": "phy_def",
                    "qual_3": "mag_def",
                    "skill_1_id": null,
                    "skill_1_name": "^飞^断",
                    "skill_2_id": null,
                    "skill_2_name": "^虫^结^阵",
                    "skill_3_id": null,
                    "skill_3_name": "^吓^退",
                    "skill_4_id": null,
                    "skill_4_name": "^啃^咬",
                    "member_desc": ""
                },
                {
                    "pokemon_id": 303,
                    "pokemon_name": "^食^尘^短^绒",
                    "sort_order": 2,
                    "bloodline_dict_id": 47,
                    "bloodline_label": "^翼",
                    "personality_id": 9,
                    "personality_name_zh": "^平^和",
                    "qual_1": "hp",
                    "qual_2": "phy_def",
                    "qual_3": "spd",
                    "skill_1_id": null,
                    "skill_1_name": "^地^刺",
                    "skill_2_id": null,
                    "skill_2_name": "^虫^结^阵",
                    "skill_3_id": null,
                    "skill_3_name": "^飞^断",
                    "skill_4_id": null,
                    "skill_4_name": "^虫^群^过^境",
                    "member_desc": ""
                },
                {
                    "pokemon_id": 324,
                    "pokemon_name": "^陨^星^虫",
                    "sort_order": 3,
                    "bloodline_dict_id": 47,
                    "bloodline_label": "^翼",
                    "personality_id": 2,
                    "personality_name_zh": "^开^朗",
                    "qual_1": "hp",
                    "qual_2": "phy_atk",
                    "qual_3": "spd",
                    "skill_1_id": null,
                    "skill_1_name": "^虫^群",
                    "skill_2_id": null,
                    "skill_2_name": "^吓^退",
                    "skill_3_id": null,
                    "skill_3_name": "^羽^翼^庇^护",
                    "skill_4_id": null,
                    "skill_4_name": "^假^寐",
                    "member_desc": ""
                },
                {
                    "pokemon_id": 106,
                    "pokemon_name": "^花^衣^蝶",
                    "sort_order": 4,
                    "bloodline_dict_id": 37,
                    "bloodline_label": "^火",
                    "personality_id": 9,
                    "personality_name_zh": "^平^和",
                    "qual_1": "hp",
                    "qual_2": "phy_def",
                    "qual_3": "mag_def",
                    "skill_1_id": null,
                    "skill_1_name": "^虫^群^智^慧",
                    "skill_2_id": null,
                    "skill_2_name": "^虫^结^阵",
                    "skill_3_id": null,
                    "skill_3_name": "^晒^太^阳",
                    "skill_4_id": null,
                    "skill_4_name": "^虫^群",
                    "member_desc": ""
                },
                {
                    "pokemon_id": 39,
                    "pokemon_name": "^化^蝶^（^平^常^的^样^子^）",
                    "sort_order": 5,
                    "bloodline_dict_id": 44,
                    "bloodline_label": "^毒",
                    "personality_id": 29,
                    "personality_name_zh": "^聪^明",
                    "qual_1": "mag_atk",
                    "qual_2": "mag_def",
                    "qual_3": "spd",
                    "skill_1_id": null,
                    "skill_1_name": "^破^罐^破^摔",
                    "skill_2_id": null,
                    "skill_2_name": "^毒^孢^子",
                    "skill_3_id": null,
                    "skill_3_name": "^晒^太^阳",
                    "skill_4_id": null,
                    "skill_4_name": "^棘^刺",
                    "member_desc": ""
                },
                {
                    "pokemon_id": 89,
                    "pokemon_name": "^花^魁^蜂^后",
                    "sort_order": 6,
                    "bloodline_dict_id": 53,
                    "bloodline_label": "^首^领",
                    "personality_id": 2,
                    "personality_name_zh": "^开^朗",
                    "qual_1": "hp",
                    "qual_2": "phy_atk",
                    "qual_3": "spd",
                    "skill_1_id": null,
                    "skill_1_name": "^热^身^运^动",
                    "skill_2_id": null,
                    "skill_2_name": "^虫^群",
                    "skill_3_id": null,
                    "skill_3_name": "^有^效^预^防",
                    "skill_4_id": null,
                    "skill_4_name": "^快^速^移^动",
                    "member_desc": ""
                }
            ]
        },
        "team_b": {
            "title": "^火^神^圣^剑^队",
            "lineup_desc": "",
            "source_type": "user_pk",
            "resonance_magic_id": 2,
            "resonance_magic_name": "^进^化^之^力",
            "members": [
                {
                    "pokemon_id": 7,
                    "pokemon_name": "^火^神",
                    "sort_order": 1,
                    "bloodline_dict_id": 53,
                    "bloodline_label": "^首^领",
                    "personality_id": 2,
                    "personality_name_zh": "^开^朗",
                    "qual_1": "hp",
                    "qual_2": "phy_atk",
                    "qual_3": "spd",
                    "skill_1_id": null,
                    "skill_1_name": "^吹^火",
                    "skill_2_id": null,
                    "skill_2_name": "^暗^突^袭",
                    "skill_3_id": null,
                    "skill_3_name": "^火^云^车",
                    "skill_4_id": null,
                    "skill_4_name": "^山^火",
                    "member_desc": ""
                },
                {
                    "pokemon_id": 157,
                    "pokemon_name": "^圣^羽^翼^王",
                    "sort_order": 2,
                    "bloodline_dict_id": 41,
                    "bloodline_label": "^冰",
                    "personality_id": 2,
                    "personality_name_zh": "^开^朗",
                    "qual_1": "spd",
                    "qual_2": "phy_atk",
                    "qual_3": "hp",
                    "skill_1_id": null,
                    "skill_1_name": "^水^刃",
                    "skill_2_id": null,
                    "skill_2_name": "^闪^击",
                    "skill_3_id": null,
                    "skill_3_name": "^力^量^增^效",
                    "skill_4_id": null,
                    "skill_4_name": "^光^之^矛",
                    "member_desc": ""
                },
                {
                    "pokemon_id": 295,
                    "pokemon_name": "^寂^灭^骨^龙",
                    "sort_order": 3,
                    "bloodline_dict_id": 37,
                    "bloodline_label": "^火",
                    "personality_id": 1,
                    "personality_name_zh": "^固^执",
                    "qual_1": "hp",
                    "qual_2": "phy_atk",
                    "qual_3": "spd",
                    "skill_1_id": null,
                    "skill_1_name": "^电^弧",
                    "skill_2_id": null,
                    "skill_2_name": "^隼^鳞",
                    "skill_3_id": null,
                    "skill_3_name": "^吓^退",
                    "skill_4_id": null,
                    "skill_4_name": "^幻^象",
                    "member_desc": ""
                },
                {
                    "pokemon_id": 267,
                    "pokemon_name": "^帕^帕^斯^卡",
                    "sort_order": 4,
                    "bloodline_dict_id": 43,
                    "bloodline_label": "^电",
                    "personality_id": 1,
                    "personality_name_zh": "^固^执",
                    "qual_1": "hp",
                    "qual_2": "phy_atk",
                    "qual_3": "spd",
                    "skill_1_id": null,
                    "skill_1_name": "^钢^铁^洪^流",
                    "skill_2_id": null,
                    "skill_2_name": "^轴^承^支^撑",
                    "skill_3_id": null,
                    "skill_3_name": "^超^级^糖^果",
                    "skill_4_id": null,
                    "skill_4_name": "^倾^泻",
                    "member_desc": ""
                },
                {
                    "pokemon_id": 362,
                    "pokemon_name": "^岚^鸟^（^春^天^的^样^子^）",
                    "sort_order": 5,
                    "bloodline_dict_id": 41,
                    "bloodline_label": "^冰",
                    "personality_id": 2,
                    "personality_name_zh": "^开^朗",
                    "qual_1": "hp",
                    "qual_2": "phy_def",
                    "qual_3": "spd",
                    "skill_1_id": null,
                    "skill_1_name": "^龙^卷^风",
                    "skill_2_id": null,
                    "skill_2_name": "^水^刃",
                    "skill_3_id": null,
                    "skill_3_name": "^冰^爪",
                    "skill_4_id": null,
                    "skill_4_name": "^筛^管^奔^流",
                    "member_desc": ""
                },
                {
                    "pokemon_id": 291,
                    "pokemon_name": "^圣^剑-X",
                    "sort_order": 6,
                    "bloodline_dict_id": 53,
                    "bloodline_label": "^首^领",
                    "personality_id": 1,
                    "personality_name_zh": "^固^执",
                    "qual_1": "hp",
                    "qual_2": "phy_atk",
                    "qual_3": "mag_def",
                    "skill_1_id": null,
                    "skill_1_name": "^轴^承^支^撑",
                    "skill_2_id": null,
                    "skill_2_name": "^齿^轮^扭^矩",
                    "skill_3_id": null,
                    "skill_3_name": "^齿^轮^切^开",
                    "skill_4_id": null,
                    "skill_4_name": "^啮^合^传^递",
                    "member_desc": ""
                }
            ]
        }
    }
    """
    data = json.loads(msg)
    output = await analyze_battle2(data["team_a"], data["team_b"])
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(_cli2())
