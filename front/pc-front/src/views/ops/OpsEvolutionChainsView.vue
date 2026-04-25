<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import {
  deleteOpsEvolutionGraphByChainId,
  fetchOpsEvolutionGraphByPokemonId,
  fetchOpsPokemon,
  showOpsToast,
  updateOpsEvolutionGraphByPokemonId,
  type OpsEvolutionGraph,
  type OpsEvolutionGraphEdge,
  type OpsPokemonItem,
} from '@/api/ops'

type Position = { x: number; y: number }

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const searchKeyword = ref('')
const pokemonOptions = ref<OpsPokemonItem[]>([])
const selectedPokemonId = ref<number | null>(null)
const selectedPokemonName = ref('')
const chainId = ref<number | null>(null)
const nodes = ref<Array<{ pokemon_id: number; pokemon_name: string; image_url?: string; is_root?: boolean }>>([])
const edges = ref<OpsEvolutionGraphEdge[]>([])
const positions = reactive<Record<number, Position>>({})
const canvasRef = ref<HTMLElement | null>(null)
const viewport = reactive({ x: 40, y: 40 })
const nodeEls = reactive<Record<number, HTMLElement | null>>({})
const nodeHeights = reactive<Record<number, number>>({})
const nodeObservers = new Map<number, ResizeObserver>()

const draftSourcePokemonId = ref<number | null>(null)
const dragSourceNodeId = ref<number | null>(null)
const connectingFrom = ref<number | null>(null)
const connectingPoint = ref<{ x: number; y: number } | null>(null)

const draggingNodeId = ref<number | null>(null)
const dragOffset = ref({ x: 0, y: 0 })
const panning = ref(false)
const panStart = ref({ x: 0, y: 0 })
const viewportStart = ref({ x: 0, y: 0 })
const hoveredEdgeKey = ref<string | null>(null)

const sortedNodes = computed(() => [...nodes.value].sort((a, b) => a.pokemon_id - b.pokemon_id))

const renderedEdges = computed(() => {
  const output: Array<OpsEvolutionGraphEdge & { x1: number; y1: number; x2: number; y2: number; mx: number; my: number }> = []
  for (const edge of edges.value) {
    const srcAnchor = getOutAnchor(edge.pre_pokemon_id)
    const dstAnchor = getInAnchor(edge.pokemon_id)
    if (!srcAnchor || !dstAnchor) continue
    const x1 = srcAnchor.x
    const y1 = srcAnchor.y
    const x2 = dstAnchor.x
    const y2 = dstAnchor.y
    output.push({
      ...edge,
      x1,
      y1,
      x2,
      y2,
      mx: (x1 + x2) / 2,
      my: (y1 + y2) / 2,
    })
  }
  return output
})

function ensureNodePosition(nodeId: number, index: number) {
  if (positions[nodeId]) return
  positions[nodeId] = { x: 140, y: 80 + index * 180 }
}

function buildTopDownLayout(graph: OpsEvolutionGraph) {
  const nodeIds = (graph.nodes || []).map((n) => n.pokemon_id)
  const idSet = new Set(nodeIds)
  const incoming = new Map<number, number>()
  const nexts = new Map<number, number[]>()
  for (const id of nodeIds) {
    incoming.set(id, 0)
    nexts.set(id, [])
  }
  for (const edge of graph.edges || []) {
    if (!idSet.has(edge.pre_pokemon_id) || !idSet.has(edge.pokemon_id)) continue
    incoming.set(edge.pokemon_id, (incoming.get(edge.pokemon_id) || 0) + 1)
    nexts.get(edge.pre_pokemon_id)?.push(edge.pokemon_id)
  }

  const roots = nodeIds.filter((id) => (incoming.get(id) || 0) === 0)
  const queue = [...roots]
  const level = new Map<number, number>()
  for (const r of roots) level.set(r, 0)

  while (queue.length) {
    const cur = queue.shift()!
    const curLv = level.get(cur) || 0
    for (const nxt of nexts.get(cur) || []) {
      const old = level.get(nxt)
      const nextLv = curLv + 1
      if (old === undefined || nextLv > old) {
        level.set(nxt, nextLv)
      }
      queue.push(nxt)
    }
  }

  for (const id of nodeIds) {
    if (!level.has(id)) level.set(id, 0)
  }
  const buckets = new Map<number, number[]>()
  for (const id of nodeIds) {
    const lv = level.get(id) || 0
    if (!buckets.has(lv)) buckets.set(lv, [])
    buckets.get(lv)!.push(id)
  }

  for (const key of Object.keys(positions)) delete positions[Number(key)]
  const levelKeys = [...buckets.keys()].sort((a, b) => a - b)
  for (const lv of levelKeys) {
    const ids = buckets.get(lv) || []
    ids.sort((a, b) => a - b)
    ids.forEach((id, idx) => {
      positions[id] = {
        x: 80 + idx * 280,
        y: 60 + lv * 180,
      }
    })
  }
}

function hydrateGraph(graph: OpsEvolutionGraph) {
  chainId.value = graph.chain_id
  nodes.value = graph.nodes || []
  edges.value = graph.edges || []
  if (nodes.value.length) {
    buildTopDownLayout(graph)
  } else {
    for (const key of Object.keys(positions)) delete positions[Number(key)]
  }
}

async function searchPokemonOptions() {
  loading.value = true
  try {
    const resp = await fetchOpsPokemon({ keyword: searchKeyword.value.trim(), page: 1, page_size: 30 })
    pokemonOptions.value = resp.items || []
  } finally {
    loading.value = false
  }
}

async function loadGraphByPokemon(item: OpsPokemonItem) {
  selectedPokemonId.value = item.id
  selectedPokemonName.value = item.name
  loading.value = true
  try {
    const graph = await fetchOpsEvolutionGraphByPokemonId(item.id)
    hydrateGraph(graph)
    showOpsToast(`已加载：${item.name}`, 'success')
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '加载失败', 'error')
  } finally {
    loading.value = false
  }
}

function hasNode(pokemonId: number) {
  return nodes.value.some((node) => node.pokemon_id === pokemonId)
}

function addNodeFromOption(item: OpsPokemonItem) {
  if (hasNode(item.id)) return
  nodes.value.push({
    pokemon_id: item.id,
    pokemon_name: item.name,
    image_url: '',
    is_root: true,
  })
  ensureNodePosition(item.id, nodes.value.length - 1)
}

function startSourceDrag(item: OpsPokemonItem) {
  draftSourcePokemonId.value = item.id
}

function onCanvasDrop(event: DragEvent) {
  event.preventDefault()
  if (!draftSourcePokemonId.value) return
  const item = pokemonOptions.value.find((x) => x.id === draftSourcePokemonId.value)
  if (!item) return
  addNodeFromOption(item)
  draftSourcePokemonId.value = null
}

function removeNode(nodeId: number) {
  nodes.value = nodes.value.filter((node) => node.pokemon_id !== nodeId)
  edges.value = edges.value.filter((edge) => edge.pre_pokemon_id !== nodeId && edge.pokemon_id !== nodeId)
  delete positions[nodeId]
  delete nodeHeights[nodeId]
  const oldObserver = nodeObservers.get(nodeId)
  if (oldObserver) {
    oldObserver.disconnect()
    nodeObservers.delete(nodeId)
  }
  delete nodeEls[nodeId]
}

function removeEdge(src: number, dst: number) {
  edges.value = edges.value.filter((edge) => !(edge.pre_pokemon_id === src && edge.pokemon_id === dst))
}

function beginNodeDrag(event: MouseEvent, nodeId: number) {
  if ((event.target as HTMLElement)?.classList.contains('link-dot')) return
  const box = canvasRef.value?.getBoundingClientRect()
  if (!box) return
  const pos = positions[nodeId]
  if (!pos) return
  draggingNodeId.value = nodeId
  dragOffset.value = {
    x: event.clientX - box.left - viewport.x - pos.x,
    y: event.clientY - box.top - viewport.y - pos.y,
  }
  window.addEventListener('mousemove', onNodeDragging)
  window.addEventListener('mouseup', endNodeDrag)
}

function onNodeDragging(event: MouseEvent) {
  if (!draggingNodeId.value) return
  const box = canvasRef.value?.getBoundingClientRect()
  if (!box) return
  const nodeId = draggingNodeId.value
  positions[nodeId] = {
    x: Math.max(0, event.clientX - box.left - viewport.x - dragOffset.value.x),
    y: Math.max(0, event.clientY - box.top - viewport.y - dragOffset.value.y),
  }
}

function endNodeDrag() {
  draggingNodeId.value = null
  window.removeEventListener('mousemove', onNodeDragging)
  window.removeEventListener('mouseup', endNodeDrag)
}

function beginConnect(event: MouseEvent, nodeId: number) {
  event.stopPropagation()
  connectingFrom.value = nodeId
  dragSourceNodeId.value = nodeId
  window.addEventListener('mousemove', onConnectingMove)
  window.addEventListener('mouseup', onConnectingCancel)
}

function onConnectingMove(event: MouseEvent) {
  const box = canvasRef.value?.getBoundingClientRect()
  if (!box) return
  connectingPoint.value = {
    x: event.clientX - box.left - viewport.x,
    y: event.clientY - box.top - viewport.y,
  }
}

function onConnectingCancel() {
  connectingFrom.value = null
  connectingPoint.value = null
  dragSourceNodeId.value = null
  window.removeEventListener('mousemove', onConnectingMove)
  window.removeEventListener('mouseup', onConnectingCancel)
}

function completeConnect(targetNodeId: number) {
  const src = dragSourceNodeId.value
  if (!src || src === targetNodeId) {
    onConnectingCancel()
    return
  }
  if (edges.value.some((edge) => edge.pre_pokemon_id === src && edge.pokemon_id === targetNodeId)) {
    onConnectingCancel()
    return
  }
  const condition = window.prompt('请输入进化条件（可留空）', '') || ''
  edges.value.push({ pre_pokemon_id: src, pokemon_id: targetNodeId, pre_evolution_condition: condition.trim() })
  onConnectingCancel()
}

function setNodeRef(nodeId: number, el: Element | null) {
  const oldObserver = nodeObservers.get(nodeId)
  if (oldObserver) {
    oldObserver.disconnect()
    nodeObservers.delete(nodeId)
  }
  const nodeEl = (el as HTMLElement) || null
  nodeEls[nodeId] = nodeEl
  if (!nodeEl) return
  nodeHeights[nodeId] = nodeEl.offsetHeight || 130
  const observer = new ResizeObserver((entries) => {
    const h = entries[0]?.contentRect?.height
    if (h && Number.isFinite(h)) {
      nodeHeights[nodeId] = h
    }
  })
  observer.observe(nodeEl)
  nodeObservers.set(nodeId, observer)
}

function getInAnchor(nodeId: number) {
  const pos = positions[nodeId]
  if (!pos) return null
  return { x: pos.x + 120, y: pos.y }
}

function getOutAnchor(nodeId: number) {
  const pos = positions[nodeId]
  if (!pos) return null
  const h = nodeHeights[nodeId] || nodeEls[nodeId]?.offsetHeight || 130
  return { x: pos.x + 120, y: pos.y + h }
}

function updateEdgeCondition(edge: OpsEvolutionGraphEdge) {
  edge.pre_evolution_condition = (edge.pre_evolution_condition || '').trim()
}

function getIncomingEdges(nodeId: number) {
  return edges.value.filter((edge) => edge.pokemon_id === nodeId)
}

function getEdgeKey(edge: { pre_pokemon_id: number; pokemon_id: number }) {
  return `${edge.pre_pokemon_id}-${edge.pokemon_id}`
}

function onEdgeEnter(edge: { pre_pokemon_id: number; pokemon_id: number }) {
  hoveredEdgeKey.value = getEdgeKey(edge)
}

function onEdgeLeave(edge: { pre_pokemon_id: number; pokemon_id: number }) {
  if (hoveredEdgeKey.value === getEdgeKey(edge)) hoveredEdgeKey.value = null
}

function beginPan(event: MouseEvent) {
  if (draggingNodeId.value || connectingFrom.value) return
  const target = event.target as HTMLElement
  if (target.closest('.node-card')) return
  if (target.closest('.link-dot') || target.closest('input') || target.closest('button') || target.closest('.edge-delete')) return
  panning.value = true
  panStart.value = { x: event.clientX, y: event.clientY }
  viewportStart.value = { x: viewport.x, y: viewport.y }
  event.preventDefault()
  window.addEventListener('mousemove', onPanning)
  window.addEventListener('mouseup', endPan)
}

function onPanning(event: MouseEvent) {
  if (!panning.value) return
  viewport.x = viewportStart.value.x + (event.clientX - panStart.value.x)
  viewport.y = viewportStart.value.y + (event.clientY - panStart.value.y)
}

function endPan() {
  panning.value = false
  window.removeEventListener('mousemove', onPanning)
  window.removeEventListener('mouseup', endPan)
}

function resetViewport() {
  viewport.x = 40
  viewport.y = 40
}

async function saveGraph() {
  if (!selectedPokemonId.value) {
    showOpsToast('请先选择一个精灵作为编辑对象', 'error')
    return
  }
  saving.value = true
  try {
    const payload = {
      nodes: nodes.value.map((node) => ({ pokemon_id: node.pokemon_id })),
      edges: edges.value.map((edge) => ({
        pre_pokemon_id: edge.pre_pokemon_id,
        pokemon_id: edge.pokemon_id,
        pre_evolution_condition: edge.pre_evolution_condition || '',
      })),
    }
    const latest = await updateOpsEvolutionGraphByPokemonId(selectedPokemonId.value, payload)
    hydrateGraph(latest)
    if (latest.chain_id) {
      showOpsToast(`保存成功（链ID：${latest.chain_id}）`, 'success')
    } else {
      showOpsToast('已删除整条进化链', 'success')
    }
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function deleteChain() {
  if (!chainId.value) return
  if (!window.confirm(`确认删除进化链 ${chainId.value} 吗？`)) return
  deleting.value = true
  try {
    await deleteOpsEvolutionGraphByChainId(chainId.value)
    chainId.value = null
    nodes.value = []
    edges.value = []
    showOpsToast('已删除整条进化链', 'success')
  } catch (err: any) {
    showOpsToast(err?.response?.data?.detail || '删除失败', 'error')
  } finally {
    deleting.value = false
  }
}

onBeforeUnmount(() => {
  endNodeDrag()
  onConnectingCancel()
  endPan()
  for (const observer of nodeObservers.values()) {
    observer.disconnect()
  }
  nodeObservers.clear()
})
</script>

<template>
  <section class="page">
    <header class="toolbar">
      <h3>进化链维护</h3>
      <div class="actions">
        <button class="btn-secondary" :disabled="loading" @click="searchPokemonOptions">搜索精灵</button>
        <button class="btn-secondary" @click="resetViewport">重置视角</button>
        <button class="btn-primary" :disabled="saving || loading" @click="saveGraph">{{ saving ? '保存中...' : '保存改动' }}</button>
        <button class="btn-danger" :disabled="!chainId || deleting" @click="deleteChain">删除整链</button>
      </div>
    </header>

    <div class="panel-grid">
      <aside class="left-panel">
        <label class="block">
          <span>按名称搜索精灵</span>
          <input v-model="searchKeyword" placeholder="例如：小火龙" @keyup.enter="searchPokemonOptions" />
        </label>
        <p class="tip">将左侧卡片拖到右侧画布空白处，可新增节点；无链时即新建链。</p>
        <div class="pokemon-list">
          <article
            v-for="item in pokemonOptions"
            :key="item.id"
            class="pokemon-item"
            draggable="true"
            @dragstart="startSourceDrag(item)"
          >
            <div class="main" @click="loadGraphByPokemon(item)">
              <strong>{{ item.name }}</strong>
              <small>#{{ item.no }}</small>
            </div>
            <button class="mini-btn" @click.stop="addNodeFromOption(item)">+节点</button>
          </article>
          <div v-if="!pokemonOptions.length" class="empty">暂无数据，请先搜索</div>
        </div>
      </aside>

      <main class="canvas-wrap">
        <div class="meta">
          <span>当前精灵：{{ selectedPokemonName || '未选择' }}</span>
          <span>链ID：{{ chainId ?? '未创建' }}</span>
          <span>节点：{{ nodes.length }}，关系：{{ edges.length }}</span>
        </div>
        <section
          ref="canvasRef"
          class="canvas"
          :class="{ panning }"
          @mousedown="beginPan"
          @dragover.prevent
          @drop="onCanvasDrop"
        >
          <div class="viewport" :style="{ transform: `translate(${viewport.x}px, ${viewport.y}px)` }">
            <svg class="edges" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <polygon points="0 0, 8 4, 0 8" fill="#409eff" />
                </marker>
              </defs>
              <line
                v-for="edge in renderedEdges"
                :key="`${edge.pre_pokemon_id}-${edge.pokemon_id}`"
                :x1="edge.x1"
                :y1="edge.y1"
                :x2="edge.x2"
                :y2="edge.y2"
                stroke="#409eff"
                stroke-width="2"
                marker-end="url(#arrow)"
              />
              <line
                v-if="connectingFrom && connectingPoint && positions[connectingFrom]"
                :x1="(getOutAnchor(connectingFrom)?.x || 0)"
                :y1="(getOutAnchor(connectingFrom)?.y || 0)"
                :x2="connectingPoint.x"
                :y2="connectingPoint.y"
                stroke="#67c23a"
                stroke-width="2"
                stroke-dasharray="6 6"
              />
            </svg>

            <article
              v-for="node in sortedNodes"
              :key="node.pokemon_id"
              class="node-card"
              :ref="(el) => setNodeRef(node.pokemon_id, el)"
              :style="{ left: `${positions[node.pokemon_id]?.x || 0}px`, top: `${positions[node.pokemon_id]?.y || 0}px` }"
              @mousedown="beginNodeDrag($event, node.pokemon_id)"
            >
              <button class="icon-btn danger node-delete-top" title="删除节点" @click="removeNode(node.pokemon_id)">-</button>
              <button class="link-dot in" title="作为目标松开完成连线" @mouseup.stop="completeConnect(node.pokemon_id)"></button>
              <div class="title">{{ node.pokemon_name || `#${node.pokemon_id}` }}</div>
              <div class="sub"><span v-if="node.is_root" class="tag">起点</span></div>
              <div class="node-actions">
                <button class="link-dot out" title="新增线：按住并拖动到目标节点" @mousedown="beginConnect($event, node.pokemon_id)">+</button>
              </div>
              <div class="edge-editor">
                <div v-for="edge in getIncomingEdges(node.pokemon_id)" :key="`${edge.pre_pokemon_id}-${edge.pokemon_id}`" class="edge-row">
                  <input v-model="edge.pre_evolution_condition" placeholder="进化条件" @blur="updateEdgeCondition(edge)" />
                </div>
              </div>
            </article>
            <button
              v-for="edge in renderedEdges"
              :key="`edge-hit-${edge.pre_pokemon_id}-${edge.pokemon_id}`"
              class="edge-hit-zone"
              :style="{ left: `${edge.mx}px`, top: `${edge.my}px` }"
              @mouseenter="onEdgeEnter(edge)"
              @mouseleave="onEdgeLeave(edge)"
            />
            <button
              v-for="edge in renderedEdges"
              :key="`edge-btn-${edge.pre_pokemon_id}-${edge.pokemon_id}`"
              class="edge-delete-btn"
              :class="{ visible: hoveredEdgeKey === getEdgeKey(edge) }"
              :style="{ left: `${edge.mx}px`, top: `${edge.my}px` }"
              @mouseenter="onEdgeEnter(edge)"
              @mouseleave="onEdgeLeave(edge)"
              @click.stop="removeEdge(edge.pre_pokemon_id, edge.pokemon_id)"
            >
              -
            </button>
          </div>

          <div v-if="!nodes.length" class="canvas-empty">将左侧精灵拖到这里开始维护进化链</div>
          <div v-else class="canvas-hint">空白处按住拖动可平移画布视角</div>
        </section>
      </main>
    </div>
  </section>
</template>

<style scoped>
.page { display: grid; gap: 12px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.actions { display: flex; gap: 8px; }
.panel-grid { display: grid; grid-template-columns: 320px 1fr; gap: 12px; min-height: 70vh; }
.left-panel, .canvas-wrap { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; }
.block { display: grid; gap: 6px; }
input { height: 36px; border: 1px solid #dcdfe6; border-radius: 6px; padding: 0 10px; }
.tip { color: #909399; font-size: 12px; margin: 8px 0; }
.pokemon-list { display: grid; gap: 8px; max-height: 56vh; overflow: auto; }
.pokemon-item { border: 1px solid #ebeef5; border-radius: 8px; padding: 8px; display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.pokemon-item .main { cursor: pointer; display: grid; }
.pokemon-item small { color: #909399; }
.meta { display: flex; gap: 18px; font-size: 13px; margin-bottom: 8px; color: #606266; }
.canvas { position: relative; min-height: 62vh; border: 1px dashed #dcdfe6; border-radius: 8px; background: #f8fafc; overflow: hidden; cursor: grab; }
.canvas.panning { cursor: grabbing; }
.viewport { position: absolute; inset: 0; transform-origin: 0 0; }
.edges { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; z-index: 1; pointer-events: none; }
.node-card { position: absolute; width: 240px; background: #fff; border: 1px solid #dcdfe6; border-radius: 10px; padding: 10px; box-shadow: 0 4px 14px rgba(0,0,0,.06); cursor: move; z-index: 2; }
.title { font-weight: 700; color: #303133; }
.sub { margin-top: 4px; color: #909399; font-size: 12px; }
.tag { margin-left: 6px; color: #67c23a; }
.node-actions { margin-top: 10px; display: flex; justify-content: center; align-items: center; }
.edge-editor { margin-top: 8px; display: grid; gap: 6px; }
.edge-row { display: grid; grid-template-columns: 1fr; gap: 6px; align-items: center; }
.edge-row input { height: 26px; font-size: 12px; }
.link-dot { width: 14px; height: 14px; border-radius: 999px; border: none; cursor: crosshair; background: #409eff; }
.link-dot.in { position: absolute; left: 50%; top: -7px; transform: translateX(-50%); background: #67c23a; z-index: 5; }
.link-dot.out {
  position: absolute;
  left: 50%;
  bottom: -11px;
  transform: translateX(-50%);
  width: 22px;
  height: 22px;
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  line-height: 22px;
  text-align: center;
  background: #409eff;
}
.icon-btn {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  border: 1px solid #dcdfe6;
  background: #fff;
  cursor: pointer;
  line-height: 18px;
  font-size: 16px;
}
.icon-btn.danger {
  border-color: #f56c6c;
  color: #f56c6c;
}
.node-delete-top {
  position: absolute;
  right: 8px;
  top: 8px;
  z-index: 6;
}
.edge-delete-btn {
  position: absolute;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  border-radius: 999px;
  border: 1px solid #f56c6c;
  background: #f56c6c;
  color: #fff;
  font-size: 14px;
  line-height: 16px;
  text-align: center;
  cursor: pointer;
  z-index: 5;
  padding: 0;
  opacity: 0;
  pointer-events: none;
  transition: opacity .15s ease;
}
.edge-delete-btn.visible {
  opacity: 1;
  pointer-events: auto;
}
.edge-hit-zone {
  position: absolute;
  transform: translate(-50%, -50%);
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 999px;
  background: transparent;
  z-index: 4;
  cursor: pointer;
  padding: 0;
}
.mini-btn { height: 24px; border: 1px solid #dcdfe6; background: #fff; border-radius: 4px; font-size: 12px; cursor: pointer; padding: 0 8px; }
.mini-btn.danger, .btn-danger { border-color: #f56c6c; color: #f56c6c; background: #fff; }
.canvas-empty { position: absolute; inset: 0; display: grid; place-items: center; color: #909399; }
.canvas-hint { position: absolute; right: 12px; bottom: 8px; color: #909399; font-size: 12px; background: rgba(255,255,255,.85); padding: 3px 8px; border-radius: 6px; }
.btn-primary, .btn-secondary, .btn-danger { height: 34px; border-radius: 6px; padding: 0 12px; cursor: pointer; border: 1px solid #dcdfe6; background: #fff; }
.btn-primary { background: #409eff; border-color: #409eff; color: #fff; }
.empty { color: #909399; text-align: center; padding: 12px; }
</style>
