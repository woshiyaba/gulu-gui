<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  fetchBloodlines,
  fetchPersonalities,
  fetchPokemon,
  fetchResonanceMagics,
  fetchSkills,
  submitBattlePk,
} from '@/api/pokemon'
import type {
  BattlePkMember,
  BattlePkResponse,
  BattlePkTeam,
  BloodlineOption,
  PersonalityOption,
  Pokemon,
  ResonanceMagicOption,
  Skill,
} from '@/types'

type TeamKey = 'A' | 'B'

interface MemberForm {
  pokemon_id: number | null
  pokemon_name: string
  pokemon_image: string
  sort_order: number
  bloodline_dict_id: number | null
  bloodline_label: string
  personality_id: number | null
  personality_name_zh: string
  qual_1: string
  qual_2: string
  qual_3: string
  skills: Array<{ name: string; image: string }>
  member_desc: string
}

interface TeamForm {
  title: string
  lineup_desc: string
  resonance_magic_id: number | null
  resonance_magic_name: string
  members: MemberForm[]
}

const STAT_LABEL_MAP: Record<string, string> = {
  hp: 'HP',
  phy_atk: '物攻',
  mag_atk: '魔攻',
  phy_def: '物防',
  mag_def: '魔防',
  spd: '速度',
}

const STAT_OPTIONS = [
  { value: 'hp', label: 'HP' },
  { value: 'phy_atk', label: '物攻' },
  { value: 'mag_atk', label: '魔攻' },
  { value: 'phy_def', label: '物防' },
  { value: 'mag_def', label: '魔防' },
  { value: 'spd', label: '速度' },
] as const

function emptyMember(sort: number): MemberForm {
  return {
    pokemon_id: null,
    pokemon_name: '',
    pokemon_image: '',
    sort_order: sort,
    bloodline_dict_id: null,
    bloodline_label: '',
    personality_id: null,
    personality_name_zh: '',
    qual_1: '',
    qual_2: '',
    qual_3: '',
    skills: [
      { name: '', image: '' },
      { name: '', image: '' },
      { name: '', image: '' },
      { name: '', image: '' },
    ],
    member_desc: '',
  }
}

function emptyTeam(title: string): TeamForm {
  return {
    title,
    lineup_desc: '',
    resonance_magic_id: null,
    resonance_magic_name: '',
    members: [emptyMember(1)],
  }
}

const teamA = reactive<TeamForm>(emptyTeam('我的队伍'))
const teamB = reactive<TeamForm>(emptyTeam('对手队伍'))
const personalities = ref<PersonalityOption[]>([])
const bloodlines = ref<BloodlineOption[]>([])
const resonanceMagics = ref<ResonanceMagicOption[]>([])

// 性格描述：以"加 X / 降 Y"或修饰百分比形式拼描述，hover 时显示。
function personalityDesc(p: PersonalityOption): string {
  const pairs: Array<[string, number]> = [
    ['hp', p.hp_mod_pct],
    ['phy_atk', p.phy_atk_mod_pct],
    ['mag_atk', p.mag_atk_mod_pct],
    ['phy_def', p.phy_def_mod_pct],
    ['mag_def', p.mag_def_mod_pct],
    ['spd', p.spd_mod_pct],
  ]
  const buffs = pairs.filter(([, v]) => v > 0)
  const nerfs = pairs.filter(([, v]) => v < 0)
  if (!buffs.length && !nerfs.length) return '中性性格，不影响任何属性'
  // 后端 *_mod_pct 是小数（0.1 = 10%），这里转成百分比展示。
  const fmt = (k: string, v: number) => {
    const pct = Math.round(v * 100)
    return `${STAT_LABEL_MAP[k] || k} ${pct > 0 ? '+' : ''}${pct}%`
  }
  const buffStr = buffs.length ? `加：${buffs.map(([k, v]) => fmt(k, v)).join('、')}` : ''
  const nerfStr = nerfs.length ? `降：${nerfs.map(([k, v]) => fmt(k, v)).join('、')}` : ''
  return [buffStr, nerfStr].filter(Boolean).join(' / ')
}

const personalityById = computed(() => {
  const map = new Map<number, PersonalityOption>()
  for (const p of personalities.value) map.set(p.id, p)
  return map
})
const resonanceById = computed(() => {
  const map = new Map<number, ResonanceMagicOption>()
  for (const m of resonanceMagics.value) map.set(m.id, m)
  return map
})

const submitting = ref(false)
const error = ref('')
const result = ref<BattlePkResponse | null>(null)

// 搜索下拉状态：用 `${team}-${memberIndex}` / `${team}-${memberIndex}-${skillIndex}` 当 key
const pokemonKw = ref<Record<string, string>>({})
const pokemonHits = ref<Record<string, Pokemon[]>>({})
const pokemonOpen = ref<Record<string, boolean>>({})
const skillKw = ref<Record<string, string>>({})
const skillHits = ref<Record<string, Skill[]>>({})
const skillOpen = ref<Record<string, boolean>>({})

let pokemonTimer: ReturnType<typeof setTimeout> | undefined
let skillTimer: ReturnType<typeof setTimeout> | undefined

function teamRef(key: TeamKey): TeamForm {
  return key === 'A' ? teamA : teamB
}

function petKey(team: TeamKey, mi: number) {
  return `${team}-${mi}`
}
function skillCellKey(team: TeamKey, mi: number, si: number) {
  return `${team}-${mi}-${si}`
}

function addMember(team: TeamKey) {
  const t = teamRef(team)
  if (t.members.length >= 6) return
  t.members.push(emptyMember(t.members.length + 1))
}

function removeMember(team: TeamKey, index: number) {
  const t = teamRef(team)
  if (t.members.length <= 1) return
  t.members.splice(index, 1)
  t.members.forEach((m, i) => { m.sort_order = i + 1 })
}

function searchPokemon(team: TeamKey, mi: number) {
  if (pokemonTimer) clearTimeout(pokemonTimer)
  const k = petKey(team, mi)
  pokemonTimer = setTimeout(async () => {
    const kw = (pokemonKw.value[k] || '').trim()
    if (!kw) {
      pokemonHits.value[k] = []
      pokemonOpen.value[k] = false
      return
    }
    try {
      const res = await fetchPokemon({ name: kw, page: 1, page_size: 20 })
      pokemonHits.value[k] = res.items
      pokemonOpen.value[k] = true
    } catch { /* ignore */ }
  }, 280)
}

function pickPokemon(team: TeamKey, mi: number, item: Pokemon) {
  const m = teamRef(team).members[mi]
  if (!m) return
  // 后端 BattlePkMember.pokemon_id 是可空 int，这里图鉴号 no 做 fallback。
  const idNum = Number(item.no)
  m.pokemon_id = Number.isFinite(idNum) ? idNum : null
  m.pokemon_name = item.name
  m.pokemon_image = item.image_url
  const k = petKey(team, mi)
  pokemonKw.value[k] = ''
  pokemonOpen.value[k] = false
}

function clearPokemon(team: TeamKey, mi: number) {
  const m = teamRef(team).members[mi]
  if (!m) return
  m.pokemon_id = null
  m.pokemon_name = ''
  m.pokemon_image = ''
}

function searchSkill(team: TeamKey, mi: number, si: number) {
  if (skillTimer) clearTimeout(skillTimer)
  const k = skillCellKey(team, mi, si)
  skillTimer = setTimeout(async () => {
    const kw = (skillKw.value[k] || '').trim()
    if (!kw) {
      skillHits.value[k] = []
      skillOpen.value[k] = false
      return
    }
    try {
      const res = await fetchSkills({ name: kw })
      skillHits.value[k] = res.items
      skillOpen.value[k] = true
    } catch { /* ignore */ }
  }, 280)
}

function pickSkill(team: TeamKey, mi: number, si: number, item: Skill) {
  const m = teamRef(team).members[mi]
  if (!m) return
  m.skills[si] = { name: item.name, image: item.icon }
  const k = skillCellKey(team, mi, si)
  skillKw.value[k] = ''
  skillOpen.value[k] = false
}

function clearSkill(team: TeamKey, mi: number, si: number) {
  const m = teamRef(team).members[mi]
  if (!m) return
  m.skills[si] = { name: '', image: '' }
}

function hidePokemon(team: TeamKey, mi: number) {
  setTimeout(() => { pokemonOpen.value[petKey(team, mi)] = false }, 180)
}
function hideSkill(team: TeamKey, mi: number, si: number) {
  setTimeout(() => { skillOpen.value[skillCellKey(team, mi, si)] = false }, 180)
}

function onPersonalityChange(team: TeamKey, mi: number, pid: number | null) {
  const m = teamRef(team).members[mi]
  if (!m) return
  m.personality_id = pid
  m.personality_name_zh = pid !== null ? personalityById.value.get(pid)?.name || '' : ''
}

function onBloodlineChange(team: TeamKey, mi: number, dictId: number | null) {
  const m = teamRef(team).members[mi]
  if (!m) return
  m.bloodline_dict_id = dictId
  m.bloodline_label = dictId !== null ? bloodlines.value.find((b) => b.id === dictId)?.label || '' : ''
}

function onResonanceChange(team: TeamKey, magicId: number | null) {
  const t = teamRef(team)
  t.resonance_magic_id = magicId
  t.resonance_magic_name = magicId !== null ? resonanceById.value.get(magicId)?.name || '' : ''
}

function toPayload(team: TeamForm): BattlePkTeam {
  const members: BattlePkMember[] = team.members
    .filter((m) => m.pokemon_name.trim())
    .map((m, i) => ({
      pokemon_id: m.pokemon_id,
      pokemon_name: m.pokemon_name,
      sort_order: i + 1,
      bloodline_dict_id: m.bloodline_dict_id,
      bloodline_label: m.bloodline_label.trim(),
      personality_id: m.personality_id,
      personality_name_zh: m.personality_name_zh,
      qual_1: m.qual_1,
      qual_2: m.qual_2,
      qual_3: m.qual_3,
      skill_1_id: null,
      skill_1_name: m.skills[0]?.name || '',
      skill_2_id: null,
      skill_2_name: m.skills[1]?.name || '',
      skill_3_id: null,
      skill_3_name: m.skills[2]?.name || '',
      skill_4_id: null,
      skill_4_name: m.skills[3]?.name || '',
      member_desc: m.member_desc,
    }))
  return {
    title: team.title.trim() || '未命名队伍',
    lineup_desc: team.lineup_desc.trim(),
    source_type: 'user_pk',
    resonance_magic_id: team.resonance_magic_id,
    resonance_magic_name: team.resonance_magic_name,
    members,
  }
}

function validate(): string {
  const a = toPayload(teamA)
  const b = toPayload(teamB)
  if (!a.members.length) return '请至少为「我方队伍」配置 1 只精灵'
  if (!b.members.length) return '请至少为「对手队伍」配置 1 只精灵'
  for (const team of [
    { name: '我方', payload: a },
    { name: '对手', payload: b },
  ]) {
    for (const [i, m] of team.payload.members.entries()) {
      const stats = [m.qual_1, m.qual_2, m.qual_3].filter(Boolean)
      if (stats.length && new Set(stats).size !== stats.length) {
        return `${team.name}第 ${i + 1} 只精灵的资质属性不能重复`
      }
      const skillNames = [m.skill_1_name, m.skill_2_name, m.skill_3_name, m.skill_4_name].filter(Boolean)
      if (new Set(skillNames).size !== skillNames.length) {
        return `${team.name}第 ${i + 1} 只精灵的技能不能重复`
      }
    }
  }
  return ''
}

async function runBattle() {
  if (submitting.value) return
  const message = validate()
  if (message) {
    error.value = message
    return
  }
  submitting.value = true
  error.value = ''
  result.value = null
  try {
    const data = await submitBattlePk({
      team_a: toPayload(teamA),
      team_b: toPayload(teamB),
    })
    result.value = data
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || '分析失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

function resetAll() {
  Object.assign(teamA, emptyTeam('我的队伍'))
  Object.assign(teamB, emptyTeam('对手队伍'))
  pokemonKw.value = {}
  pokemonHits.value = {}
  pokemonOpen.value = {}
  skillKw.value = {}
  skillHits.value = {}
  skillOpen.value = {}
  result.value = null
  error.value = ''
}

function winnerLabel(w: string): string {
  if (w === 'A') return '我方更优'
  if (w === 'B') return '对手更优'
  return '势均力敌'
}

onMounted(async () => {
  const [p, b, r] = await Promise.allSettled([
    fetchPersonalities(),
    fetchBloodlines(),
    fetchResonanceMagics(),
  ])
  if (p.status === 'fulfilled') personalities.value = p.value
  if (b.status === 'fulfilled') bloodlines.value = b.value
  if (r.status === 'fulfilled') resonanceMagics.value = r.value
})
</script>

<template>
  <div class="pk-page">
    <header class="pk-header">
      <RouterLink class="back-link" to="/">← 返回首页</RouterLink>
      <h1 class="pk-title">阵容 PK · 经典回合制对战模拟</h1>
      <p class="pk-tip">配置两套队伍（每方最多 6 只），将基于属性克制、速度线、物魔分流和换宠节奏给出胜率与回合推演。</p>
    </header>

    <main class="pk-main">
      <div class="teams">
        <section v-for="team in (['A', 'B'] as TeamKey[])" :key="team" class="team-card" :class="{ 'team-b': team === 'B' }">
          <div class="team-head">
            <span class="team-tag">{{ team === 'A' ? '我方' : '对手' }}</span>
            <input v-model="teamRef(team).title" class="team-title-input" placeholder="队伍名称" maxlength="20" />
            <button v-if="teamRef(team).members.length < 6" type="button" class="btn-small" @click="addMember(team)">+ 添加精灵</button>
          </div>

          <div class="team-resonance">
            <span class="resonance-label">共鸣魔法</span>
            <select
              :value="teamRef(team).resonance_magic_id ?? ''"
              @change="onResonanceChange(team, ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null)"
            >
              <option value="">未设置</option>
              <option v-for="m in resonanceMagics" :key="m.id" :value="m.id" :title="m.description">
                {{ m.name }}
              </option>
            </select>
            <div v-if="teamRef(team).resonance_magic_id !== null" class="resonance-preview">
              <img
                v-if="resonanceById.get(teamRef(team).resonance_magic_id!)?.icon_url"
                :src="resonanceById.get(teamRef(team).resonance_magic_id!)?.icon_url"
                alt=""
                class="resonance-icon"
              />
              <span class="resonance-desc" :title="resonanceById.get(teamRef(team).resonance_magic_id!)?.description || ''">
                {{ resonanceById.get(teamRef(team).resonance_magic_id!)?.description || '' }}
              </span>
            </div>
          </div>

          <div v-for="(member, mi) in teamRef(team).members" :key="mi" class="pet-card">
            <div class="pet-header">
              <div class="pet-avatar">
                <img v-if="member.pokemon_image" :src="member.pokemon_image" alt="" />
                <span v-else>#{{ mi + 1 }}</span>
              </div>
              <div class="pet-title">
                <strong>{{ member.pokemon_name || `精灵 ${mi + 1}` }}</strong>
                <small>第 {{ mi + 1 }} 只 · 上场顺序 {{ mi + 1 }}</small>
              </div>
              <button v-if="teamRef(team).members.length > 1" type="button" class="text-btn danger" @click="removeMember(team, mi)">移除</button>
            </div>

            <div class="form-grid">
              <div class="form-row search-field">
                <span>精灵</span>
                <div v-if="member.pokemon_name" class="selected-item">
                  <img v-if="member.pokemon_image" :src="member.pokemon_image" class="selected-img" alt="" />
                  <span>{{ member.pokemon_name }}</span>
                  <button type="button" class="clear-btn" @click="clearPokemon(team, mi)">&times;</button>
                </div>
                <div v-else class="search-input-wrap">
                  <input
                    v-model="pokemonKw[petKey(team, mi)]"
                    type="text"
                    placeholder="输入精灵名称搜索..."
                    @input="searchPokemon(team, mi)"
                    @focus="searchPokemon(team, mi)"
                    @blur="hidePokemon(team, mi)"
                  />
                  <div v-if="pokemonOpen[petKey(team, mi)] && pokemonHits[petKey(team, mi)]?.length" class="dropdown">
                    <div
                      v-for="opt in pokemonHits[petKey(team, mi)]"
                      :key="opt.no"
                      class="dropdown-item"
                      @mousedown.prevent="pickPokemon(team, mi, opt)"
                    >
                      <img v-if="opt.image_url" :src="opt.image_url" class="dropdown-img" alt="" />
                      <span>{{ opt.name }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="form-row personality-row">
                <span>性格</span>
                <div class="personality-wrap">
                  <select
                    :value="member.personality_id ?? ''"
                    :title="member.personality_id !== null && personalityById.get(member.personality_id) ? personalityDesc(personalityById.get(member.personality_id)!) : '将鼠标悬停可查看加/降属性'"
                    @change="onPersonalityChange(team, mi, ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null)"
                  >
                    <option value="">未设置</option>
                    <option v-for="p in personalities" :key="p.id" :value="p.id" :title="personalityDesc(p)">
                      {{ p.name }}
                    </option>
                  </select>
                  <span
                    v-if="member.personality_id !== null && personalityById.get(member.personality_id)"
                    class="personality-hint"
                    :title="personalityDesc(personalityById.get(member.personality_id!)!)"
                  >
                    ⓘ {{ personalityDesc(personalityById.get(member.personality_id!)!) }}
                  </span>
                </div>
              </div>

              <label class="form-row">
                <span>血脉</span>
                <select
                  :value="member.bloodline_dict_id ?? ''"
                  @change="onBloodlineChange(team, mi, ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null)"
                >
                  <option value="">未设置</option>
                  <option v-for="b in bloodlines" :key="b.id" :value="b.id">{{ b.label }}</option>
                </select>
              </label>
            </div>

            <div class="section-subtitle">三项资质（不能重复）</div>
            <div class="quality-grid">
              <select v-model="member.qual_1">
                <option value="">未设置</option>
                <option v-for="opt in STAT_OPTIONS" :key="`q1-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
              </select>
              <select v-model="member.qual_2">
                <option value="">未设置</option>
                <option v-for="opt in STAT_OPTIONS" :key="`q2-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
              </select>
              <select v-model="member.qual_3">
                <option value="">未设置</option>
                <option v-for="opt in STAT_OPTIONS" :key="`q3-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>

            <div class="section-subtitle">技能配置（最多 4 个）</div>
            <div class="pet-skills">
              <div v-for="si in 4" :key="si" class="form-row search-field skill-field">
                <span>技能{{ si }}</span>
                <div v-if="member.skills[si - 1]?.name" class="selected-item">
                  <img v-if="member.skills[si - 1]?.image" :src="member.skills[si - 1]?.image" class="selected-img" alt="" />
                  <span>{{ member.skills[si - 1]!.name }}</span>
                  <button type="button" class="clear-btn" @click="clearSkill(team, mi, si - 1)">&times;</button>
                </div>
                <div v-else class="search-input-wrap">
                  <input
                    v-model="skillKw[skillCellKey(team, mi, si - 1)]"
                    type="text"
                    placeholder="搜索技能名..."
                    @input="searchSkill(team, mi, si - 1)"
                    @focus="searchSkill(team, mi, si - 1)"
                    @blur="hideSkill(team, mi, si - 1)"
                  />
                  <div v-if="skillOpen[skillCellKey(team, mi, si - 1)] && skillHits[skillCellKey(team, mi, si - 1)]?.length" class="dropdown">
                    <div
                      v-for="opt in skillHits[skillCellKey(team, mi, si - 1)]"
                      :key="opt.name"
                      class="dropdown-item"
                      @mousedown.prevent="pickSkill(team, mi, si - 1, opt)"
                    >
                      <img v-if="opt.icon" :src="opt.icon" class="dropdown-img" alt="" />
                      <span>{{ opt.name }}</span>
                      <em v-if="opt.attr">· {{ opt.attr }}</em>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="section-subtitle">该精灵备注（可选）</div>
            <textarea v-model="member.member_desc" rows="2" class="desc-textarea" placeholder="例如：核心输出 / 工具人 / 联防替补..."></textarea>
          </div>

          <div class="section-subtitle team-desc-title">队伍说明（可选）</div>
          <textarea v-model="teamRef(team).lineup_desc" rows="2" class="desc-textarea" placeholder="整体打法描述，如高速压制 / 消耗联防..."></textarea>
        </section>
      </div>

      <div class="action-bar">
        <button type="button" class="btn-primary" :disabled="submitting" @click="runBattle">
          {{ submitting ? '正在模拟对战...' : '开始 PK' }}
        </button>
        <button type="button" class="btn-default" :disabled="submitting" @click="resetAll">重置全部</button>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <section v-if="result" class="result-card">
        <div v-if="result.error" class="error">
          AI 输出解析失败：{{ result.error }}
          <pre v-if="result.raw" class="raw-pre">{{ result.raw }}</pre>
        </div>

        <template v-else>
          <div v-if="result.completeness && !result.completeness.ok && result.completeness.missing?.length" class="warn">
            数据不完整：{{ result.completeness.missing.join('；') }}
          </div>

          <div class="verdict">
            <div class="verdict-headline">
              <span class="verdict-tag" :class="`tag-${result.verdict.winner.toLowerCase()}`">
                {{ winnerLabel(result.verdict.winner) }}
              </span>
              <strong>我方胜率 {{ result.verdict.win_rate_a }}%</strong>
              <span class="verdict-vs">VS</span>
              <strong>对手胜率 {{ 100 - result.verdict.win_rate_a }}%</strong>
            </div>
            <p class="verdict-reason">{{ result.verdict.reason }}</p>
            <div class="bar">
              <div class="bar-a" :style="{ width: `${result.verdict.win_rate_a}%` }"></div>
              <div class="bar-b" :style="{ width: `${100 - result.verdict.win_rate_a}%` }"></div>
            </div>
          </div>

          <div v-if="result.plan" class="plan-card">
            <h3 class="plan-title">AI 推荐的最优出战计划</h3>
            <div class="plan-orders">
              <div class="plan-order plan-a">
                <div class="plan-order-head">
                  <span class="plan-tag tag-a">我方 最优顺序</span>
                </div>
                <div class="plan-chain">
                  <template v-for="(name, i) in result.plan.team_a_order" :key="`oa-${i}`">
                    <span class="chain-node">{{ name }}</span>
                    <span v-if="i < result.plan.team_a_order.length - 1" class="chain-arrow">→</span>
                  </template>
                </div>
                <p v-if="result.plan.team_a_order_reason" class="plan-reason">
                  {{ result.plan.team_a_order_reason }}
                </p>
              </div>
              <div class="plan-order plan-b">
                <div class="plan-order-head">
                  <span class="plan-tag tag-b">对手 最优顺序</span>
                </div>
                <div class="plan-chain">
                  <template v-for="(name, i) in result.plan.team_b_order" :key="`ob-${i}`">
                    <span class="chain-node">{{ name }}</span>
                    <span v-if="i < result.plan.team_b_order.length - 1" class="chain-arrow">→</span>
                  </template>
                </div>
                <p v-if="result.plan.team_b_order_reason" class="plan-reason">
                  {{ result.plan.team_b_order_reason }}
                </p>
              </div>
            </div>

            <div class="plan-grid">
              <div v-if="result.plan.skill_matchup?.length" class="plan-section">
                <h4>技能应对关系</h4>
                <ul>
                  <li v-for="(s, i) in result.plan.skill_matchup" :key="`sm-${i}`">{{ s }}</li>
                </ul>
              </div>
              <div v-if="result.plan.ability_impact?.length" class="plan-section">
                <h4>特性 / 共鸣魔法 影响</h4>
                <ul>
                  <li v-for="(s, i) in result.plan.ability_impact" :key="`ai-${i}`">{{ s }}</li>
                </ul>
              </div>
            </div>
          </div>

          <div class="sides">
            <div class="side-block">
              <h3>我方 · {{ result.team_a.summary }}</h3>
              <h4>优势</h4>
              <ul>
                <li v-for="(s, i) in result.team_a.advantages" :key="`aa-${i}`">{{ s }}</li>
              </ul>
              <h4>风险</h4>
              <ul class="muted-list">
                <li v-for="(s, i) in result.team_a.weaknesses" :key="`aw-${i}`">{{ s }}</li>
              </ul>
            </div>
            <div class="side-block">
              <h3>对手 · {{ result.team_b.summary }}</h3>
              <h4>优势</h4>
              <ul>
                <li v-for="(s, i) in result.team_b.advantages" :key="`ba-${i}`">{{ s }}</li>
              </ul>
              <h4>风险</h4>
              <ul class="muted-list">
                <li v-for="(s, i) in result.team_b.weaknesses" :key="`bw-${i}`">{{ s }}</li>
              </ul>
            </div>
          </div>

          <div class="rounds">
            <h3>关键回合推演</h3>
            <ol>
              <li v-for="r in result.key_rounds" :key="r.round">
                <span class="round-tag">R{{ r.round }}</span>
                <span>{{ r.desc }}</span>
              </li>
            </ol>
          </div>

          <div v-if="result.turning_points?.length" class="turn">
            <h3>翻盘点</h3>
            <ul>
              <li v-for="(t, i) in result.turning_points" :key="`tp-${i}`">{{ t }}</li>
            </ul>
          </div>
        </template>
      </section>
    </main>
  </div>
</template>

<style scoped>
.pk-page {
  min-height: 100vh;
  background: var(--color-bg);
  color: var(--color-text);
  padding-bottom: 48px;
}

.pk-header {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  padding: 20px 24px 16px;
  position: sticky;
  top: 0;
  z-index: 5;
}
.back-link { color: var(--color-accent); text-decoration: none; font-size: 13px; }
.back-link:hover { text-decoration: underline; }
.pk-title { margin: 8px 0 4px; font-size: 22px; color: var(--color-accent); }
.pk-tip { margin: 0; color: var(--color-muted); font-size: 13px; }

.pk-main { max-width: 1280px; margin: 0 auto; padding: 16px 24px 0; }

.teams { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.team-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-top: 3px solid #409eff;
  border-radius: 4px;
  padding: 16px;
}
.team-card.team-b { border-top-color: #f56c6c; }

.team-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.team-tag {
  padding: 4px 10px; border-radius: 12px;
  background: #ecf5ff; color: #409eff; font-size: 12px; font-weight: 600;
}
.team-b .team-tag { background: #fef0f0; color: #f56c6c; }

.team-title-input {
  flex: 1; height: 32px; border: 1px solid var(--color-border);
  border-radius: 4px; padding: 0 10px; font-size: 14px;
  background: var(--color-bg); color: var(--color-text);
}
.team-title-input:focus { outline: none; border-color: var(--color-accent); }

.btn-small {
  height: 28px; padding: 0 10px; border: 1px solid #409eff; border-radius: 2px;
  background: #ecf5ff; color: #409eff; cursor: pointer; font-size: 12px;
}
.btn-small:hover { background: #409eff; color: #fff; }

.team-resonance {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  background: var(--color-bg);
  border: 1px dashed var(--color-border);
  border-radius: 4px;
  padding: 8px 10px;
  margin-bottom: 10px;
}
.resonance-label { font-size: 12px; color: var(--color-muted); white-space: nowrap; }
.team-resonance select { flex: 0 0 180px; }
.resonance-preview { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
.resonance-icon { width: 24px; height: 24px; object-fit: contain; }
.resonance-desc {
  font-size: 12px; color: var(--color-muted);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  max-width: 100%;
}

.personality-row { align-items: start; }
.personality-wrap { display: grid; gap: 4px; min-width: 0; }
.personality-hint {
  font-size: 11px; color: var(--color-muted);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  cursor: help;
}

.pet-card {
  border: 1px solid var(--color-border); border-radius: 4px;
  padding: 12px 14px; margin-bottom: 10px; background: var(--color-bg);
}
.pet-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.pet-avatar {
  width: 40px; height: 40px; border-radius: 4px;
  background: var(--color-surface); border: 1px solid var(--color-border);
  display: grid; place-items: center; overflow: hidden; font-size: 12px; color: var(--color-muted);
}
.pet-avatar img { width: 100%; height: 100%; object-fit: contain; }
.pet-title { flex: 1; display: grid; gap: 2px; }
.pet-title strong { font-size: 14px; }
.pet-title small { font-size: 12px; color: var(--color-muted); }

.form-grid {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px; margin-top: 4px;
}
.form-row {
  display: grid; grid-template-columns: max-content minmax(0, 1fr);
  align-items: center; gap: 6px;
}
.form-row > span { color: var(--color-muted); font-size: 13px; }

.section-subtitle { margin: 12px 0 6px; font-size: 12px; font-weight: 600; color: var(--color-muted); }
.team-desc-title { margin-top: 6px; }

.quality-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.pet-skills { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }

.search-field { position: relative; }
.skill-field { margin-bottom: 0; }
.search-input-wrap { position: relative; }
.search-input-wrap input { width: 100%; height: 32px; }

input, select, textarea {
  border: 1px solid var(--color-border); border-radius: 4px;
  padding: 0 12px; font-size: 13px;
  background: var(--color-bg); color: var(--color-text);
}
input, select { height: 32px; }
textarea { padding: 8px 12px; }
input:focus, select:focus, textarea:focus {
  outline: none; border-color: var(--color-accent);
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.15);
}

.dropdown {
  position: absolute; top: 100%; left: 0; right: 0;
  background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: 4px; max-height: 240px; overflow: auto; z-index: 20;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
}
.dropdown-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; font-size: 13px; cursor: pointer;
}
.dropdown-item:hover { background: var(--color-hover); }
.dropdown-item em { color: var(--color-muted); font-style: normal; font-size: 12px; }
.dropdown-img { width: 24px; height: 24px; object-fit: contain; }

.selected-item {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 8px; background: rgba(64, 158, 255, 0.12);
  border: 1px solid rgba(64, 158, 255, 0.4); border-radius: 4px;
  font-size: 13px; color: var(--color-accent);
}
.selected-img { width: 22px; height: 22px; object-fit: contain; }
.clear-btn { border: none; background: transparent; color: var(--color-muted); cursor: pointer; font-size: 14px; }
.clear-btn:hover { color: #f56c6c; }

.text-btn { padding: 0; border: none; background: transparent; color: var(--color-accent); cursor: pointer; font-size: 13px; }
.text-btn.danger { color: #f56c6c; }

.desc-textarea { width: 100%; resize: vertical; }

.action-bar {
  display: flex; justify-content: center; gap: 12px;
  padding: 20px 0;
}

.btn-primary, .btn-default {
  height: 40px; padding: 0 28px; border-radius: 4px;
  font-size: 14px; cursor: pointer; transition: all 0.15s ease;
}
.btn-primary {
  border: 1px solid var(--color-accent); background: var(--color-accent); color: #fff;
}
.btn-primary:hover:not(:disabled) { opacity: 0.9; }
.btn-primary:disabled { cursor: not-allowed; opacity: 0.6; }
.btn-default { border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text); }
.btn-default:hover:not(:disabled) { border-color: var(--color-accent); color: var(--color-accent); }

.error {
  background: #fef0f0; color: #c45656;
  border: 1px solid #fde2e2; padding: 10px 14px;
  border-radius: 4px; margin: 8px 0;
}
.warn {
  background: #fdf6ec; color: #b88230;
  border: 1px solid #faecd8; padding: 10px 14px;
  border-radius: 4px; margin-bottom: 12px; font-size: 13px;
}
.raw-pre {
  margin-top: 8px; padding: 8px; background: #fff;
  border-radius: 4px; font-size: 12px; max-height: 200px; overflow: auto;
}

.result-card {
  background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: 6px; padding: 20px; margin-top: 8px;
}

.verdict { padding-bottom: 16px; border-bottom: 1px solid var(--color-border); margin-bottom: 16px; }
.verdict-headline { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; font-size: 16px; }
.verdict-vs { color: var(--color-muted); font-size: 13px; }
.verdict-tag {
  padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 13px;
}
.tag-a { background: #ecf5ff; color: #409eff; }
.tag-b { background: #fef0f0; color: #f56c6c; }
.tag-draw { background: #f4f4f5; color: #909399; }
.verdict-reason { color: var(--color-muted); margin: 8px 0 12px; font-size: 13px; }

.bar {
  height: 12px; border-radius: 6px; overflow: hidden;
  background: #f0f0f0; display: flex;
}
.bar-a { background: linear-gradient(90deg, #409eff, #66b1ff); }
.bar-b { background: linear-gradient(90deg, #f78989, #f56c6c); }

.plan-card {
  margin-bottom: 16px; padding: 14px 16px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.06), rgba(245, 108, 108, 0.06));
  border: 1px solid var(--color-border); border-radius: 6px;
}
.plan-title { margin: 0 0 12px; font-size: 15px; }
.plan-orders { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
.plan-order {
  padding: 10px 12px; border-radius: 4px;
  background: var(--color-surface); border: 1px solid var(--color-border);
}
.plan-order-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.plan-tag { padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 600; }
.plan-chain { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 13px; }
.chain-node {
  padding: 3px 10px; border-radius: 12px;
  background: var(--color-bg); border: 1px solid var(--color-border);
  font-weight: 600;
}
.plan-a .chain-node { color: #409eff; border-color: rgba(64, 158, 255, 0.4); }
.plan-b .chain-node { color: #f56c6c; border-color: rgba(245, 108, 108, 0.4); }
.chain-arrow { color: var(--color-muted); font-size: 13px; }
.plan-reason { margin: 8px 0 0; font-size: 12px; color: var(--color-muted); line-height: 1.6; }

.plan-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.plan-section h4 { margin: 0 0 6px; font-size: 13px; color: var(--color-muted); }
.plan-section ul { margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.7; }

.sides { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.side-block h3 { margin: 0 0 8px; font-size: 15px; }
.side-block h4 { margin: 10px 0 6px; font-size: 13px; color: var(--color-muted); }
.side-block ul { margin: 0; padding-left: 20px; font-size: 13px; line-height: 1.7; }
.side-block ul.muted-list { color: var(--color-muted); }

.rounds h3, .turn h3 { font-size: 15px; margin: 0 0 8px; }
.rounds ol { margin: 0; padding-left: 0; list-style: none; }
.rounds ol li {
  display: flex; gap: 10px; padding: 8px 10px;
  border: 1px solid var(--color-border); border-radius: 4px;
  margin-bottom: 6px; background: var(--color-bg); font-size: 13px;
}
.round-tag {
  flex: 0 0 auto; padding: 1px 8px; height: 22px; line-height: 20px;
  background: var(--color-accent); color: #fff;
  border-radius: 10px; font-size: 12px; font-weight: 600;
}
.turn { margin-top: 16px; }
.turn ul { padding-left: 20px; font-size: 13px; line-height: 1.7; margin: 0; }

@media (max-width: 960px) {
  .teams { grid-template-columns: 1fr; }
  .form-grid { grid-template-columns: 1fr 1fr; }
  .sides, .plan-orders, .plan-grid { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .form-grid, .quality-grid, .pet-skills { grid-template-columns: 1fr; }
  .form-row { grid-template-columns: 1fr; gap: 4px; }
}
</style>
