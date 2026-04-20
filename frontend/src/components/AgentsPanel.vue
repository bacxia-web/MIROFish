<template>
  <div class="agents-panel">
    <!-- 加载中 -->
    <div v-if="loading" class="agents-loading">
      <span class="loading-spinner"></span>
      <span>Loading agents...</span>
    </div>

    <!-- 错误 -->
    <div v-else-if="error" class="agents-error">
      <span class="error-icon">⚠</span>
      <span>{{ error }}</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!profiles.length" class="agents-empty">
      <span class="empty-icon">◈</span>
      <span>No agent profiles found</span>
    </div>

    <!-- 人设列表 -->
    <div v-else class="agents-list">
      <div class="agents-summary">
        <span class="agents-count">{{ profiles.length }} Agents</span>
        <div class="type-badges">
          <span v-for="(count, type) in typeCounts" :key="type" class="type-badge">
            {{ type }} <em>{{ count }}</em>
          </span>
        </div>
      </div>

      <div
        v-for="profile in profiles"
        :key="profile.user_id"
        class="agent-card"
        :class="{ expanded: expandedId === profile.user_id }"
        @click="toggle(profile.user_id)"
      >
        <div class="agent-card-header">
          <div class="agent-avatar">{{ getInitial(profile.name) }}</div>
          <div class="agent-info">
            <div class="agent-name">{{ profile.name }}</div>
            <div class="agent-meta">
              <span class="agent-type">{{ profile.profession }}</span>
              <span v-if="profile.mbti" class="agent-mbti">{{ profile.mbti }}</span>
              <span v-if="profile.age" class="agent-age">{{ profile.age }}岁</span>
            </div>
          </div>
          <span class="agent-chevron">{{ expandedId === profile.user_id ? '▲' : '▼' }}</span>
        </div>

        <div v-if="expandedId === profile.user_id" class="agent-detail">
          <p class="agent-persona">{{ profile.persona || profile.bio }}</p>
          <div class="agent-tags">
            <span v-if="profile.country" class="detail-tag">📍 {{ profile.country }}</span>
            <span v-if="profile.karma" class="detail-tag">⚡ {{ profile.karma }} karma</span>
            <span v-for="topic in (profile.interested_topics || [])" :key="topic" class="detail-tag topic-tag">{{ topic }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { getSimulationProfiles } from '../api/simulation'

const props = defineProps({
  simulationId: { type: String, default: '' }
})

const loading = ref(false)
const error = ref('')
const profiles = ref([])
const expandedId = ref(null)

const typeCounts = computed(() => {
  const counts = {}
  for (const p of profiles.value) {
    const t = p.profession || 'Unknown'
    counts[t] = (counts[t] || 0) + 1
  }
  return counts
})

const getInitial = (name) => {
  if (!name) return '?'
  return name.charAt(0).toUpperCase()
}

const toggle = (id) => {
  expandedId.value = expandedId.value === id ? null : id
}

const load = async (simId) => {
  if (!simId) return
  loading.value = true
  error.value = ''
  try {
    const res = await getSimulationProfiles(simId, 'reddit')
    if (res.success && res.data?.profiles) {
      profiles.value = res.data.profiles
    } else {
      error.value = 'Failed to load profiles'
    }
  } catch (e) {
    error.value = e?.message || 'Network error'
  } finally {
    loading.value = false
  }
}

watch(() => props.simulationId, (id) => { if (id) load(id) }, { immediate: true })
</script>

<style scoped>
.agents-panel {
  height: 100%;
  overflow-y: auto;
  background: #0e1724;
  display: flex;
  flex-direction: column;
}

.agents-loading,
.agents-error,
.agents-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: 100%;
  color: #64748b;
  font-size: 13px;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #1a2a3e;
  border-top-color: #3B82F6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty-icon, .error-icon {
  font-size: 24px;
}

.agents-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.agents-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #1a2a3e;
  flex-wrap: wrap;
}

.agents-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  color: #3B82F6;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.type-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.type-badge {
  font-size: 10px;
  padding: 2px 7px;
  background: #131e2e;
  border: 1px solid #1a2a3e;
  color: #64748b;
  border-radius: 3px;
}

.type-badge em {
  font-style: normal;
  color: #e2e8f0;
  margin-left: 3px;
}

.agent-card {
  border-bottom: 1px solid #1a2a3e;
  cursor: pointer;
  transition: background 0.15s;
}

.agent-card:hover {
  background: #131e2e;
}

.agent-card.expanded {
  background: #131e2e;
}

.agent-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
}

.agent-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #1a2a3e;
  border: 1px solid #2d3a4a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: #94a3b8;
  flex-shrink: 0;
}

.agent-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-meta {
  display: flex;
  gap: 6px;
  margin-top: 2px;
  flex-wrap: wrap;
}

.agent-type {
  font-size: 10px;
  color: #3B82F6;
  font-family: 'JetBrains Mono', monospace;
}

.agent-mbti {
  font-size: 10px;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}

.agent-age {
  font-size: 10px;
  color: #64748b;
}

.agent-chevron {
  font-size: 9px;
  color: #2d3a4a;
  flex-shrink: 0;
}

.agent-detail {
  padding: 0 16px 12px 58px;
  animation: fadeIn 0.15s ease;
}

@keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }

.agent-persona {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.6;
  margin: 0 0 8px;
}

.agent-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.detail-tag {
  font-size: 10px;
  padding: 2px 6px;
  background: #0e1724;
  border: 1px solid #1a2a3e;
  color: #64748b;
  border-radius: 3px;
}

.topic-tag {
  color: #94a3b8;
}
</style>
