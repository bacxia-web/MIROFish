<template>
  <div class="main-view">
    <!-- Header -->
    <header class="app-header">
      <div class="header-left">
        <div class="brand" @click="router.push('/')">MIROFISH</div>
      </div>
      
      <div class="header-center">
        <div class="view-switcher">
          <button 
            v-for="mode in ['graph', 'split', 'workbench']" 
            :key="mode"
            class="switch-btn"
            :class="{ active: viewMode === mode }"
            @click="viewMode = mode"
          >
            {{ { graph: $t('main.layoutGraph'), split: $t('main.layoutSplit'), workbench: $t('main.layoutWorkbench') }[mode] }}
          </button>
        </div>
      </div>

      <div class="header-right">
        <LanguageSwitcher />
        <div class="step-divider"></div>
        <div class="workflow-step">
          <span class="step-num">Step 4/5</span>
          <span class="step-name">{{ $tm('main.stepNames')[3] }}</span>
        </div>
        <div class="step-divider"></div>
        <span class="status-indicator" :class="statusClass">
          <span class="dot"></span>
          {{ statusText }}
        </span>
        <div v-if="hasDualGraph" class="ab-status-bar">
          <span class="ab-pill">RAW: {{ abReportStatus.raw }}</span>
          <span class="ab-pill">DISAMB: {{ abReportStatus.disamb }}</span>
        </div>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="content-area">
      <!-- Left Panel: Graph / Agents tab -->
      <div class="panel-wrapper left" :style="leftPanelStyle">
        <!-- Tab switcher -->
        <div class="left-tab-bar">
          <button
            class="left-tab"
            :class="{ active: leftTab === 'graph' }"
            @click="leftTab = 'graph'"
          >Graph</button>
          <button
            class="left-tab"
            :class="{ active: leftTab === 'agents' }"
            @click="leftTab = 'agents'"
          >Agents <span v-if="simulationId" class="tab-dot">●</span></button>
        </div>
        <div class="left-tab-content">
          <GraphPanel
            v-show="leftTab === 'graph'"
            :graphData="graphData"
            :loading="graphLoading"
            :currentPhase="4"
            :isSimulating="false"
            :graphVariant="graphVariant"
            :showGraphVariantTabs="hasDualGraph"
            @refresh="refreshGraph"
            @toggle-maximize="toggleMaximize('graph')"
            @select-variant="onGraphVariantSelect"
          />
          <AgentsPanel
            v-if="leftTab === 'agents'"
            :simulationId="simulationId"
          />
        </div>
      </div>

      <!-- Right Panel: Step4 报告生成 -->
      <div class="panel-wrapper right" :style="rightPanelStyle">
        <Step4Report
          :reportId="currentReportId"
          :simulationId="simulationId"
          :systemLogs="systemLogs"
          @add-log="addLog"
          @update-status="updateStatus"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import GraphPanel from '../components/GraphPanel.vue'
import Step4Report from '../components/Step4Report.vue'
import AgentsPanel from '../components/AgentsPanel.vue'
import { getProject, getGraphData } from '../api/graph'
import {
  effectiveGraphIdFromProject,
  getGraphVariantForProject,
  resolveProjectGraphId
} from '../utils/graphVariant'
import { getSimulation } from '../api/simulation'
import { getReport } from '../api/report'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

// Props
const props = defineProps({
  reportId: String
})

// Layout State - 默认切换到工作台视角
const viewMode = ref('workbench')

// 左侧面板 tab：graph | agents
const leftTab = ref('graph')

// Data State
const currentReportId = ref(route.params.reportId)
const simulationId = ref(null)
const reportIds = ref({
  raw: '',
  disamb: ''
})
const projectData = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const graphVariant = ref('disamb')
const hasDualGraph = computed(() => {
  const p = projectData.value
  return !!(p?.graph_id_raw && p?.graph_id_disamb && p.graph_id_raw !== p.graph_id_disamb)
})
const systemLogs = ref([])
const currentStatus = ref('processing') // processing | completed | error
const abReportStatus = ref({ raw: '-', disamb: '-' })
let abStatusTimer = null

// --- Computed Layout Styles ---
const leftPanelStyle = computed(() => {
  if (viewMode.value === 'graph') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'workbench') return { width: '0%', opacity: 0, transform: 'translateX(-20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

const rightPanelStyle = computed(() => {
  if (viewMode.value === 'workbench') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'graph') return { width: '0%', opacity: 0, transform: 'translateX(20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

// --- Status Computed ---
const statusClass = computed(() => {
  return currentStatus.value
})

const statusText = computed(() => {
  if (currentStatus.value === 'error') return 'Error'
  if (currentStatus.value === 'completed') return 'Completed'
  return 'Generating'
})

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + new Date().getMilliseconds().toString().padStart(3, '0')
  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 200) {
    systemLogs.value.shift()
  }
}

const updateStatus = (status) => {
  currentStatus.value = status
}

// --- Layout Methods ---
const toggleMaximize = (target) => {
  if (viewMode.value === target) {
    viewMode.value = 'split'
  } else {
    viewMode.value = target
  }
}

// --- Data Logic ---
const loadReportData = async (targetReportId = currentReportId.value) => {
  try {
    addLog(t('log.loadReportData', { id: targetReportId }))

    // 获取 report 信息以获取 simulation_id
    const reportRes = await getReport(targetReportId)
    if (reportRes.success && reportRes.data) {
      const reportData = reportRes.data
      simulationId.value = reportData.simulation_id
      currentReportId.value = targetReportId

      if (simulationId.value) {
        // 获取 simulation 信息
        const simRes = await getSimulation(simulationId.value)
        if (simRes.success && simRes.data) {
          const simData = simRes.data

          // 获取 project 信息
          if (simData.project_id) {
            const projRes = await getProject(simData.project_id)
            if (projRes.success && projRes.data) {
              projectData.value = projRes.data
              graphVariant.value = getGraphVariantForProject(projRes.data.project_id)
              const qRaw = typeof route.query.rawReportId === 'string' ? route.query.rawReportId : ''
              const qDis = typeof route.query.disambReportId === 'string' ? route.query.disambReportId : ''
              reportIds.value = {
                raw: qRaw || currentReportId.value,
                disamb: qDis || currentReportId.value
              }
              if (hasDualGraph.value) {
                const switchedId = graphVariant.value === 'raw' ? reportIds.value.raw : reportIds.value.disamb
                if (switchedId && switchedId !== currentReportId.value) {
                  return loadReportData(switchedId)
                }
              }
              refreshAbReportStatus()
              addLog(t('log.projectLoadSuccess', { id: projRes.data.project_id }))

              const gid = effectiveGraphIdFromProject(projRes.data, projRes.data.project_id)
              if (gid) {
                await loadGraph(gid)
              }
            }
          }
        }
      }
    } else {
      addLog(t('log.getReportInfoFailed', { error: reportRes.error || t('common.unknownError') }))
    }
  } catch (err) {
    addLog(t('log.loadException', { error: err.message }))
  }
}

const loadGraph = async (graphId) => {
  graphLoading.value = true
  
  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      addLog(t('log.graphDataLoadSuccess'))
    }
  } catch (err) {
    addLog(t('log.graphLoadFailed', { error: err.message }))
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  const pid = projectData.value?.project_id
  const gid = effectiveGraphIdFromProject(projectData.value, pid)
  if (gid) loadGraph(gid)
}

const onGraphVariantSelect = (v) => {
  if (v !== 'raw' && v !== 'disamb') return
  graphVariant.value = v
  const pid = projectData.value?.project_id
  if (pid) localStorage.setItem(`mirofish_gv_${pid}`, v)
  const mappedReport = v === 'raw' ? reportIds.value.raw : reportIds.value.disamb
  if (mappedReport && mappedReport !== currentReportId.value) {
    router.replace({
      name: 'Report',
      params: { reportId: mappedReport },
      query: {
        ...route.query,
        rawReportId: reportIds.value.raw || undefined,
        disambReportId: reportIds.value.disamb || undefined
      }
    })
    loadReportData(mappedReport)
  }
  const gid = resolveProjectGraphId(projectData.value, v)
  if (gid) loadGraph(gid)
}

const refreshAbReportStatus = async () => {
  if (!hasDualGraph.value) return
  const map = { raw: reportIds.value.raw, disamb: reportIds.value.disamb }
  const next = { raw: '-', disamb: '-' }
  for (const k of ['raw', 'disamb']) {
    const rid = map[k]
    if (!rid) continue
    try {
      const r = await getReport(rid)
      next[k] = r?.success ? (r.data?.status || 'unknown') : 'error'
    } catch {
      next[k] = 'error'
    }
  }
  abReportStatus.value = next
}

// Watch route params
watch(() => route.params.reportId, (newId) => {
  if (newId && newId !== currentReportId.value) {
    currentReportId.value = newId
    loadReportData()
  }
}, { immediate: true })

onMounted(() => {
  addLog(t('log.reportViewInit'))
  loadReportData()
  abStatusTimer = setInterval(refreshAbReportStatus, 5000)
})

onUnmounted(() => {
  if (abStatusTimer) clearInterval(abStatusTimer)
})
</script>

<style scoped>
.main-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #0e1724;
  overflow: hidden;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

/* Header */
.app-header {
  height: 60px;
  border-bottom: 1px solid #1a2a3e;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: rgba(4,8,16,0.95);
  backdrop-filter: blur(16px);
  z-index: 100;
  position: relative;
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.brand {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 1px;
  color: #e2e8f0;
  cursor: pointer;
}

.view-switcher {
  display: flex;
  background: #0e1724;
  padding: 4px;
  border-radius: 6px;
  gap: 4px;
}

.switch-btn {
  border: none;
  background: transparent;
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.switch-btn.active {
  background: #1a2a3e;
  color: #e2e8f0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.workflow-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.step-num {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: #64748b;
}

.step-name {
  font-weight: 700;
  color: #e2e8f0;
}

.step-divider {
  width: 1px;
  height: 14px;
  background-color: #1a2a3e;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2d3a4a;
}

.status-indicator.processing .dot { background: #60a5fa; animation: pulse 1s infinite; }
.status-indicator.completed .dot { background: #4CAF50; }
.status-indicator.error .dot { background: #F44336; }

.ab-status-bar {
  display: flex;
  gap: 6px;
}

.ab-pill {
  border: 1px solid #ddd;
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 11px;
  color: #555;
}

@keyframes pulse { 50% { opacity: 0.5; } }

/* Content */
.content-area {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.panel-wrapper {
  height: 100%;
  overflow: hidden;
  transition: width 0.4s cubic-bezier(0.25, 0.8, 0.25, 1), opacity 0.3s ease, transform 0.3s ease;
  will-change: width, opacity, transform;
}

.panel-wrapper.left {
  border-right: 1px solid #1a2a3e;
  display: flex;
  flex-direction: column;
}

/* Left panel tab bar */
.left-tab-bar {
  display: flex;
  border-bottom: 1px solid #1a2a3e;
  background: #0e1724;
  flex-shrink: 0;
  height: 36px;
}

.left-tab {
  flex: 1;
  border: none;
  background: transparent;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.left-tab.active {
  color: #e2e8f0;
  background: #131e2e;
}

.left-tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: #3B82F6;
}

.left-tab:hover:not(.active) {
  color: #94a3b8;
  background: rgba(255,255,255,0.03);
}

.tab-dot {
  font-size: 7px;
  color: #10B981;
  vertical-align: middle;
  margin-left: 3px;
}

.left-tab-content {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.left-tab-content > * {
  height: 100%;
}
</style>
