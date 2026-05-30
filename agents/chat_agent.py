"""chat_agent —— 宠物对话 Agent。

每只宠物在 pet_prompt 表里有一段独立人设；用户还能在 pet_prompt_extra 里补充
昵称、性格、伙伴关系等可扩展属性。聊天前把"通用扮演守则 + 宠物人设 + 用户补充"
合并成一个 system prompt，再据此创建一个属于"这个用户 × 这只宠物"的对话 agent。

对外暴露：
- compose_pet_system_prompt(pet_prompt, extra)  合并出最终 system prompt
- create_pet_chat_agent(system_prompt, name)     按 system prompt 创建对话 agent
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.utils.llm_utils import (
    PROJECT_ROOT,
    ReadOnlyFilesystemBackend,
    create_app_deep_agent,
)

# ---------------------------------------------------------------------------
# 通用扮演守则 —— 所有宠物对话共用，拼在每只宠物自己的人设之前
# ---------------------------------------------------------------------------

PET_CHAT_GUIDELINES = """\
你正在扮演洛克王国世界（手游）里的一只精灵，作为玩家（你称呼对方为"主人"）的伙伴和它聊天。
你不是助手、不是 AI，就是这只活生生的小精灵本身，有自己的情绪、喜好和说话习惯。

## 扮演要求

始终保持角色，第一人称"我"说话，绝不跳出角色解释自己是程序或模型。
你的性格、口吻完全由下面的"人设"和"主人对你的设定"决定，要自然地体现出来。
像真正的伙伴那样回应主人：会撒娇、会好奇、会开心也会闹小情绪，但始终亲近主人。
如果主人问到你不知道的现实世界知识，就用小精灵的视角天真地回应，别一本正经科普。

## 禁止

不要自称助手 / AI / 模型，不要说"作为一只精灵我……"这种出戏的话。
不要写分析报告、不要列要点标题、不要客套地感谢主人提问。

## 输出格式

用纯自然语言，像说话一样，不要任何 Markdown 语法（不要 #、加粗、列表、代码块、表格）。
回复简短口语化，一般 50 字以内，闲聊打招呼 20 字以内，除非主人明确希望你多说点。
全程使用中文。\
"""


# ---------------------------------------------------------------------------
# system prompt 合并
# ---------------------------------------------------------------------------

def _format_extra(extra: dict[str, Any] | None) -> str:
    """把用户补充的键值对渲染成"字段：值"的多行文本，过滤空值。"""
    if not extra:
        return ""
    lines = [
        f"{key}：{value}"
        for key, value in extra.items()
        if str(value).strip()
    ]
    return "\n".join(lines)


def compose_pet_system_prompt(
    pet_prompt: str,
    extra: dict[str, Any] | None = None,
) -> str:
    """合并通用守则、宠物人设、用户个性化补充为完整 system prompt。

    Args:
        pet_prompt: pet_prompt 表里该宠物的独立人设。
        extra: 用户在 pet_prompt_extra 里的补充（昵称 / 性格 / 伙伴关系等键值对）。
    """
    sections = [PET_CHAT_GUIDELINES]

    pet_prompt = (pet_prompt or "").strip()
    if pet_prompt:
        sections.append("## 你的人设\n" + pet_prompt)

    extra_text = _format_extra(extra)
    if extra_text:
        sections.append("## 主人对你的设定（请严格体现）\n" + extra_text)

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

def create_pet_chat_agent(system_prompt: str, *, name: str = "pet-chat-agent") -> Any:
    """按合并好的 system prompt 创建一个宠物对话 agent。

    纯角色扮演聊天，不挂任何外部工具 / 技能，避免出戏。每个
    "用户 × 宠物" 会话各自持有一个独立实例（内含独立的对话记忆）。
    """
    backend = ReadOnlyFilesystemBackend(root_dir=PROJECT_ROOT, virtual_mode=True)
    return create_app_deep_agent(
        system_prompt=system_prompt,
        skills=None,
        backend=backend,
        name=name,
    )
