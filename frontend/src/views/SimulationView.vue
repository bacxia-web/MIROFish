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
          <span class="step-num">Step 2/5</span>
          <span class="step-name">{{ $tm('main.stepNames')[1] }}</span>
        </div>
        <div class="step-divider"></div>
        <span class="status-indicator" :class="statusClass">
          <span class="dot"></span>
          {{ statusText }}
        </span>
        <div v-if="hasDualGraph" class="ab-status-bar">
          <span class="ab-pill">RAW: {{ abSimStatus.raw }}</span>
          <span class="ab-pill">DISAMB: {{ abSimStatus.disamb }}</span>
        </div>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="content-area">
      <!-- Left Panel: Graph -->
      <div class="panel-wrapper left" :style="leftPanelStyle">
        <GraphPanel 
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="2"
          :graphVariant="graphVariant"
          :showGraphVariantTabs="hasDualGraph"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
          @select-variant="onGraphVariantSelect"
        />
      </div>

      <!-- Right Panel: Step2 环境搭建 -->
      <div class="panel-wrapper right" :style="rightPanelStyle">
        <Step2EnvSetup
          :simulationId="currentSimulationId"
          :projectData="projectData"
          :graphData="graphData"
          :systemLogs="systemLogs"
          @go-back="handleGoBack"
          @next-step="handleNextStep"
          @add-log="addLog"
          @update-status="updateStatus"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GraphPanel from '../components/GraphPanel.vue'
import Step2EnvSetup from '../components/Step2EnvSetup.vue'
import { getProject, getGraphData } from '../api/graph'
import {
  effectiveGraphIdFromProject,
  getGraphVariantForProject,
  resolveProjectGraphId
} from '../utils/graphVariant'
import { getSimulation, stopSimulation, getEnvStatus, closeSimulationEnv } from '../api/simulation'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

// Props
const props = defineProps({
  simulationId: String
})

// Layout State
const viewMode = ref('split')

// Data State
const currentSimulationId = ref(route.params.simulationId)
const simulationIds = ref({
  raw: '',
  disamb: ''
})
const projectData = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const systemLogs = ref([])
const currentStatus = ref('processing') // processing | completed | error
const abSimStatus = ref({ raw: '-', disamb: '-' })
let abStatusTimer = null

const graphVariant = ref('disamb')
const hasDualGraph = computed(() => {
  const p = projectData.value
  return !!(p?.graph_id_raw && p?.graph_id_disamb && p.graph_id_raw !== p.graph_id_disamb)
})

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
  if (currentStatus.value === 'completed') return 'Ready'
  return 'Preparing'
})

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + new Date().getMilliseconds().toString().padStart(3, '0')
  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 100) {
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

const handleGoBack = () => {
  // 返回到 process 页面
  if (projectData.value?.project_id) {
    router.push({ name: 'Process', params: { projectId: projectData.value.project_id } })
  } else {
    router.push('/')
  }
}

const handleNextStep = (params = {}) => {
  addLog(t('log.enterStep3'))

  // 记录模拟轮数配置
  if (params.maxRounds) {
    addLog(t('log.customRoundsConfig', { rounds: params.maxRounds }))
  } else {
    addLog(t('log.useAutoRounds'))
  }
  
  // 构建路由参数
  const routeParams = {
    name: 'SimulationRun',
    params: { simulationId: currentSimulationId.value },
    query: {
      rawSimulationId: simulationIds.value.raw || undefined,
      disambSimulationId: simulationIds.value.disamb || undefined
    }
  }
  
  // 如果有自定义轮数，通过 query 参数传递
  if (params.maxRounds) {
    routeParams.query.maxRounds = params.maxRounds
  }
  
  // 跳转到 Step 3 页面
  router.push(routeParams)
}

// --- Data Logic ---

/**
 * 检查并关闭正在运行的模拟
 * 当用户从 Step 3 返回到 Step 2 时，默认用户要退出模拟
 */
const checkAndStopRunningSimulation = async () => {
  if (!currentSimulationId.value) return
  
  try {
    // 先检查模拟环境是否存活
    const envStatusRes = await getEnvStatus({ simulation_id: currentSimulationId.value })
    
    if (envStatusRes.success && envStatusRes.data?.env_alive) {
      addLog(t('log.detectedSimEnvRunning'))
      
      // 尝试优雅关闭模拟环境
      try {
        const closeRes = await closeSimulationEnv({ 
          simulation_id: currentSimulationId.value,
          timeout: 10  // 10秒超时
        })
        
        if (closeRes.success) {
          addLog(t('log.simEnvClosed'))
        } else {
          addLog(t('log.closeSimEnvFailedWithError', { error: closeRes.error || t('common.unknownError') }))
          // 如果优雅关闭失败，尝试强制停止
          await forceStopSimulation()
        }
      } catch (closeErr) {
        addLog(t('log.closeSimEnvException', { error: closeErr.message }))
        // 如果优雅关闭异常，尝试强制停止
        await forceStopSimulation()
      }
    } else {
      // 环境未运行，但可能进程还在，检查模拟状态
      const simRes = await getSimulation(currentSimulationId.value)
      if (simRes.success && simRes.data?.status === 'running') {
        addLog(t('log.detectedSimRunning'))
        await forceStopSimulation()
      }
    }
  } catch (err) {
    // 检查环境状态失败不影响后续流程
    console.warn('检查模拟状态失败:', err)
  }
}

/**
 * 强制停止模拟
 */
const forceStopSimulation = async () => {
  try {
    const stopRes = await stopSimulation({ simulation_id: currentSimulationId.value })
    if (stopRes.success) {
      addLog(t('log.simForceStopSuccess'))
    } else {
      addLog(t('log.forceStopSimFailed', { error: stopRes.error || t('common.unknownError') }))
    }
  } catch (err) {
    addLog(t('log.forceStopSimException', { error: err.message }))
  }
}

const loadSimulationData = async () => {
  try {
    addLog(t('log.loadingSimData', { id: currentSimulationId.value }))

    // 获取 simulation 信息
    const simRes = await getSimulation(currentSimulationId.value)
    if (simRes.success && simRes.data) {
      const simData = simRes.data

      // 获取 project 信息
      if (simData.project_id) {
        const projRes = await getProject(simData.project_id)
        if (projRes.success && projRes.data) {
          projectData.value = projRes.data
          graphVariant.value = getGraphVariantForProject(projRes.data.project_id)
          const qRaw = typeof route.query.rawSimulationId === 'string' ? route.query.rawSimulationId : ''
          const qDis = typeof route.query.disambSimulationId === 'string' ? route.query.disambSimulationId : ''
          simulationIds.value = {
            raw: qRaw || currentSimulationId.value,
            disamb: qDis || currentSimulationId.value
          }
          if (hasDualGraph.value) {
            const switchedId = graphVariant.value === 'raw' ? simulationIds.value.raw : simulationIds.value.disamb
            if (switchedId && switchedId !== currentSimulationId.value) {
              currentSimulationId.value = switchedId
              return loadSimulationData()
            }
          }
          refreshAbSimulationStatus()
          addLog(t('log.projectLoadSuccess', { id: projRes.data.project_id }))
          
          // 获取 graph 数据
          const gid = effectiveGraphIdFromProject(projRes.data, projRes.data.project_id)
          if (gid) {
            await loadGraph(gid)
          }
        }
      }
    } else {
      addLog(t('log.loadSimDataFailed', { error: simRes.error || t('common.unknownError') }))
    }
  } catch (err) {
    addLog(t('log.loadException', { error: err.message }))
  }
}

const refreshAbSimulationStatus = async () => {
  if (!hasDualGraph.value) return
  const map = { raw: simulationIds.value.raw, disamb: simulationIds.value.disamb }
  const next = { raw: '-', disamb: '-' }
  for (const k of ['raw', 'disamb']) {
    const sid = map[k]
    if (!sid) continue
    try {
      const r = await getSimulation(sid)
      next[k] = r?.success ? (r.data?.status || 'unknown') : 'error'
    } catch {
      next[k] = 'error'
    }
  }
  abSimStatus.value = next
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
  const mappedSim = v === 'raw' ? simulationIds.value.raw : simulationIds.value.disamb
  if (mappedSim && mappedSim !== currentSimulationId.value) {
    currentSimulationId.value = mappedSim
    router.replace({
      name: 'Simulation',
      params: { simulationId: mappedSim },
      query: {
        ...route.query,
        rawSimulationId: simulationIds.value.raw || undefined,
        disambSimulationId: simulationIds.value.disamb || undefined
      }
    })
    loadSimulationData()
  }
  const gid = resolveProjectGraphId(projectData.value, v)
  if (gid) loadGraph(gid)
}

onMounted(async () => {
  addLog(t('log.simViewInit'))
  
  // 检查并关闭正在运行的模拟（用户从 Step 3 返回时）
  await checkAndStopRunningSimulation()
  
  // 加载模拟数据
  loadSimulationData()
  abStatusTimer = setInterval(refreshAbSimulationStatus, 5000)
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
  background: #FFF;
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

.brand {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 1px;
  color: #e2e8f0;
  cursor: pointer;
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
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

.status-indicator.processing .dot { background: #3B82F6; animation: pulse 1s infinite; }
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
  border-right: 1px solid #EAEAEA;
}
</style>

