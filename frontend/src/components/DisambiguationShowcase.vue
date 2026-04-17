<template>
  <div class="disamb-showcase" :class="{ 'is-compact': compact }">
    <!-- 4 hero stats -->
    <div class="hero-stats">
      <div class="stat-card">
        <div class="stat-num">{{ summary.taskCount }}</div>
        <div class="stat-label">{{ $t('showcase.statTasks') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ summary.pairDecisionsTotal }}</div>
        <div class="stat-label">{{ $t('showcase.statDecisions') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num teal">{{ summary.avgNodeCompressionPercent }}%</div>
        <div class="stat-label">{{ $t('showcase.statCompression') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num orange">{{ summary.duplicateEliminationRate }}%</div>
        <div class="stat-label">{{ $t('showcase.statDupElim') }}</div>
      </div>
    </div>

    <!-- 3 task results -->
    <div class="tasks-grid">
      <div v-for="task in tasks" :key="task.index" class="task-card">
        <div class="task-header">
          <span class="task-badge">Task {{ task.index }}</span>
          <span class="task-model">{{ task.model }}</span>
        </div>

        <div class="compare-row">
          <div class="compare-col raw">
            <div class="compare-label">{{ $t('showcase.beforeRaw') }}</div>
            <div class="compare-stat">
              <span class="stat-val">{{ task.raw.nodes }}</span>
              <span class="stat-unit">{{ $t('showcase.nodes') }}</span>
            </div>
            <div class="compare-stat">
              <span class="stat-val">{{ task.raw.edges }}</span>
              <span class="stat-unit">{{ $t('showcase.edges') }}</span>
            </div>
            <div class="compare-stat">
              <span class="stat-val">{{ (task.raw.isolatedRatio * 100).toFixed(1) }}%</span>
              <span class="stat-unit">{{ $t('showcase.isolatedRatio') }}</span>
            </div>
            <div class="compare-stat">
              <span class="stat-val">{{ task.raw.avgDegree.toFixed(2) }}</span>
              <span class="stat-unit">{{ $t('showcase.avgDegree') }}</span>
            </div>
            <div class="compare-stat duplicate">
              <span class="stat-val warn">{{ task.raw.duplicateGroups }}</span>
              <span class="stat-unit">{{ $t('showcase.dupGroups') }}</span>
            </div>
          </div>
          <div class="compare-arrow-col">
            <div class="compare-arrow-icon">⟹</div>
            <div class="reduction-badge">
              -{{ (task.nodeReductionRatio * 100).toFixed(1) }}%<br>
              <span class="reduction-sub">{{ $t('showcase.nodeReduction') }}</span>
            </div>
          </div>
          <div class="compare-col disamb">
            <div class="compare-label">{{ $t('showcase.afterDisamb') }}</div>
            <div class="compare-stat">
              <span class="stat-val teal">{{ task.disamb.nodes }}</span>
              <span class="stat-unit">{{ $t('showcase.nodes') }}</span>
            </div>
            <div class="compare-stat">
              <span class="stat-val teal">{{ task.disamb.edges }}</span>
              <span class="stat-unit">{{ $t('showcase.edges') }}</span>
            </div>
            <div class="compare-stat">
              <span class="stat-val teal">{{ (task.disamb.isolatedRatio * 100).toFixed(1) }}%</span>
              <span class="stat-unit">{{ $t('showcase.isolatedRatio') }}</span>
            </div>
            <div class="compare-stat">
              <span class="stat-val teal">{{ task.disamb.avgDegree.toFixed(2) }}</span>
              <span class="stat-unit">{{ $t('showcase.avgDegree') }}</span>
            </div>
            <div class="compare-stat duplicate">
              <span class="stat-val teal">0</span>
              <span class="stat-unit">{{ $t('showcase.dupGroups') }}</span>
            </div>
          </div>
        </div>

        <div class="decisions-row">
          <div class="decisions-label">{{ $t('showcase.llmDecisions') }}</div>
          <div class="decisions-detail">
            <i18n-t keypath="showcase.decisionsSummary" tag="span">
              <template #total><strong>{{ task.pairDecisions }}</strong></template>
              <template #merged><strong class="teal">{{ task.mergedGroups }}</strong></template>
            </i18n-t>
          </div>
        </div>

        <div v-if="task.merges.length > 0" class="merge-list">
          <div class="merge-list-title">{{ $t('showcase.mergeDetail') }}</div>
          <div v-for="m in task.merges" :key="m.kept" class="merge-item">
            <span class="merge-removed">{{ m.removed.join(' / ') }}</span>
            <span class="merge-arrow"> → </span>
            <span class="merge-canonical">{{ m.canonical }}</span>
            <span class="merge-label-tag">{{ m.label }}</span>
          </div>
        </div>
        <div v-else class="no-merge">{{ $t('showcase.noMerge') }}</div>

        <!-- 完整版才显示 bar chart -->
        <div v-if="!compact" class="bar-chart">
          <div class="bar-chart-title">{{ $t('showcase.barChartTitle') }}</div>
          <div v-for="metric in taskMetrics(task)" :key="metric.label" class="bar-row">
            <div class="bar-label">{{ metric.label }}</div>
            <div class="bar-track">
              <div class="bar-fill raw" :style="{ width: metric.rawPct + '%' }">
                <span class="bar-val">{{ metric.rawVal }}</span>
              </div>
            </div>
            <div class="bar-track">
              <div class="bar-fill disamb" :style="{ width: metric.disambPct + '%' }">
                <span class="bar-val">{{ metric.disambVal }}</span>
              </div>
            </div>
          </div>
          <div class="bar-legend">
            <span class="legend-raw">■ {{ $t('showcase.legendRaw') }}</span>
            <span class="legend-disamb">■ {{ $t('showcase.legendDisamb') }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { tasks, summary } from '../constants/disambiguationTasks.js'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps({
  compact: { type: Boolean, default: false },
})

function taskMetrics(task) {
  const maxNodes = 77, maxEdges = 121, maxDeg = 10.083
  return [
    {
      label: t('showcase.metricNodes'),
      rawVal: task.raw.nodes,
      disambVal: task.disamb.nodes,
      rawPct: Math.round(task.raw.nodes / maxNodes * 100),
      disambPct: Math.round(task.disamb.nodes / maxNodes * 100),
    },
    {
      label: t('showcase.metricEdges'),
      rawVal: task.raw.edges,
      disambVal: task.disamb.edges,
      rawPct: Math.round(task.raw.edges / maxEdges * 100),
      disambPct: Math.round(task.disamb.edges / maxEdges * 100),
    },
    {
      label: t('showcase.metricAvgDegree'),
      rawVal: task.raw.avgDegree.toFixed(2),
      disambVal: task.disamb.avgDegree.toFixed(2),
      rawPct: Math.round(task.raw.avgDegree / maxDeg * 100),
      disambPct: Math.round(task.disamb.avgDegree / maxDeg * 100),
    },
  ]
}
</script>

<style scoped>
.disamb-showcase {
  font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  color: #e2e8f0;
}

/* ── Hero stats ── */
.hero-stats {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 48px;
}
.stat-card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 20px 32px;
  min-width: 110px;
  text-align: center;
}
.stat-num {
  font-size: 36px;
  font-weight: 700;
  color: #f8fafc;
  line-height: 1;
}
.stat-num.teal { color: #14b8a6; }
.stat-num.orange { color: #f97316; }
.stat-label {
  font-size: 12px;
  color: #64748b;
  margin-top: 6px;
}

/* ── Task Cards ── */
.tasks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}
.is-compact .tasks-grid {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}
.task-card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.task-badge {
  font-size: 12px;
  font-weight: 600;
  background: #14b8a620;
  color: #14b8a6;
  border: 1px solid #14b8a640;
  border-radius: 6px;
  padding: 3px 10px;
}
.task-model {
  font-size: 11px;
  color: #475569;
  font-family: monospace;
}

/* Compare columns */
.compare-row {
  display: flex;
  gap: 8px;
  align-items: stretch;
}
.compare-col {
  flex: 1;
  background: #080c14;
  border-radius: 8px;
  padding: 12px 10px;
  border: 1px solid #1e293b;
}
.compare-col.disamb { border-color: #14b8a630; }
.compare-label {
  font-size: 10px;
  letter-spacing: 0.06em;
  color: #64748b;
  margin-bottom: 10px;
  text-transform: uppercase;
}
.compare-stat {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 6px;
}
.stat-val {
  font-size: 16px;
  font-weight: 600;
  color: #cbd5e1;
}
.stat-val.teal { color: #14b8a6; }
.stat-val.warn { color: #f97316; }
.stat-unit { font-size: 10px; color: #475569; }
.compare-arrow-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-shrink: 0;
  width: 52px;
}
.compare-arrow-icon { font-size: 20px; color: #334155; }
.reduction-badge {
  font-size: 11px;
  font-weight: 600;
  color: #14b8a6;
  text-align: center;
  line-height: 1.4;
}
.reduction-sub { font-weight: 400; color: #475569; }

/* Decisions */
.decisions-row {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #080c14;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  color: #64748b;
}
.decisions-label {
  font-size: 11px;
  letter-spacing: 0.06em;
  color: #475569;
  flex-shrink: 0;
}
.teal { color: #14b8a6; }

/* Merge list */
.merge-list {
  background: #080c14;
  border: 1px solid #14b8a630;
  border-radius: 8px;
  padding: 12px;
}
.merge-list-title {
  font-size: 11px;
  color: #14b8a6;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}
.merge-item {
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}
.merge-removed { color: #f97316; text-decoration: line-through; opacity: 0.7; }
.merge-arrow { color: #475569; }
.merge-canonical { color: #14b8a6; font-weight: 600; }
.merge-label-tag {
  font-size: 10px;
  background: #1e293b;
  color: #64748b;
  border-radius: 4px;
  padding: 1px 6px;
  margin-left: 6px;
}
.no-merge {
  font-size: 12px;
  color: #475569;
  background: #080c14;
  border-radius: 8px;
  padding: 10px 12px;
  border: 1px dashed #1e293b;
}

/* Bar chart */
.bar-chart {
  background: #080c14;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #1e293b;
}
.bar-chart-title {
  font-size: 11px;
  color: #475569;
  letter-spacing: 0.06em;
  margin-bottom: 10px;
}
.bar-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.bar-label {
  font-size: 11px;
  color: #64748b;
  width: 48px;
  flex-shrink: 0;
}
.bar-track {
  flex: 1;
  background: #1e293b;
  border-radius: 3px;
  height: 20px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 3px;
  display: flex;
  align-items: center;
  padding-left: 6px;
  min-width: 24px;
  transition: width 0.6s ease;
}
.bar-fill.raw { background: #475569; }
.bar-fill.disamb { background: #14b8a6; }
.bar-val {
  font-size: 10px;
  color: #f8fafc;
  font-weight: 600;
  white-space: nowrap;
}
.bar-legend {
  display: flex;
  gap: 14px;
  margin-top: 8px;
  font-size: 10px;
}
.legend-raw { color: #64748b; }
.legend-disamb { color: #14b8a6; }
</style>
