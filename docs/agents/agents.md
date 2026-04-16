# main_agents设计
main_agents主要负责分析用户的请求和规划

比如
你是一个任务规划器。

可用技能：
{skills}


请输出 JSON 格式的执行计划：
[
  {{"step":1, "skill":"xxx", "input":{{}}}},
  ...
]

可用技能则使用llm_utils 的load skills方法写入 然后使用 这样的格式添加到system pormpt中
<available_skills>
<skill>
name: demo-skill1
description: 用于提示转储的演示技能1
</skill>
<skill>
name: demo-skill2
description: 用于提示转储的演示技能2
</skill>
</available_skills>

然后要求llm输出一个json列表 列表中需要包含需要完成的任务，需要调用的技能等等 执行任务所必须要的参数
