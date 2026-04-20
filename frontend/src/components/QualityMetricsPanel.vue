<template>
  <div class="quality-metrics-panel" v-if="projectId">
    <div class="qm-header">
      <h3 class="qm-title">质量指标报表</h3>
      <button type="button" class="qm-refresh" :disabled="loading" @click="load">
        {{ loading ? '加载中…' : '刷新指标' }}
      </button>
    </div>
    <p v-if="error" class="qm-error">{{ error }}</p>
    <div class="qm-charts">
      <div ref="chartGraphRef" class="qm-chart"></div>
      <div ref="chartSimRef" class="qm-chart"></div>
    </div>
    <div class="qm-meta" v-if="payload?.updated_at">
      <span>更新于 {{ payload.updated_at }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getQualityMetrics } from '../api/graph'

const props = defineProps({
  projectId: { type: String, default: '' }
})

const loading = ref(false)
const error = ref('')
const payload = ref(null)
const chartGraphRef = ref(null)
const chartSimRef = ref(null)
let chartGraph = null
let chartSim = null

function disposeCharts() {
  chartGraph?.dispose()
  chartSim?.dispose()
  chartGraph = null
  chartSim = null
}

function renderCharts(data) {
  if (!data) return
  const raw = data.graph?.by_variant?.raw || {}
  const dis = data.graph?.by_variant?.disamb || {}

  if (chartGraphRef.value) {
    if (!chartGraph) chartGraph = echarts.init(chartGraphRef.value)
    chartGraph.setOption({
      title: { text: '图谱质量（节点/边）', left: 0, textStyle: { fontSize: 13 } },
      tooltip: { trigger: 'axis' },
      legend: { data: ['未消歧', '已消歧'], bottom: 0 },
      xAxis: { type: 'category', data: ['节点数', '边数'] },
      yAxis: { type: 'value' },
      series: [
        {
          name: '未消歧',
          type: 'bar',
          data: [raw.node_count || 0, raw.edge_count || 0],
          itemStyle: { color: '#94a3b8' }
        },
        {
          name: '已消歧',
          type: 'bar',
          data: [dis.node_count || 0, dis.edge_count || 0],
          itemStyle: { color: '#0f766e' }
        }
      ],
      grid: { left: 48, right: 16, top: 36, bottom: 48 }
    })
  }

  const sRaw = data.simulation?.by_variant?.raw || {}
  const sDis = data.simulation?.by_variant?.disamb || {}
  const rRaw = data.retrieval?.by_variant?.raw || {}
  const rDis = data.retrieval?.by_variant?.disamb || {}

  if (chartSimRef.value) {
    if (!chartSim) chartSim = echarts.init(chartSimRef.value)
    chartSim.setOption({
      title: { text: '仿真与检索（累计）', left: 0, textStyle: { fontSize: 13 } },
      tooltip: { trigger: 'axis' },
      legend: { data: ['未消歧', '已消歧'], bottom: 0 },
      xAxis: {
        type: 'category',
        data: ['Agent 数', '重名组数', 'search 调用', '平均命中']
      },
      yAxis: { type: 'value' },
      series: [
        {
          name: '未消歧',
          type: 'bar',
          data: [
            sRaw.agent_count || 0,
            sRaw.duplicate_display_name_groups || 0,
            rRaw.search_graph_calls || 0,
            rRaw.search_graph_avg_result_count || 0
          ],
          itemStyle: { color: '#94a3b8' }
        },
        {
          name: '已消歧',
          type: 'bar',
          data: [
            sDis.agent_count || 0,
            sDis.duplicate_display_name_groups || 0,
            rDis.search_graph_calls || 0,
            rDis.search_graph_avg_result_count || 0
          ],
          itemStyle: { color: '#0f766e' }
        }
      ],
      grid: { left: 48, right: 16, top: 36, bottom: 48 }
    })
  }
}

async function load() {
  if (!props.projectId || props.projectId === 'new') return
  loading.value = true
  error.value = ''
  try {
    const res = await getQualityMetrics(props.projectId)
    if (res.success && res.data) {
      payload.value = res.data
      await nextTick()
      renderCharts(res.data)
    } else {
      error.value = res.error || '加载失败'
    }
  } catch (e) {
    error.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

watch(
  () => props.projectId,
  (pid) => {
    if (pid && pid !== 'new') load()
    else disposeCharts()
  }
)

onMounted(() => {
  if (props.projectId && props.projectId !== 'new') load()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  disposeCharts()
})

function onResize() {
  chartGraph?.resize()
  chartSim?.resize()
}
</script>

<style scoped>
.quality-metrics-panel {
  margin-top: 16px;
  padding: 16px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
.qm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.qm-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}
.qm-refresh {
  font-size: 12px;
  padding: 8px 14px;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  cursor: pointer;
}
.qm-error {
  color: #b91c1c;
  font-size: 13px;
}
.qm-charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.qm-chart {
  min-height: 260px;
  width: 100%;
}
.qm-meta {
  margin-top: 8px;
  font-size: 11px;
  color: #6b7280;
}
@media (max-width: 900px) {
  .qm-charts {
    grid-template-columns: 1fr;
  }
}
</style>
