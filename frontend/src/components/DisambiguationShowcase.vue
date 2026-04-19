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
  font-family: 'Space Grotesk', 'JetBrains Mono', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  color: #f0f0f0;
}

/* ── Hero stats ── */
.hero-stats {
  display: flex;
  justify-content: center;
  gap: 0;
  flex-wrap: wrap;
  margin-bottom: 40px;
  border: 1px solid #1a2a3e;
}
.stat-card {
  background: #0e1724;
  border-right: 1px solid #1a2a3e;
  padding: 24px 36px;
  min-width: 140px;
  text-align: center;
  flex: 1;
}
.stat-card:last-child { border-right: none; }
.stat-num {
  font-size: 40px;
  font-weight: 700;
  color: #f0f0f0;
  line-height: 1;
  font-family: 'JetBrains Mono', monospace;
}
.stat-num.teal { color: #3B82F6; }
.stat-num.orange { color: #3B82F6; }
.stat-label {
  font-size: 11px;
  color: #9a9a9a;
  margin-top: 10px;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

/* ── Task Cards ── */
.tasks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}
.is-compact .tasks-grid {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}
.task-card {
  background: #0e1724;
  border: 1px solid #1a2a3e;
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
  font-size: 11px;
  font-weight: 700;
  background: rgba(59,130,246,0.12);
  color: #3B82F6;
  border: 1px solid rgba(59,130,246,0.4);
  padding: 3px 10px;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 1px;
}
.task-model {
  font-size: 11px;
  color: #8a8a8a;
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
  background: #0d0d0d;
  padding: 12px 10px;
  border: 1px solid #1a2a3e;
}
.compare-col.disamb {
  background: #0f0a08;
  border-color: rgba(59,130,246,0.5);
}
.compare-label {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: #a0a0a0;
  margin-bottom: 10px;
  text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
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
  color: #aaa;
  font-family: 'JetBrains Mono', monospace;
}
.stat-val.teal { color: #3B82F6; }
.stat-val.warn { color: #e53e3e; }
.stat-unit { font-size: 10px; color: #8a8a8a; }
.compare-arrow-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-shrink: 0;
  width: 52px;
}
.compare-arrow-icon { font-size: 22px; color: #3B82F6; opacity: 0.7; }
.reduction-badge {
  font-size: 11px;
  font-weight: 700;
  color: #3B82F6;
  text-align: center;
  line-height: 1.4;
  font-family: 'JetBrains Mono', monospace;
}
.reduction-sub { font-weight: 400; color: #9a9a9a; font-size: 10px; }

/* Decisions */
.decisions-row {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #0d0d0d;
  padding: 10px 12px;
  font-size: 13px;
  color: #c0c0c0;
  border: 1px solid #1a2a3e;
}
.decisions-label {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: #9a9a9a;
  flex-shrink: 0;
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  font-weight: 600;
}
.teal { color: #3B82F6; }

/* Merge list */
.merge-list {
  background: #0d0d0d;
  border: 1px solid rgba(59,130,246,0.3);
  padding: 12px;
}
.merge-list-title {
  font-size: 10px;
  color: #3B82F6;
  letter-spacing: 0.08em;
  margin-bottom: 8px;
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
}
.merge-item {
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}
.merge-removed { color: #ff7070; text-decoration: line-through; opacity: 0.75; }
.merge-arrow { color: #707070; }
.merge-canonical { color: #3B82F6; font-weight: 600; }
.merge-label-tag {
  font-size: 10px;
  background: #1a1a1a;
  color: #a0a0a0;
  border: 1px solid #1a2a3e;
  padding: 1px 6px;
  margin-left: 6px;
}
.no-merge {
  font-size: 12px;
  color: #9a9a9a;
  background: #0d0d0d;
  padding: 10px 12px;
  border: 1px dashed #1a2a3e;
}

/* Bar chart */
.bar-chart {
  background: #0d0d0d;
  padding: 14px;
  border: 1px solid #1a2a3e;
}
.bar-chart-title {
  font-size: 10px;
  color: #9a9a9a;
  letter-spacing: 0.08em;
  margin-bottom: 10px;
  text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
}
.bar-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.bar-label {
  font-size: 11px;
  color: #b0b0b0;
  width: 48px;
  flex-shrink: 0;
}
.bar-track {
  flex: 1;
  background: #14202f;
  height: 20px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  display: flex;
  align-items: center;
  padding-left: 6px;
  min-width: 24px;
  transition: width 0.6s ease;
}
.bar-fill.raw { background: #3a3a3a; }
.bar-fill.disamb { background: #3B82F6; }
.bar-val {
  font-size: 10px;
  color: #ddd;
  font-weight: 600;
  white-space: nowrap;
}
.bar-legend {
  display: flex;
  gap: 14px;
  margin-top: 8px;
  font-size: 10px;
}
.legend-raw { color: #a0a0a0; }
.legend-disamb { color: #3B82F6; }
</style>
