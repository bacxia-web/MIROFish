<template>
  <div class="demo-page">
    <!-- Navbar -->
    <nav class="demo-nav">
      <div class="nav-brand">MIROFISH</div>
      <div class="nav-right">
        <span class="nav-badge">Entity Disambiguation Showcase</span>
        <a href="https://github.com/666ghj/MiroFish" target="_blank" class="nav-github">
          GitHub ↗
        </a>
      </div>
    </nav>

    <!-- Hero -->
    <section class="hero">
      <div class="hero-tag">Knowledge Graph · 图谱构建</div>
      <h1 class="hero-title">
        实体消歧效果展示
        <span class="hero-title-en">Entity Disambiguation</span>
      </h1>
      <p class="hero-desc">
        MiroFish 在构建仿真世界的知识图谱时，通过 LLM 对候选实体对进行语义判断，
        识别并合并指向同一真实实体的冗余节点，显著提升图谱质量与后续检索效率。
      </p>
      <div class="hero-stats">
        <div class="stat-card">
          <div class="stat-num">3</div>
          <div class="stat-label">评测任务</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">17</div>
          <div class="stat-label">LLM 判定对数</div>
        </div>
        <div class="stat-card">
          <div class="stat-num teal">52%</div>
          <div class="stat-label">平均节点压缩率</div>
        </div>
        <div class="stat-card">
          <div class="stat-num orange">100%</div>
          <div class="stat-label">重名 Agent 消除率</div>
        </div>
      </div>
    </section>

    <!-- How it works -->
    <section class="section">
      <h2 class="section-title">工作原理</h2>
      <div class="pipeline-steps">
        <div class="pipeline-step">
          <div class="step-icon">📄</div>
          <div class="step-label">Step 1</div>
          <div class="step-desc">从种子文档中提取实体，构建原始图谱（Raw Graph）</div>
        </div>
        <div class="pipeline-arrow">→</div>
        <div class="pipeline-step">
          <div class="step-icon">🤖</div>
          <div class="step-label">LLM 判定</div>
          <div class="step-desc">对候选实体对逐一判断：是否指向同一真实实体？</div>
        </div>
        <div class="pipeline-arrow">→</div>
        <div class="pipeline-step">
          <div class="step-icon">🔀</div>
          <div class="step-label">合并</div>
          <div class="step-desc">确认为同一实体则合并节点，保留规范名称</div>
        </div>
        <div class="pipeline-arrow">→</div>
        <div class="pipeline-step">
          <div class="step-icon">✨</div>
          <div class="step-label">消歧图谱</div>
          <div class="step-desc">得到更精简、密度更高的 Disambiguated Graph</div>
        </div>
      </div>
    </section>

    <!-- Task Results -->
    <section class="section">
      <h2 class="section-title">三组实验结果</h2>
      <div class="tasks-grid">
        <div v-for="task in tasks" :key="task.index" class="task-card">
          <div class="task-header">
            <span class="task-badge">Task {{ task.index }}</span>
            <span class="task-model">{{ task.model }}</span>
          </div>

          <!-- Graph stats before/after -->
          <div class="compare-row">
            <div class="compare-col raw">
              <div class="compare-label">消歧前 Raw</div>
              <div class="compare-stat">
                <span class="stat-val">{{ task.raw.nodes }}</span>
                <span class="stat-unit">节点</span>
              </div>
              <div class="compare-stat">
                <span class="stat-val">{{ task.raw.edges }}</span>
                <span class="stat-unit">边</span>
              </div>
              <div class="compare-stat">
                <span class="stat-val">{{ (task.raw.isolatedRatio * 100).toFixed(1) }}%</span>
                <span class="stat-unit">孤立节点率</span>
              </div>
              <div class="compare-stat">
                <span class="stat-val">{{ task.raw.avgDegree.toFixed(2) }}</span>
                <span class="stat-unit">平均度</span>
              </div>
              <div class="compare-stat duplicate">
                <span class="stat-val warn">{{ task.raw.duplicateGroups }}</span>
                <span class="stat-unit">重名 Agent 组</span>
              </div>
            </div>
            <div class="compare-arrow-col">
              <div class="compare-arrow-icon">⟹</div>
              <div class="reduction-badge">
                -{{ (task.nodeReductionRatio * 100).toFixed(1) }}%<br>
                <span class="reduction-sub">节点压缩</span>
              </div>
            </div>
            <div class="compare-col disamb">
              <div class="compare-label">消歧后 Disamb</div>
              <div class="compare-stat">
                <span class="stat-val teal">{{ task.disamb.nodes }}</span>
                <span class="stat-unit">节点</span>
              </div>
              <div class="compare-stat">
                <span class="stat-val teal">{{ task.disamb.edges }}</span>
                <span class="stat-unit">边</span>
              </div>
              <div class="compare-stat">
                <span class="stat-val teal">{{ (task.disamb.isolatedRatio * 100).toFixed(1) }}%</span>
                <span class="stat-unit">孤立节点率</span>
              </div>
              <div class="compare-stat">
                <span class="stat-val teal">{{ task.disamb.avgDegree.toFixed(2) }}</span>
                <span class="stat-unit">平均度</span>
              </div>
              <div class="compare-stat duplicate">
                <span class="stat-val teal">0</span>
                <span class="stat-unit">重名 Agent 组</span>
              </div>
            </div>
          </div>

          <!-- LLM decisions -->
          <div class="decisions-row">
            <div class="decisions-label">LLM 判定</div>
            <div class="decisions-detail">
              共 <strong>{{ task.pairDecisions }}</strong> 对候选，
              合并 <strong class="teal">{{ task.mergedGroups }}</strong> 组
            </div>
          </div>

          <!-- Merge detail if any -->
          <div v-if="task.merges.length > 0" class="merge-list">
            <div class="merge-list-title">合并详情</div>
            <div v-for="m in task.merges" :key="m.kept" class="merge-item">
              <span class="merge-removed">{{ m.removed.join(' / ') }}</span>
              <span class="merge-arrow"> → </span>
              <span class="merge-canonical">{{ m.canonical }}</span>
              <span class="merge-label-tag">{{ m.label }}</span>
            </div>
          </div>
          <div v-else class="no-merge">所有候选对均判定为不同实体，无合并（精准保守策略）</div>

          <!-- Chart -->
          <div :ref="el => { if(el) chartRefs[task.index] = el }" class="task-chart"></div>
        </div>
      </div>
    </section>

    <!-- Retrieval A/B Section -->
    <section class="section">
      <h2 class="section-title">检索质量 A/B 对比</h2>
      <p class="section-sub">消歧后图谱在 Agent 仿真过程中的 GraphRAG 检索表现对比（natural_traffic 模式）</p>
      <div class="ab-grid">
        <div v-for="task in tasks" :key="'ab' + task.index" class="ab-card">
          <div class="ab-task-label">Task {{ task.index }}</div>
          <div class="ab-row">
            <div class="ab-col">
              <div class="ab-col-label raw">Raw</div>
              <div class="ab-stat">
                <span class="ab-val">{{ task.retrieval.raw.calls }}</span>
                <span class="ab-unit">search 调用</span>
              </div>
              <div class="ab-stat">
                <span class="ab-val warn">{{ task.retrieval.raw.emptyCalls }}</span>
                <span class="ab-unit">空结果次数</span>
              </div>
              <div class="ab-stat">
                <span class="ab-val">{{ task.retrieval.raw.emptyRate }}</span>
                <span class="ab-unit">空结果率</span>
              </div>
            </div>
            <div class="ab-divider">vs</div>
            <div class="ab-col">
              <div class="ab-col-label disamb">Disamb</div>
              <div class="ab-stat">
                <span class="ab-val teal">{{ task.retrieval.disamb.calls }}</span>
                <span class="ab-unit">search 调用</span>
              </div>
              <div class="ab-stat">
                <span class="ab-val" :class="task.retrieval.deltaEmptyCalls < 0 ? 'teal' : (task.retrieval.deltaEmptyCalls > 0 ? 'warn' : '')">
                  {{ task.retrieval.disamb.emptyCalls }}
                </span>
                <span class="ab-unit">空结果次数</span>
              </div>
              <div class="ab-stat">
                <span class="ab-val" :class="task.retrieval.disamb.emptyRateNum < task.retrieval.raw.emptyRateNum ? 'teal' : ''">
                  {{ task.retrieval.disamb.emptyRate }}
                </span>
                <span class="ab-unit">空结果率</span>
              </div>
            </div>
          </div>
          <div class="ab-delta" :class="task.retrieval.deltaEmptyCalls < 0 ? 'delta-good' : (task.retrieval.deltaEmptyCalls > 0 ? 'delta-bad' : 'delta-neutral')">
            空结果变化：{{ task.retrieval.deltaEmptyCalls > 0 ? '+' : '' }}{{ task.retrieval.deltaEmptyCalls }}
          </div>
        </div>
      </div>
    </section>

    <!-- Tech Stack -->
    <section class="section tech-section">
      <h2 class="section-title">技术栈</h2>
      <div class="tech-tags">
        <span class="tech-tag">Python 3.11</span>
        <span class="tech-tag">Flask 3.0</span>
        <span class="tech-tag">Vue 3</span>
        <span class="tech-tag">Zep Memory Graph</span>
        <span class="tech-tag">GraphRAG</span>
        <span class="tech-tag">HDBSCAN</span>
        <span class="tech-tag">qwen3-max</span>
        <span class="tech-tag">ECharts</span>
        <span class="tech-tag">D3.js</span>
        <span class="tech-tag">Docker</span>
      </div>
    </section>

    <!-- Footer -->
    <footer class="demo-footer">
      <div class="footer-brand">MIROFISH</div>
      <div class="footer-sub">Multi-Agent Swarm Intelligence Simulation Engine</div>
      <a href="https://github.com/666ghj/MiroFish" target="_blank" class="footer-link">
        View Source on GitHub ↗
      </a>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

// ── Static demo data ────────────────────────────────────────────────────────
const tasks = [
  {
    index: 1,
    model: 'qwen3-max-preview',
    nodeReductionRatio: 0.688312,
    pairDecisions: 6,
    mergedGroups: 0,
    merges: [],
    raw:    { nodes: 77,  edges: 70,  isolatedRatio: 0.25974,  avgDegree: 1.8182,  duplicateGroups: 4 },
    disamb: { nodes: 24,  edges: 121, isolatedRatio: 0.041667, avgDegree: 10.083,  duplicateGroups: 0 },
    retrieval: {
      raw:    { calls: 183, emptyCalls: 25,  emptyRate: '13.7%', emptyRateNum: 0.137 },
      disamb: { calls: 85,  emptyCalls: 36,  emptyRate: '42.4%', emptyRateNum: 0.424 },
      deltaEmptyCalls: -11,
    },
  },
  {
    index: 2,
    model: 'qwen3-coder-flash',
    nodeReductionRatio: 0.488372,
    pairDecisions: 9,
    mergedGroups: 1,
    merges: [
      { canonical: '吴泽明', removed: ['范禹'], kept: '7e0411f1', label: 'Person' },
    ],
    raw:    { nodes: 43,  edges: 52,  isolatedRatio: 0.046512, avgDegree: 2.4186, duplicateGroups: 2 },
    disamb: { nodes: 22,  edges: 45,  isolatedRatio: 0.0,      avgDegree: 4.0909, duplicateGroups: 0 },
    retrieval: {
      raw:    { calls: 202, emptyCalls: 27,  emptyRate: '13.4%', emptyRateNum: 0.134 },
      disamb: { calls: 131, emptyCalls: 120, emptyRate: '91.6%', emptyRateNum: 0.916 },
      deltaEmptyCalls: -93,
    },
  },
  {
    index: 3,
    model: 'qwen3-coder-flash',
    nodeReductionRatio: 0.388889,
    pairDecisions: 2,
    mergedGroups: 0,
    merges: [],
    raw:    { nodes: 18, edges: 21, isolatedRatio: 0.111111, avgDegree: 2.3333, duplicateGroups: 1 },
    disamb: { nodes: 11, edges: 13, isolatedRatio: 0.0,      avgDegree: 2.3636, duplicateGroups: 0 },
    retrieval: {
      raw:    { calls: 57, emptyCalls: 32, emptyRate: '56.1%', emptyRateNum: 0.561 },
      disamb: { calls: 43, emptyCalls: 32, emptyRate: '74.4%', emptyRateNum: 0.744 },
      deltaEmptyCalls: 0,
    },
  },
]

// ── ECharts ─────────────────────────────────────────────────────────────────
const chartRefs = ref({})
const chartInstances = []

function buildChartOption(task) {
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: {
      data: ['消歧前 Raw', '消歧后 Disamb'],
      textStyle: { color: '#94a3b8' },
      bottom: 0,
    },
    grid: { left: 48, right: 12, top: 32, bottom: 44 },
    xAxis: {
      type: 'category',
      data: ['节点数', '边数', '平均度'],
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      axisLine: { lineStyle: { color: '#334155' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#1e293b' } },
    },
    series: [
      {
        name: '消歧前 Raw',
        type: 'bar',
        barMaxWidth: 32,
        data: [task.raw.nodes, task.raw.edges, task.raw.avgDegree],
        itemStyle: { color: '#475569', borderRadius: [3, 3, 0, 0] },
      },
      {
        name: '消歧后 Disamb',
        type: 'bar',
        barMaxWidth: 32,
        data: [task.disamb.nodes, task.disamb.edges, task.disamb.avgDegree],
        itemStyle: { color: '#14b8a6', borderRadius: [3, 3, 0, 0] },
      },
    ],
  }
}

onMounted(() => {
  tasks.forEach(task => {
    const el = chartRefs.value[task.index]
    if (!el) return
    const chart = echarts.init(el, null, { renderer: 'canvas' })
    chart.setOption(buildChartOption(task))
    chartInstances.push(chart)
  })
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  chartInstances.forEach(c => c.dispose())
})

function resizeCharts() {
  chartInstances.forEach(c => c.resize())
}
</script>

<style scoped>
/* ── Base ── */
.demo-page {
  min-height: 100vh;
  background: #080c14;
  color: #e2e8f0;
  font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ── Navbar ── */
.demo-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 40px;
  border-bottom: 1px solid #1e293b;
  position: sticky;
  top: 0;
  background: rgba(8, 12, 20, 0.92);
  backdrop-filter: blur(12px);
  z-index: 100;
}
.nav-brand {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: #14b8a6;
}
.nav-right {
  display: flex;
  align-items: center;
  gap: 20px;
}
.nav-badge {
  font-size: 12px;
  color: #64748b;
  letter-spacing: 0.05em;
}
.nav-github {
  font-size: 13px;
  color: #94a3b8;
  text-decoration: none;
  transition: color 0.2s;
}
.nav-github:hover { color: #14b8a6; }

/* ── Hero ── */
.hero {
  max-width: 900px;
  margin: 80px auto 0;
  padding: 0 24px;
  text-align: center;
}
.hero-tag {
  display: inline-block;
  font-size: 12px;
  color: #14b8a6;
  letter-spacing: 0.1em;
  border: 1px solid #14b8a6;
  border-radius: 4px;
  padding: 3px 10px;
  margin-bottom: 20px;
}
.hero-title {
  font-size: clamp(32px, 5vw, 52px);
  font-weight: 700;
  line-height: 1.2;
  margin: 0 0 8px;
  color: #f8fafc;
}
.hero-title-en {
  display: block;
  font-size: clamp(16px, 2.5vw, 24px);
  font-weight: 400;
  color: #64748b;
  letter-spacing: 0.05em;
  margin-top: 6px;
}
.hero-desc {
  font-size: 15px;
  line-height: 1.8;
  color: #94a3b8;
  max-width: 700px;
  margin: 24px auto 48px;
}
.hero-stats {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 80px;
}
.stat-card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 20px 32px;
  min-width: 110px;
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

/* ── Section ── */
.section {
  max-width: 1100px;
  margin: 0 auto 80px;
  padding: 0 24px;
}
.section-title {
  font-size: 22px;
  font-weight: 600;
  color: #f8fafc;
  margin: 0 0 8px;
  padding-bottom: 12px;
  border-bottom: 1px solid #1e293b;
}
.section-sub {
  font-size: 13px;
  color: #64748b;
  margin: 8px 0 24px;
}

/* ── Pipeline ── */
.pipeline-steps {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 28px;
}
.pipeline-step {
  flex: 1;
  min-width: 160px;
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 10px;
  padding: 20px 16px;
  text-align: center;
}
.step-icon { font-size: 28px; margin-bottom: 8px; }
.step-label {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: #14b8a6;
  font-weight: 600;
  margin-bottom: 6px;
}
.step-desc { font-size: 12px; color: #94a3b8; line-height: 1.6; }
.pipeline-arrow {
  font-size: 20px;
  color: #334155;
  flex-shrink: 0;
}

/* ── Task Cards ── */
.tasks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 28px;
}
.task-card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
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

/* Chart */
.task-chart {
  height: 180px;
  width: 100%;
}

/* ── A/B Grid ── */
.ab-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  margin-top: 24px;
}
.ab-card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 20px;
}
.ab-task-label {
  font-size: 12px;
  font-weight: 600;
  color: #14b8a6;
  letter-spacing: 0.06em;
  margin-bottom: 14px;
}
.ab-row {
  display: flex;
  align-items: stretch;
  gap: 8px;
}
.ab-col {
  flex: 1;
  background: #080c14;
  border-radius: 8px;
  padding: 10px;
}
.ab-col-label {
  font-size: 10px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.ab-col-label.raw { color: #64748b; }
.ab-col-label.disamb { color: #14b8a6; }
.ab-stat {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 6px;
}
.ab-val { font-size: 15px; font-weight: 600; color: #cbd5e1; }
.ab-val.teal { color: #14b8a6; }
.ab-val.warn { color: #f97316; }
.ab-unit { font-size: 10px; color: #475569; }
.ab-divider {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #334155;
  flex-shrink: 0;
  padding: 0 2px;
}
.ab-delta {
  margin-top: 12px;
  font-size: 12px;
  text-align: center;
  padding: 6px;
  border-radius: 6px;
}
.delta-good { background: #14b8a610; color: #14b8a6; }
.delta-bad  { background: #f9731610; color: #f97316; }
.delta-neutral { background: #1e293b; color: #64748b; }

/* ── Tech ── */
.tech-section { margin-bottom: 60px; }
.tech-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 20px;
}
.tech-tag {
  font-size: 13px;
  background: #0f172a;
  border: 1px solid #1e293b;
  color: #94a3b8;
  border-radius: 6px;
  padding: 6px 14px;
}

/* ── Footer ── */
.demo-footer {
  border-top: 1px solid #1e293b;
  padding: 40px 24px;
  text-align: center;
  background: #080c14;
}
.footer-brand {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: #14b8a6;
  margin-bottom: 6px;
}
.footer-sub {
  font-size: 13px;
  color: #475569;
  margin-bottom: 16px;
}
.footer-link {
  font-size: 14px;
  color: #94a3b8;
  text-decoration: none;
  transition: color 0.2s;
}
.footer-link:hover { color: #14b8a6; }

/* ── Responsive ── */
@media (max-width: 640px) {
  .demo-nav { padding: 12px 16px; }
  .hero { margin-top: 40px; }
  .pipeline-steps { flex-direction: column; }
  .pipeline-arrow { transform: rotate(90deg); }
  .compare-row { flex-direction: column; }
  .compare-arrow-col { flex-direction: row; width: 100%; justify-content: center; }
}
</style>
