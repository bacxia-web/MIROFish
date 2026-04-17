<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modelValue" class="modal-mask" @click.self="close" @keydown.esc="close" tabindex="-1">
        <div class="modal-card" role="dialog" aria-modal="true">
          <button class="modal-close" type="button" @click="close" aria-label="Close">×</button>

          <div class="modal-notice">
            ⚠ {{ $t('tryDemo.notice') }}
          </div>

          <h2 class="modal-title">{{ $t('tryDemo.title') }}</h2>

          <div class="console-box">
            <!-- 上传区 -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">{{ $t('home.realitySeed') }}</span>
                <span class="console-meta">{{ $t('home.supportedFormats') }}</span>
              </div>

              <div
                class="upload-zone"
                :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
                @dragover.prevent="handleDragOver"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input
                  ref="fileInput"
                  type="file"
                  multiple
                  accept=".pdf,.md,.txt"
                  @change="handleFileSelect"
                  style="display: none"
                  :disabled="loading"
                />

                <div v-if="files.length === 0" class="upload-placeholder">
                  <div class="upload-icon">↑</div>
                  <div class="upload-title">{{ $t('home.dragToUpload') }}</div>
                  <div class="upload-hint">{{ $t('home.orBrowse') }}</div>
                </div>

                <div v-else class="file-list">
                  <div v-for="(file, index) in files" :key="index" class="file-item">
                    <span class="file-icon">📄</span>
                    <span class="file-name">{{ file.name }}</span>
                    <button @click.stop="removeFile(index)" class="remove-btn">×</button>
                  </div>
                </div>
              </div>
            </div>

            <div class="console-divider">
              <span>{{ $t('home.inputParams') }}</span>
            </div>

            <!-- 输入区 -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">{{ $t('home.simulationPrompt') }}</span>
              </div>
              <div class="input-wrapper">
                <textarea
                  v-model="simulationRequirement"
                  class="code-input"
                  :placeholder="$t('home.promptPlaceholder')"
                  rows="6"
                  :disabled="loading"
                ></textarea>
                <div class="model-badge">{{ $t('home.engineBadge') }}</div>
              </div>
            </div>

            <!-- 启动 -->
            <div class="console-section btn-section">
              <button
                class="start-engine-btn"
                @click="startSimulation"
                :disabled="!canSubmit || loading"
              >
                <span v-if="!loading">{{ $t('home.startEngine') }}</span>
                <span v-else>{{ $t('home.initializing') }}</span>
                <span class="btn-arrow">→</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const router = useRouter()

const files = ref([])
const simulationRequirement = ref('')
const loading = ref(false)
const isDragOver = ref(false)
const fileInput = ref(null)

const canSubmit = computed(
  () => simulationRequirement.value.trim() !== '' && files.value.length > 0
)

function close() {
  if (loading.value) return
  emit('update:modelValue', false)
}

function triggerFileInput() {
  if (!loading.value) fileInput.value?.click()
}

function handleFileSelect(e) {
  addFiles(Array.from(e.target.files))
}

function handleDragOver() {
  if (!loading.value) isDragOver.value = true
}
function handleDragLeave() {
  isDragOver.value = false
}
function handleDrop(e) {
  isDragOver.value = false
  if (loading.value) return
  addFiles(Array.from(e.dataTransfer.files))
}

function addFiles(newFiles) {
  const valid = newFiles.filter((f) => {
    const ext = f.name.split('.').pop().toLowerCase()
    return ['pdf', 'md', 'txt'].includes(ext)
  })
  files.value.push(...valid)
}

function removeFile(i) {
  files.value.splice(i, 1)
}

function startSimulation() {
  if (!canSubmit.value || loading.value) return
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, simulationRequirement.value)
    emit('update:modelValue', false)
    router.push({ name: 'Process', params: { projectId: 'new' } })
  })
}

// ESC 关闭
function onKey(e) {
  if (e.key === 'Escape' && props.modelValue) close()
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

// 锁定 body 滚动
watch(
  () => props.modelValue,
  (visible) => {
    document.body.style.overflow = visible ? 'hidden' : ''
  }
)
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
  backdrop-filter: blur(4px);
}
.modal-card {
  position: relative;
  background: #fff;
  border-radius: 12px;
  width: min(640px, 100%);
  max-height: 90vh;
  overflow-y: auto;
  padding: 32px 28px 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}
.modal-close {
  position: absolute;
  top: 12px;
  right: 14px;
  background: transparent;
  border: none;
  font-size: 26px;
  line-height: 1;
  color: #999;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.15s;
}
.modal-close:hover {
  background: #f5f5f5;
  color: #000;
}
.modal-notice {
  background: #fff8e1;
  color: #856404;
  font-size: 13px;
  padding: 10px 14px;
  border-radius: 6px;
  border-left: 3px solid #ffc107;
  margin-bottom: 18px;
  line-height: 1.5;
}
.modal-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 18px;
  color: #000;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

/* console-box 样式（搬自 Home.vue） */
.console-box {
  font-family: 'JetBrains Mono', monospace;
}
.console-section { margin-bottom: 16px; }
.console-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #666;
  margin-bottom: 8px;
  letter-spacing: 0.05em;
}
.console-label {
  text-transform: uppercase;
  font-weight: 600;
}
.console-meta {
  color: #999;
}
.console-divider {
  text-align: center;
  font-size: 10px;
  color: #999;
  letter-spacing: 0.1em;
  margin: 14px 0 8px;
  position: relative;
}
.console-divider::before,
.console-divider::after {
  content: '';
  position: absolute;
  top: 50%;
  width: calc(50% - 60px);
  height: 1px;
  background: #e5e5e5;
}
.console-divider::before { left: 0; }
.console-divider::after  { right: 0; }

.upload-zone {
  border: 1.5px dashed #d0d0d0;
  border-radius: 8px;
  padding: 26px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: #fafafa;
  min-height: 130px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.upload-zone:hover { border-color: #FF4500; background: #fff; }
.upload-zone.drag-over { border-color: #FF4500; background: #fff5ef; }
.upload-zone.has-files { padding: 14px; }
.upload-placeholder { color: #888; }
.upload-icon { font-size: 28px; margin-bottom: 6px; color: #bbb; }
.upload-title { font-size: 13px; font-weight: 600; color: #333; margin-bottom: 4px; }
.upload-hint { font-size: 11px; color: #999; }
.file-list { width: 100%; }
.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 4px;
  margin-bottom: 4px;
  font-size: 12px;
}
.file-icon { font-size: 14px; }
.file-name {
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.remove-btn {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
}
.remove-btn:hover { color: #FF4500; }

.input-wrapper { position: relative; }
.code-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  resize: vertical;
  background: #fafafa;
  color: #333;
  box-sizing: border-box;
}
.code-input:focus { outline: none; border-color: #FF4500; background: #fff; }
.code-input::placeholder { color: #b8b8b8; font-style: italic; }
.model-badge {
  position: absolute;
  bottom: 8px;
  right: 10px;
  font-size: 10px;
  color: #999;
  background: rgba(255, 255, 255, 0.85);
  padding: 2px 6px;
  border-radius: 3px;
  pointer-events: none;
}

.btn-section { margin-top: 18px; margin-bottom: 0; }
.start-engine-btn {
  width: 100%;
  padding: 14px;
  background: #000;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-family: 'Space Grotesk', system-ui, sans-serif;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.08em;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  transition: all 0.2s;
}
.start-engine-btn:hover:not(:disabled) { background: #FF4500; }
.start-engine-btn:disabled { background: #ccc; cursor: not-allowed; }
.btn-arrow { font-size: 16px; }

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }
</style>
