<template>
  <div class="demo-page">
    <!-- Navbar -->
    <nav class="demo-nav">
      <div class="nav-left">
        <div class="nav-brand">MIROFISH</div>
        <span class="nav-badge">Entity Disambiguation Showcase</span>
      </div>
      <div class="nav-right">
        <a href="https://mirofish-production-7f8c.up.railway.app/" target="_blank" class="nav-live">
          Live Demo ↗
        </a>
        <a href="https://github.com/bacxia-web/MIROFish" target="_blank" class="nav-github">
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
    </section>

    <!-- 共享展示组件：4 stat 卡 + 三组实验 -->
    <section class="section">
      <DisambiguationShowcase :compact="false" />
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
      <div class="footer-links">
        <a href="https://mirofish-production-7f8c.up.railway.app/" target="_blank" class="footer-link footer-link-primary">
          🚀 进入项目主页 →
        </a>
        <a href="https://github.com/bacxia-web/MIROFish" target="_blank" class="footer-link">
          View Source on GitHub ↗
        </a>
      </div>
    </footer>
  </div>
</template>

<script setup>
import DisambiguationShowcase from '../components/DisambiguationShowcase.vue'
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
.nav-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.nav-brand {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: #3B82F6;
}
.nav-badge {
  font-size: 12px;
  color: #64748b;
  letter-spacing: 0.05em;
}
.nav-right {
  display: flex;
  align-items: center;
  gap: 20px;
}
.nav-live {
  font-size: 13px;
  color: #3B82F6;
  text-decoration: none;
  transition: color 0.2s;
  font-weight: 500;
}
.nav-live:hover { color: #2563eb; }
.nav-github {
  font-size: 13px;
  color: #94a3b8;
  text-decoration: none;
  transition: color 0.2s;
}
.nav-github:hover { color: #3B82F6; }

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
  color: #3B82F6;
  letter-spacing: 0.1em;
  border: 1px solid #3B82F6;
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
.stat-num.teal { color: #3B82F6; }
.stat-num.orange { color: #f97316; }
.stat-label {
  font-size: 12px;
  color: #64748b;
  margin-top: 6px;
}

/* ── Section ── */
.section {
  max-width: 1400px;
  margin: 0 auto 80px;
  padding: 0 40px;
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
  color: #3B82F6;
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
  background: #3B82F620;
  color: #3B82F6;
  border: 1px solid #3B82F640;
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
.compare-col.disamb { border-color: #3B82F630; }
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
.stat-val.teal { color: #3B82F6; }
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
  color: #3B82F6;
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
.teal { color: #3B82F6; }

/* Merge list */
.merge-list {
  background: #080c14;
  border: 1px solid #3B82F630;
  border-radius: 8px;
  padding: 12px;
}
.merge-list-title {
  font-size: 11px;
  color: #3B82F6;
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
.merge-canonical { color: #3B82F6; font-weight: 600; }
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

/* CSS bar chart */
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
  width: 36px;
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
.bar-fill.disamb { background: #3B82F6; }
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
.legend-disamb { color: #3B82F6; }

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
  color: #3B82F6;
  margin-bottom: 6px;
}
.footer-sub {
  font-size: 13px;
  color: #475569;
  margin-bottom: 16px;
}
.footer-links {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.footer-link {
  font-size: 14px;
  color: #94a3b8;
  text-decoration: none;
  transition: color 0.2s;
}
.footer-link:hover { color: #3B82F6; }
.footer-link-primary {
  color: #3B82F6;
  font-weight: 600;
  font-size: 16px;
}
.footer-link-primary:hover { color: #2563eb; }

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
