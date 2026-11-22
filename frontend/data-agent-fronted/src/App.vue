<template>
  <div class="chat-page" :data-theme="currentTheme">
    <!-- 动态背景层 -->
    <div class="bg-layer" aria-hidden="true">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
      <div class="blob blob-3"></div>
      <div class="grid-overlay"></div>
      <div class="scan-overlay"></div>
    </div>

    <!-- 顶栏 -->
    <header class="topbar">
      <div class="brand">
        <div class="brand-logo">◆</div>
        <div class="brand-text">
          <div class="brand-title">Data Agent</div>
          <div class="brand-sub">自然语言问数智能体</div>
        </div>
      </div>
      <ThemeSwitcher v-model="currentTheme" />
    </header>

    <!-- 消息区 -->
    <div ref="messagesEl" class="messages">
      <TransitionGroup name="msg">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message-row', msg.role]"
        >
          <div v-if="msg.role === 'assistant'" class="avatar">🤖</div>

          <div class="bubble">
            <!-- 文本 -->
            <div v-if="msg.type === 'text'" class="text-content">
              {{ msg.content }}
            </div>

            <!-- 进度步骤（时间线） -->
            <div v-else-if="msg.type === 'steps'" class="steps">
              <div
                v-for="(step, sIdx) in msg.steps"
                :key="sIdx"
                class="step"
                :class="step.status"
              >
                <span class="dot" :class="step.status">
                  <template v-if="step.status === 'success'">✓</template>
                  <template v-else-if="step.status === 'error'">✕</template>
                </span>
                <span class="step-text">{{ step.text }}</span>
                <span class="step-status">{{ statusLabel(step.status) }}</span>
              </div>
            </div>

            <!-- 表格 -->
            <div v-else-if="msg.type === 'table'" class="table-wrap">
              <table v-if="msg.columns.length" class="result-table">
                <thead>
                  <tr>
                    <th v-for="col in msg.columns" :key="col">{{ col }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, rIdx) in msg.rows" :key="rIdx">
                    <td v-for="col in msg.columns" :key="col">
                      {{ row[col] }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty-hint">查询无数据</div>
            </div>

            <!-- SQL -->
            <div v-else-if="msg.type === 'sql'" class="sql-wrap">
              <div class="sql-bar">
                <span class="sql-label">执行 SQL</span>
                <button class="copy-btn" @click="copySql(msg.content, index)">
                  {{ copiedIndex === index ? '已复制' : '复制' }}
                </button>
              </div>
              <pre class="sql-code" v-html="highlightSql(msg.content)"></pre>
            </div>

            <!-- 错误 -->
            <div v-else-if="msg.type === 'error'" class="error-text">
              {{ msg.content }}
            </div>
          </div>

          <div v-if="msg.role === 'user'" class="avatar">🧑</div>
        </div>
      </TransitionGroup>
      <div class="messages-bottom-spacer"></div>
    </div>

    <!-- 悬浮输入框 -->
    <div class="input-wrapper">
      <div class="input-box">
        <input
          v-model="question"
          @keyup.enter="sendQuestion"
          placeholder="用自然语言提问，例如：统计去年各地区的销售总额"
        />
        <button class="send-btn" @click="sendQuestion" :disabled="loading">
          <span v-if="loading" class="loading-dots">
            <i></i><i></i><i></i>
          </span>
          <span v-else>{{ loading ? '执行中...' : '发送' }}</span>
        </button>
        <button
          class="report-btn"
          @click="generateReport"
          :disabled="loading || reportLoading"
        >
          {{ reportLoading ? '生成中...' : '生成报表' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import ThemeSwitcher from './components/ThemeSwitcher.vue'
import { defaultThemeKey, isValidTheme } from './themes.js'

/* ========== 主题（纯展示，不影响数据） ========== */
const currentTheme = ref(
  isValidTheme(localStorage.getItem('da-theme'))
    ? localStorage.getItem('da-theme')
    : defaultThemeKey
)
watch(currentTheme, (v) => {
  document.documentElement.setAttribute('data-theme', v)
  localStorage.setItem('da-theme', v)
})

/* ========== 以下数据/SSE 逻辑保持与后端规约完全一致 ========== */
const API_URL = '/api/query'

const question = ref('')
const loading = ref(false)
const reportLoading = ref(false)
const lastQuery = ref('')
const messages = ref([])
const messagesEl = ref(null)
const copiedIndex = ref(-1)

function scrollToBottom() {
  const el = messagesEl.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

async function sendQuestion() {
  if (!question.value || loading.value) return

  const q = question.value
  question.value = ''
  loading.value = true
  lastQuery.value = q

  messages.value.push({ role: 'user', type: 'text', content: q })

  // steps 容器
  const stepIndex =
    messages.value.push({
      role: 'assistant',
      type: 'steps',
      steps: [],
    }) - 1

  await nextTick()
  scrollToBottom()

  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q }),
    })

    if (!response.body) throw new Error('服务器未返回流')

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split('\n\n')
      buffer = events.pop()

      for (const evt of events) {
        const line = evt.trim()
        if (!line.startsWith('data:')) continue

        let data
        try {
          data = JSON.parse(line.replace(/^data:\s*/, ''))
        } catch {
          continue
        }

        const steps = messages.value[stepIndex].steps

        // progress：完全按后端状态渲染
        if (data.type === 'progress') {
          let step = steps.find((s) => s.text === data.step)

          if (!step) {
            step = {
              text: data.step,
              status: data.status,
            }
            steps.push(step)
          } else {
            step.status = data.status
          }
        }

        // 生成的 SQL
        else if (data.type === 'sql') {
          messages.value.push({
            role: 'assistant',
            type: 'sql',
            content: data.sql || '',
          })
        }

        // 表格结果
        else if (data.type === 'result' && Array.isArray(data.data)) {
          messages.value.push({
            role: 'assistant',
            type: 'table',
            columns: Object.keys(data.data[0] || {}),
            rows: data.data,
          })
        }

        // 错误
        else if (data.type === 'error') {
          messages.value.push({
            role: 'assistant',
            type: 'error',
            content: data.message || '发生错误',
          })
        }

        await nextTick()
        scrollToBottom()
      }
    }
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      type: 'error',
      content: e?.message || '请求失败',
    })
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

async function generateReport() {
  const q = lastQuery.value || question.value
  if (!q) {
    messages.value.push({
      role: 'assistant',
      type: 'error',
      content: '请先输入并发送一个问题，再生成报表',
    })
    return
  }
  if (reportLoading.value) return

  reportLoading.value = true
  try {
    const response = await fetch('/api/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q }),
    })
    if (!response.ok) {
      const text = await response.text().catch(() => '')
      throw new Error(text || `生成报表失败（${response.status}）`)
    }

    const blob = await response.blob()
    const disposition = response.headers.get('Content-Disposition') || ''
    let filename = `数据报表_${Date.now()}.xlsx`
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/)
    if (utf8Match) {
      filename = decodeURIComponent(utf8Match[1])
    } else {
      const asciiMatch = disposition.match(/filename="?([^";]+)"?/)
      if (asciiMatch) filename = asciiMatch[1]
    }

    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      type: 'error',
      content: e?.message || '生成报表失败',
    })
  } finally {
    reportLoading.value = false
    await nextTick()
    scrollToBottom()
  }
}

/* ========== 展示辅助函数 ========== */
function statusLabel(s) {
  if (s === 'running') return '进行中'
  if (s === 'success') return '完成'
  if (s === 'error') return '失败'
  return ''
}

function copySql(sql, idx) {
  if (!navigator.clipboard) return
  navigator.clipboard.writeText(sql).then(() => {
    copiedIndex.value = idx
    setTimeout(() => {
      if (copiedIndex.value === idx) copiedIndex.value = -1
    }, 1800)
  })
}

const SQL_KEYWORDS =
  /\b(SELECT|FROM|WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|OUTER\s+JOIN|FULL\s+JOIN|CROSS\s+JOIN|ON|AS|AND|OR|NOT|IN|LIKE|BETWEEN|IS|NULL|DISTINCT|COUNT|SUM|AVG|MAX|MIN|CASE|WHEN|THEN|ELSE|END|INSERT|INTO|VALUES|UPDATE|SET|DELETE|CREATE|TABLE|ALTER|DROP|IF|EXISTS|LIMIT|OFFSET|UNION|ALL|DESC|ASC|WITH|OVER|PARTITION\s+BY)\b/gi

function highlightSql(sql) {
  if (!sql) return ''
  let s = String(sql)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  s = s.replace(/(--[^\n]*)/g, '<span class="tok-com">$1</span>')
  s = s.replace(
    /('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")/g,
    '<span class="tok-str">$1</span>'
  )
  s = s.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="tok-num">$1</span>')
  s = s.replace(SQL_KEYWORDS, '<span class="tok-kw">$1</span>')
  return s
}
</script>

<style scoped>
/* 页面容器 */
.chat-page {
  position: relative;
  height: 100%;
  overflow: hidden;
  background: var(--bg-page);
  color: var(--text-primary);
}

/* 动态背景层 */
.bg-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 0;
}
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: var(--blob-opacity);
  will-change: transform;
}
.blob-1 {
  width: 420px;
  height: 420px;
  top: -120px;
  left: -80px;
  background: var(--blob-1);
  animation: float1 18s ease-in-out infinite;
}
.blob-2 {
  width: 380px;
  height: 380px;
  bottom: -140px;
  right: -60px;
  background: var(--blob-2);
  animation: float2 22s ease-in-out infinite;
}
.blob-3 {
  width: 300px;
  height: 300px;
  top: 40%;
  left: 55%;
  background: var(--blob-3);
  animation: float3 26s ease-in-out infinite;
}
.grid-overlay {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(
      var(--text-muted) 1px,
      transparent 1px
    ),
    linear-gradient(90deg, var(--text-muted) 1px, transparent 1px);
  background-size: 44px 44px;
  opacity: var(--grid-opacity);
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
}
.scan-overlay {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent 0,
    transparent 2px,
    rgba(0, 0, 0, 0.25) 3px,
    transparent 4px
  );
  opacity: var(--scan-opacity);
  animation: scanmove 0.6s linear infinite;
  mix-blend-mode: overlay;
}

/* 顶栏 */
.topbar {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 28px;
  background: var(--header-bg);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--card-border);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: var(--accent-text);
  background: var(--btn-bg);
  box-shadow: 0 4px 14px var(--accent);
}
.brand-title {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.5px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.brand-sub {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* 消息区 */
.messages {
  position: relative;
  z-index: 1;
  height: calc(100% - 65px);
  overflow-y: auto;
  padding: 28px 20% 170px;
  scroll-behavior: smooth;
}

.message-row {
  display: flex;
  margin-bottom: 16px;
  animation: fadeInUp 0.35s ease both;
}
.message-row.assistant {
  justify-content: flex-start;
}
.message-row.user {
  justify-content: flex-end;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  margin: 0 10px;
  flex-shrink: 0;
  backdrop-filter: blur(8px);
}

.bubble {
  max-width: min(840px, 72%);
  padding: 14px 16px;
  border-radius: 16px;
  background: var(--bubble-assistant-bg);
  border: 1px solid var(--bubble-assistant-border);
  backdrop-filter: blur(12px);
  box-shadow: var(--shadow);
  color: var(--text-primary);
  line-height: 1.6;
}
.message-row.user .bubble {
  background: var(--bubble-user-bg);
  border-color: var(--bubble-user-border);
  color: var(--bubble-user-text);
}
.text-content {
  white-space: pre-wrap;
  word-break: break-word;
}

/* 步骤时间线 */
.steps {
  position: relative;
  padding-left: 26px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.steps::before {
  content: '';
  position: absolute;
  left: 9px;
  top: 10px;
  bottom: 10px;
  width: 2px;
  background: var(--timeline-line);
  border-radius: 2px;
}
.step {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 0;
  font-size: 13px;
}
.step .dot {
  position: absolute;
  left: -26px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  background: var(--card-bg);
  border: 2px solid var(--timeline-line);
  color: transparent;
}
.step .dot.running {
  border-color: var(--running);
  background: var(--running);
  animation: pulseRing 1.4s ease-out infinite;
}
.step .dot.success {
  border-color: var(--success);
  background: var(--success);
  color: #fff;
}
.step .dot.error {
  border-color: var(--error);
  background: var(--error);
  color: #fff;
}
.step-text {
  color: var(--text-secondary);
}
.step.success .step-text {
  color: var(--text-primary);
}
.step.error .step-text {
  color: var(--error);
}
.step-status {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
}
.step.running .step-status {
  color: var(--running);
}

/* 表格 */
.table-wrap {
  max-width: 100%;
  overflow-x: auto;
  border-radius: 10px;
  border: 1px solid var(--table-border);
}
.result-table {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.result-table th,
.result-table td {
  padding: 8px 14px;
  white-space: nowrap;
  text-align: left;
  border-bottom: 1px solid var(--table-border);
}
.result-table th {
  background: var(--table-head-bg);
  color: var(--table-head-text);
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
  backdrop-filter: blur(4px);
}
.result-table tbody tr:nth-child(even) {
  background: var(--table-row-alt);
}
.result-table tbody tr:hover {
  background: var(--table-hover);
}
.result-table tbody tr:last-child td {
  border-bottom: none;
}
.empty-hint {
  padding: 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

/* SQL */
.sql-wrap {
  max-width: 100%;
}
.sql-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.sql-label {
  font-size: 12px;
  color: var(--text-muted);
}
.copy-btn {
  padding: 3px 10px;
  font-size: 11px;
  border-radius: 6px;
  border: 1px solid var(--card-border);
  background: var(--card-bg);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}
.copy-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.sql-code {
  margin: 0;
  padding: 12px 14px;
  background: var(--sql-bg);
  color: var(--sql-text);
  border-radius: 10px;
  font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
  font-size: 12.5px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-x: auto;
  border: 1px solid var(--card-border);
}
.sql-code :deep(.tok-kw) {
  color: var(--tok-kw);
  font-weight: 600;
}
.sql-code :deep(.tok-str) {
  color: var(--tok-str);
}
.sql-code :deep(.tok-num) {
  color: var(--tok-num);
}
.sql-code :deep(.tok-com) {
  color: var(--tok-com);
  font-style: italic;
}

/* 错误 */
.error-text {
  color: var(--error);
  font-weight: 600;
}

/* 悬浮输入框 */
.input-wrapper {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 26px;
  display: flex;
  justify-content: center;
  padding: 0 16px;
  pointer-events: none;
  z-index: 5;
}
.input-box {
  pointer-events: auto;
  width: 100%;
  max-width: 760px;
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 18px;
  background: var(--input-bg);
  backdrop-filter: blur(16px);
  border: 1px solid var(--input-border);
  box-shadow: var(--shadow);
  transition: box-shadow 0.25s, border-color 0.25s;
}
.input-box:focus-within {
  border-color: var(--accent);
  box-shadow: var(--input-glow), var(--shadow);
}
.input-box input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 15px;
}
.input-box input::placeholder {
  color: var(--text-muted);
}
.input-box button {
  padding: 9px 18px;
  border-radius: 12px;
  border: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: transform 0.15s, opacity 0.2s, filter 0.2s;
}
.input-box button:hover:not(:disabled) {
  transform: translateY(-1px);
  filter: brightness(1.08);
}
.input-box button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.send-btn {
  background: var(--btn-bg);
  color: var(--btn-text);
}
.report-btn {
  background: linear-gradient(135deg, var(--success), var(--accent-2));
  color: var(--btn-text);
  white-space: nowrap;
}
.loading-dots {
  display: inline-flex;
  gap: 3px;
}
.loading-dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  animation: blink 1.2s infinite both;
}
.loading-dots i:nth-child(2) {
  animation-delay: 0.15s;
}
.loading-dots i:nth-child(3) {
  animation-delay: 0.3s;
}

.messages-bottom-spacer {
  height: 200px;
}

/* TransitionGroup 入场（与 message-row 动画二选一，这里禁用组动画避免重复） */
.msg-enter-active {
  animation: none;
}

/* 响应式 */
@media (max-width: 768px) {
  .messages {
    padding: 20px 14px 170px;
  }
  .bubble {
    max-width: 85%;
  }
  .topbar {
    padding: 12px 16px;
  }
  .brand-sub {
    display: none;
  }
}
</style>