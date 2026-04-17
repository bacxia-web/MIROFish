<template>
  <div class="home-container">
    <!-- 顶部导航栏 -->
    <nav class="navbar">
      <div class="nav-brand">MIROFISH</div>
      <div class="nav-links">
        <a href="#showcase-section" class="nav-link">{{ $t('home.navShowcase') }}</a>
        <a href="#history-section" class="nav-link">{{ $t('home.navHistory') }}</a>
        <LanguageSwitcher />
        <a href="https://github.com/bacxia-web/MIROFish" target="_blank" class="github-link">
          {{ $t('nav.visitGithub') }} <span class="arrow">↗</span>
        </a>
      </div>
    </nav>

    <div class="main-content">
      <!-- Hero 区域 -->
      <section class="hero-section">
        <div class="hero-left">
          <div class="tag-row">
            <span class="orange-tag">{{ $t('home.tagline') }}</span>
            <span class="version-text">{{ $t('home.version') }}</span>
          </div>

          <h1 class="main-title">
            {{ $t('home.heroTitle1') }}<br>
            <span class="gradient-text">{{ $t('home.heroTitle2') }}</span>
          </h1>

          <div class="hero-desc">
            <p>
              <i18n-t keypath="home.heroDesc" tag="span">
                <template #brand><span class="highlight-bold">{{ $t('home.heroDescBrand') }}</span></template>
                <template #agentScale><span class="highlight-orange">{{ $t('home.heroDescAgentScale') }}</span></template>
                <template #optimalSolution><span class="highlight-code">{{ $t('home.heroDescOptimalSolution') }}</span></template>
              </i18n-t>
            </p>
            <p class="slogan-text">
              {{ $t('home.slogan') }}<span class="blinking-cursor">_</span>
            </p>
          </div>

          <button class="try-demo-cta" @click="showDemoModal = true">
            {{ $t('tryDemo.ctaButton') }}
          </button>
        </div>

        <div class="hero-right">
          <div class="logo-container">
            <img src="../assets/logo/MiroFish_logo_left.jpeg" alt="MiroFish Logo" class="hero-logo" />
          </div>
        </div>
      </section>

      <!-- 工作流横向条 -->
      <section class="workflow-strip-section">
        <div class="strip-header">
          <span class="diamond-icon">◇</span> {{ $t('home.workflowSequence') }}
        </div>
        <div class="strip-row">
          <div class="strip-step" v-for="(step, idx) in workflowSteps" :key="idx">
            <span class="strip-num">{{ step.num }}</span>
            <span class="strip-title">{{ $t(step.titleKey) }}</span>
            <span class="strip-arrow" v-if="idx < workflowSteps.length - 1">→</span>
          </div>
        </div>
      </section>

      <!-- 实体消歧成果（内嵌精简版）-->
      <section id="showcase-section" class="showcase-section">
        <!-- 挑战标题 -->
        <div class="challenge-header">
          <h2 class="challenge-h2">{{ $t('home.problemSectionTitle') }}</h2>
          <div class="challenge-rule"></div>
        </div>

        <!-- 三个痛点卡片 -->
        <div class="problem-cards">
          <div class="problem-card">
            <div class="problem-num">01</div>
            <div class="problem-title">{{ $t('home.problem01Title') }}</div>
            <div class="problem-desc">{{ $t('home.problem01Desc') }}</div>
          </div>
          <div class="problem-card">
            <div class="problem-num">02</div>
            <div class="problem-title">{{ $t('home.problem02Title') }}</div>
            <div class="problem-desc">{{ $t('home.problem02Desc') }}</div>
          </div>
          <div class="problem-card">
            <div class="problem-num">03</div>
            <div class="problem-title">{{ $t('home.problem03Title') }}</div>
            <div class="problem-desc">{{ $t('home.problem03Desc') }}</div>
          </div>
        </div>

        <!-- 解决方案流程条 -->
        <div class="solution-strip">
          <span class="solution-label">{{ $t('home.solutionLabel') }}</span>
          <div class="solution-flow">
            <span class="solution-step">{{ $t('home.solutionStep1') }}</span>
            <span class="solution-arrow">→</span>
            <span class="solution-step">{{ $t('home.solutionStep2') }}</span>
            <span class="solution-arrow">→</span>
            <span class="solution-step">{{ $t('home.solutionStep3') }}</span>
            <span class="solution-arrow">→</span>
            <span class="solution-step highlight">{{ $t('home.solutionStep4') }}</span>
          </div>
        </div>

        <!-- 成果标题 -->
        <div class="showcase-section-header">
          <div>
            <h2 class="showcase-h2">{{ $t('home.showcaseSectionTitle') }}</h2>
            <p class="showcase-sub">{{ $t('home.showcaseSectionDesc') }}</p>
          </div>
          <router-link :to="{ name: 'Showcase' }" class="view-full-link">
            {{ $t('home.viewFullShowcase') }}
          </router-link>
        </div>
        <DisambiguationShowcase :compact="true" />
      </section>

      <!-- 历史项目数据库 -->
      <section id="history-section">
        <HistoryDatabase />
      </section>
    </div>

    <!-- Try Demo 弹窗 -->
    <TryDemoModal v-model="showDemoModal" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'
import DisambiguationShowcase from '../components/DisambiguationShowcase.vue'
import TryDemoModal from '../components/TryDemoModal.vue'

const showDemoModal = ref(false)

const workflowSteps = [
  { num: '01', titleKey: 'home.step01Title' },
  { num: '02', titleKey: 'home.step02Title' },
  { num: '03', titleKey: 'home.step03Title' },
  { num: '04', titleKey: 'home.step04Title' },
  { num: '05', titleKey: 'home.step05Title' },
]
</script>

<style scoped>
:root {
  --black: #000000;
  --white: #FFFFFF;
  --orange: #FF4500;
  --gray-light: #141414;
  --gray-text: #888888;
  --border: #2a2a2a;
  --text-primary: #f0f0f0;
  --font-mono: 'JetBrains Mono', monospace;
  --font-sans: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
  --font-cn: 'Noto Sans SC', system-ui, sans-serif;
}

.home-container {
  min-height: 100vh;
  background: #0a0a0a;
  font-family: var(--font-sans);
  color: var(--text-primary);
}

/* 顶部导航 */
.navbar {
  height: 60px;
  background: var(--black);
  color: var(--white);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-brand {
  font-family: var(--font-mono);
  font-weight: 800;
  letter-spacing: 1px;
  font-size: 1.2rem;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 18px;
}

.nav-link {
  color: var(--white);
  text-decoration: none;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 500;
  opacity: 0.85;
  transition: all 0.15s;
}
.nav-link:hover {
  opacity: 1;
  color: var(--orange);
}

.github-link {
  color: var(--white);
  text-decoration: none;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: opacity 0.2s;
}

.github-link:hover {
  opacity: 0.8;
}

.arrow {
  font-family: sans-serif;
}

/* 主要内容 */
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 60px 40px 40px;
}

/* Hero */
.hero-section {
  display: flex;
  justify-content: space-between;
  margin-bottom: 60px;
  position: relative;
}

.hero-left {
  flex: 1;
  padding-right: 60px;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}

.orange-tag {
  background: var(--orange);
  color: var(--white);
  padding: 4px 10px;
  font-weight: 700;
  letter-spacing: 1px;
  font-size: 0.75rem;
}

.version-text {
  color: #999;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.main-title {
  font-size: 4.5rem;
  line-height: 1.2;
  font-weight: 500;
  margin: 0 0 35px 0;
  letter-spacing: -2px;
  color: var(--text-primary);
}

.gradient-text {
  background: linear-gradient(90deg, #ffffff 0%, #aaaaaa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}

.hero-desc {
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--gray-text);
  max-width: 640px;
  margin-bottom: 36px;
  font-weight: 400;
  text-align: justify;
}

.hero-desc p {
  margin-bottom: 1.2rem;
}

.highlight-bold { color: #fff; font-weight: 700; }
.highlight-orange { color: var(--orange); font-weight: 700; font-family: var(--font-mono); }
.highlight-code {
  background: rgba(255, 255, 255, 0.08);
  padding: 2px 6px;
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: 0.9em;
  color: #e0e0e0;
  font-weight: 600;
}

.slogan-text {
  font-size: 1.2rem;
  font-weight: 520;
  color: var(--text-primary);
  letter-spacing: 1px;
  border-left: 3px solid var(--orange);
  padding-left: 15px;
  margin-top: 16px;
}

.blinking-cursor {
  color: var(--orange);
  animation: blink 1s step-end infinite;
  font-weight: 700;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* Try Demo CTA 大按钮 */
.try-demo-cta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 16px 36px;
  background: var(--orange);
  color: var(--white);
  border: 1px solid var(--orange);
  font-family: var(--font-mono);
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.2s;
  animation: pulse-border 2s infinite;
}
.try-demo-cta:hover {
  background: transparent;
  border-color: var(--orange);
  color: var(--orange);
  transform: translateY(-2px);
}
.try-demo-cta:active { transform: translateY(0); }

@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(255, 69, 0, 0.4); }
  70% { box-shadow: 0 0 0 12px rgba(255, 69, 0, 0); }
  100% { box-shadow: 0 0 0 0 rgba(255, 69, 0, 0); }
}

.hero-right {
  flex: 0.8;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-end;
}

.logo-container {
  width: 100%;
  display: flex;
  justify-content: flex-end;
  padding-right: 20px;
}

.hero-logo {
  max-width: 460px;
  width: 100%;
}

/* Workflow strip */
.workflow-strip-section {
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  padding: 26px 0;
  margin-bottom: 60px;
}

.strip-header {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  color: #999;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.diamond-icon {
  font-size: 1.1rem;
  line-height: 1;
}

.strip-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 14px;
}

.strip-step {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid var(--border);
  background: #141414;
  font-family: var(--font-mono);
  transition: all 0.2s;
}
.strip-step:hover {
  border-color: var(--orange);
  background: #1e1e1e;
}
.strip-num {
  font-weight: 700;
  color: var(--orange);
  font-size: 0.85rem;
}
.strip-title {
  font-size: 0.9rem;
  color: var(--text-primary);
  font-weight: 600;
}
.strip-arrow {
  color: #bbb;
  font-size: 1rem;
  margin-left: 4px;
}

/* Showcase section */
.showcase-section {
  margin-bottom: 70px;
}

/* 挑战标题 */
.challenge-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 28px;
}
.challenge-h2 {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0;
  font-family: var(--font-mono);
  letter-spacing: 1px;
  color: var(--text-primary);
  white-space: nowrap;
  text-transform: uppercase;
}
.challenge-rule {
  flex: 1;
  height: 1px;
  background: var(--border);
}

/* 三痛点卡片 */
.problem-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.problem-card {
  border: 1px solid var(--border);
  padding: 22px 20px;
  background: var(--gray-light);
}
.problem-num {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--orange);
  margin-bottom: 10px;
  letter-spacing: 1px;
}
.problem-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
  line-height: 1.4;
}
.problem-desc {
  font-size: 0.85rem;
  color: var(--gray-text);
  line-height: 1.6;
}

/* 解决方案流程条 */
.solution-strip {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border: 1px solid var(--black);
  background: var(--black);
  margin-bottom: 48px;
  flex-wrap: wrap;
}
.solution-label {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
  color: #888;
  letter-spacing: 1px;
  white-space: nowrap;
  flex-shrink: 0;
}
.solution-flow {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.solution-step {
  font-family: var(--font-mono);
  font-size: 0.82rem;
  font-weight: 500;
  color: #ccc;
  white-space: nowrap;
}
.solution-step.highlight {
  color: var(--orange);
  font-weight: 700;
}
.solution-arrow {
  color: #555;
  font-size: 0.9rem;
}

.showcase-section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 28px;
  gap: 24px;
  flex-wrap: wrap;
}

.showcase-h2 {
  font-size: 1.9rem;
  font-weight: 600;
  margin: 0 0 6px;
  letter-spacing: -0.5px;
  color: var(--text-primary);
}

.showcase-sub {
  margin: 0;
  color: var(--gray-text);
  font-size: 0.95rem;
  line-height: 1.5;
}

.view-full-link {
  font-family: var(--font-mono);
  font-size: 0.88rem;
  color: var(--orange);
  text-decoration: none;
  font-weight: 600;
  border: 1px solid var(--orange);
  padding: 8px 16px;
  transition: all 0.2s;
  white-space: nowrap;
}
.view-full-link:hover {
  background: var(--orange);
  color: var(--white);
}

/* 响应式适配 */
@media (max-width: 1024px) {
  .hero-section { flex-direction: column; }
  .hero-left { padding-right: 0; margin-bottom: 40px; }
  .logo-container { justify-content: flex-start; padding-right: 0; }
  .hero-logo { max-width: 280px; }
  .main-title { font-size: 3rem; }
  .strip-row { gap: 8px; }
  .strip-step { padding: 6px 10px; }
  .strip-arrow { display: none; }
  .showcase-section-header { flex-direction: column; align-items: flex-start; }
  .problem-cards { grid-template-columns: 1fr; }
  .solution-strip { flex-direction: column; align-items: flex-start; gap: 10px; }
}
</style>

<style>
/* English locale adjustments (unscoped to target html[lang]) */
html[lang="en"] .main-title {
  font-size: 3.5rem;
  font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  letter-spacing: -1px;
}

html[lang="en"] .hero-desc {
  text-align: left;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  letter-spacing: 0;
}

html[lang="en"] .slogan-text {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  letter-spacing: 0;
}

html[lang="en"] .tag-row {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

html[lang="en"] .navbar .nav-links {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
</style>
