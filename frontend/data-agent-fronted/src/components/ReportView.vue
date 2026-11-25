<template>
  <div class="report-overlay" :data-theme="theme">
    <div class="report-container">
      <!-- 顶栏 -->
      <header class="report-header">
        <button class="back-btn" @click="$emit('close')">
          <span class="back-arrow">←</span> 返回对话
        </button>
        <div class="report-title">
          <span class="report-logo">◆</span>
          <span class="report-name">数据报表</span>
          <span v-if="data.generated_at" class="report-time">{{ data.generated_at }}</span>
        </div>
        <div class="header-placeholder"></div>
      </header>

      <!-- 滚动内容 -->
      <div class="report-body">
        <!-- 查询问题 -->
        <section class="card query-card">
          <div class="card-label">查询问题</div>
          <div class="query-text">{{ data.query }}</div>
          <div class="query-meta">
            <span>共 <b>{{ data.row_count ?? rows.length }}</b> 行数据</span>
            <span v-if="!data.error" class="meta-ok">查询成功</span>
            <span v-else class="meta-err">查询失败</span>
          </div>
        </section>

        <!-- 错误提示 -->
        <section v-if="data.error" class="card error-card">
          <div class="card-label">错误信息</div>
          <div class="error-content">{{ data.error }}</div>
        </section>

        <!-- 分析结论 -->
        <section v-if="hasData && data.analysis" class="card analysis-card">
          <div class="card-label">分析结论</div>
          <div class="analysis-content">{{ data.analysis }}</div>
        </section>

        <!-- 图表区 -->
        <section v-if="hasData" class="card chart-card">
          <div class="chart-toolbar">
            <div class="card-label chart-title">可视化图表</div>
            <div class="chart-types">
              <button
                v-for="t in chartTypes"
                :key="t.key"
                class="type-btn"
                :class="{ active: chartType === t.key }"
                @click="chartType = t.key"
              >
                <span class="type-icon">{{ t.icon }}</span>
                <span>{{ t.label }}</span>
              </button>
            </div>
          </div>

          <div class="chart-config">
            <div class="cfg-item">
              <label>维度（X 轴 / 分类）</label>
              <select v-model="dimCol">
                <option v-for="c in columns" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>
            <div class="cfg-item">
              <label>指标（Y 轴 / 数值）</label>
              <select v-model="measureCol">
                <option v-for="c in numericCols" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>
          </div>

          <div v-if="!measureCol" class="chart-hint">
            未检测到数值型指标列，暂无法绘图，请检查查询结果中是否包含数值字段。
          </div>
          <div v-else ref="chartEl" class="chart-canvas"></div>
        </section>

        <!-- 数据明细 -->
        <section v-if="rows.length" class="card table-card">
          <div class="card-label">数据明细</div>
          <div class="table-scroll">
            <table class="detail-table">
              <thead>
                <tr>
                  <th v-for="col in columns" :key="col">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in rows" :key="i">
                  <td v-for="col in columns" :key="col">{{ formatCell(row[col]) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- 执行 SQL -->
        <section v-if="data.sql" class="card sql-card">
          <div class="sql-head">
            <div class="card-label">执行 SQL</div>
            <button class="copy-btn" @click="copySql">{{ copied ? '已复制' : '复制' }}</button>
          </div>
          <pre class="sql-code">{{ data.sql }}</pre>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Object, required: true },
  theme: { type: String, default: 'aurora' },
})
defineEmits(['close'])

const chartTypes = [
  { key: 'line', label: '折线图', icon: '📈' },
  { key: 'bar', label: '柱状图', icon: '📊' },
  { key: 'pie', label: '饼图', icon: '🥧' },
  { key: 'area', label: '面积图', icon: '⛰️' },
  { key: 'scatter', label: '散点图', icon: '✦' },
]

const chartType = ref('line')
const dimCol = ref('')
const measureCol = ref('')
const copied = ref(false)
const chartEl = ref(null)
let chartInstance = null

const columns = computed(() => props.data.columns || [])
const rows = computed(() => props.data.rows || [])
const hasData = computed(() => !props.data.error && rows.value.length > 0)

function isNumericValue(v) {
  if (v === null || v === undefined || v === '') return false
  if (typeof v === 'number') return isFinite(v)
  return !isNaN(Number(v))
}

const numericCols = computed(() => {
  if (!rows.value.length) return []
  return columns.value.filter((col) => {
    let total = 0
    let numeric = 0
    for (const r of rows.value) {
      const v = r[col]
      if (v !== null && v !== undefined && v !== '') {
        total++
        if (isNumericValue(v)) numeric++
      }
    }
    return total > 0 && numeric / total >= 0.8
  })
})

function ensureSelections() {
  const cols = columns.value
  if (!cols.length) {
    dimCol.value = ''
    measureCol.value = ''
    return
  }
  const nums = numericCols.value
  const cats = cols.filter((c) => !nums.includes(c))
  if (!dimCol.value || !cols.includes(dimCol.value)) {
    dimCol.value = cats[0] || cols[0]
  }
  if (!measureCol.value || !cols.includes(measureCol.value)) {
    measureCol.value = nums[0] || ''
  }
}

watch(() => props.data, ensureSelections, { immediate: true })

const aggregated = computed(() => {
  const dim = dimCol.value
  const measure = measureCol.value
  if (!dim || !measure || !rows.value.length) return []
  const map = new Map()
  for (const r of rows.value) {
    const raw = r[dim]
    const name = raw === null || raw === undefined || raw === '' ? '(空)' : String(raw)
    const val = isNumericValue(r[measure]) ? Number(r[measure]) : 0
    map.set(name, (map.get(name) || 0) + val)
  }
  return Array.from(map.entries()).map(([name, value]) => ({ name, value }))
})

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function themeColors() {
  const accent = cssVar('--accent') || '#6366f1'
  const accent2 = cssVar('--accent-2') || '#22d3ee'
  return {
    palette: [
      accent,
      accent2,
      '#a855f7',
      '#34d399',
      '#fbbf24',
      '#f472b6',
      '#fb7185',
      '#2dd4bf',
    ],
    text: cssVar('--text-primary') || '#e8ecff',
    subtext: cssVar('--text-secondary') || '#a5b0d6',
    muted: cssVar('--text-muted') || '#6b7399',
    splitLine: 'rgba(128,128,128,0.18)',
  }
}

function buildOption() {
  const agg = aggregated.value
  const c = themeColors()
  const names = agg.map((d) => d.name)
  const values = agg.map((d) => d.value)
  const dim = dimCol.value
  const measure = measureCol.value
  const base = {
    color: c.palette,
    textStyle: { color: c.text, fontFamily: 'inherit' },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0,0,0,0.78)',
      borderColor: c.palette[0],
      textStyle: { color: '#fff' },
    },
  }

  if (chartType.value === 'pie') {
    return {
      ...base,
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: {
        type: 'scroll',
        bottom: 0,
        textStyle: { color: c.subtext },
      },
      series: [
        {
          type: 'pie',
          radius: ['38%', '70%'],
          center: ['50%', '45%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 6,
            borderColor: 'rgba(0,0,0,0.25)',
            borderWidth: 2,
          },
          label: { color: c.text },
          labelLine: { lineStyle: { color: c.muted } },
          data: agg,
        },
      ],
    }
  }

  if (chartType.value === 'scatter') {
    return {
      ...base,
      tooltip: {
        trigger: 'item',
        formatter: (p) =>
          `${p.data[2]}<br/>${dim}: ${p.data[0]}<br/>${measure}: ${p.data[1]}`,
      },
      grid: { left: 50, right: 30, top: 30, bottom: 60, containLabel: true },
      xAxis: {
        type: 'category',
        data: names,
        axisLabel: { color: c.muted, rotate: names.length > 8 ? 30 : 0 },
        axisLine: { lineStyle: { color: c.muted } },
      },
      yAxis: {
        type: 'value',
        name: measure,
        nameTextStyle: { color: c.muted },
        axisLabel: { color: c.muted },
        splitLine: { lineStyle: { color: c.splitLine } },
      },
      series: [
        {
          type: 'scatter',
          symbolSize: (val) =>
            Math.max(10, Math.min(42, Math.sqrt(Math.abs(val[1]) + 1) * 2.4)),
          itemStyle: { color: c.palette[0], opacity: 0.85, shadowBlur: 10, shadowColor: c.palette[0] },
          data: agg.map((d) => [d.name, d.value, d.name]),
        },
      ],
    }
  }

  const series = {
    name: measure,
    type: chartType.value === 'bar' ? 'bar' : 'line',
    data: values,
    smooth: true,
    symbol: 'circle',
    symbolSize: 7,
  }

  if (chartType.value === 'bar') {
    series.itemStyle = {
      borderRadius: [6, 6, 0, 0],
      color: {
        type: 'linear',
        x: 0,
        y: 0,
        x2: 0,
        y2: 1,
        colorStops: [
          { offset: 0, color: c.palette[0] },
          { offset: 1, color: c.palette[0] + '55' },
        ],
      },
    }
  } else {
    series.itemStyle = { color: c.palette[0] }
    series.lineStyle = { width: 3, color: c.palette[0] }
  }
  if (chartType.value === 'area') {
    series.areaStyle = {
      color: {
        type: 'linear',
        x: 0,
        y: 0,
        x2: 0,
        y2: 1,
        colorStops: [
          { offset: 0, color: c.palette[0] + 'cc' },
          { offset: 1, color: c.palette[0] + '00' },
        ],
      },
    }
  }

  return {
    ...base,
    tooltip: { ...base.tooltip, axisPointer: { type: chartType.value === 'bar' ? 'shadow' : 'line' } },
    grid: { left: 50, right: 30, top: 30, bottom: 60, containLabel: true },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { color: c.muted, rotate: names.length > 8 ? 30 : 0 },
      axisLine: { lineStyle: { color: c.muted } },
    },
    yAxis: {
      type: 'value',
      name: measure,
      nameTextStyle: { color: c.muted },
      axisLabel: { color: c.muted },
      splitLine: { lineStyle: { color: c.splitLine } },
    },
    series: [series],
  }
}

function renderChart() {
  if (!chartInstance) return
  if (!hasData.value || !measureCol.value) {
    chartInstance.clear()
    return
  }
  chartInstance.setOption(buildOption(), true)
}

function onResize() {
  chartInstance && chartInstance.resize()
}

onMounted(() => {
  ensureSelections()
  nextTick(() => {
    if (!chartEl.value) return
    chartInstance = echarts.init(chartEl.value)
    renderChart()
  })
  window.addEventListener('resize', onResize)
})

watch([chartType, dimCol, measureCol, () => props.theme], renderChart)
watch(
  () => props.data,
  () => {
    ensureSelections()
    nextTick(renderChart)
  }
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

function formatCell(v) {
  if (v === null || v === undefined) return ''
  if (typeof v === 'number') {
    if (Number.isInteger(v)) return v.toLocaleString()
    return v.toLocaleString(undefined, { maximumFractionDigits: 4 })
  }
  return String(v)
}

function copySql() {
  if (!navigator.clipboard) return
  navigator.clipboard.writeText(props.data.sql).then(() => {
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 1800)
  })
}
</script>

<style scoped>
.report-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: var(--bg-page);
  overflow: hidden;
  animation: fadeIn 0.25s ease both;
}
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.report-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* 顶栏 */
.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 28px;
  background: var(--header-bg);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--card-border);
  flex-shrink: 0;
}
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid var(--card-border);
  background: var(--card-bg);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.15s;
}
.back-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  transform: translateX(-2px);
}
.back-arrow {
  font-size: 16px;
  line-height: 1;
}
.report-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.report-logo {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: var(--accent-text);
  background: var(--btn-bg);
  box-shadow: 0 4px 14px var(--accent);
}
.report-name {
  font-size: 16px;
  font-weight: 700;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.report-time {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: 4px;
}
.header-placeholder {
  width: 100px;
}

/* 内容区 */
.report-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 8%;
}

.card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  padding: 18px 22px;
  margin-bottom: 18px;
  box-shadow: var(--shadow);
  color: var(--text-primary);
}
.card-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: var(--text-muted);
  margin-bottom: 10px;
  font-weight: 600;
}

.query-text {
  font-size: 17px;
  font-weight: 600;
  line-height: 1.5;
  color: var(--text-primary);
}
.query-meta {
  display: flex;
  gap: 16px;
  margin-top: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}
.query-meta b {
  color: var(--accent);
}
.meta-ok {
  color: var(--success);
  font-weight: 600;
}
.meta-err {
  color: var(--error);
  font-weight: 600;
}

.error-card .error-content {
  color: var(--error);
  font-weight: 600;
  line-height: 1.6;
}

.analysis-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-secondary);
  white-space: pre-wrap;
}

/* 图表 */
.chart-card {
  padding-bottom: 22px;
}
.chart-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.chart-title {
  margin-bottom: 0;
}
.chart-types {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.type-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 10px;
  border: 1px solid var(--card-border);
  background: var(--card-bg);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 12.5px;
  font-weight: 600;
  transition: all 0.15s;
}
.type-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.type-btn.active {
  background: var(--btn-bg);
  color: var(--btn-text);
  border-color: transparent;
  box-shadow: 0 4px 14px var(--accent);
}
.type-icon {
  font-size: 13px;
}

.chart-config {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.cfg-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 180px;
}
.cfg-item label {
  font-size: 11px;
  color: var(--text-muted);
}
.cfg-item select {
  padding: 7px 10px;
  border-radius: 8px;
  border: 1px solid var(--card-border);
  background: var(--input-bg);
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  outline: none;
  backdrop-filter: blur(8px);
}
.cfg-item select:focus {
  border-color: var(--accent);
}

.chart-canvas {
  width: 100%;
  height: 420px;
}
.chart-hint {
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
  padding: 0 20px;
}

/* 数据明细表 */
.table-scroll {
  max-height: 360px;
  overflow: auto;
  border-radius: 10px;
  border: 1px solid var(--table-border);
}
.detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.detail-table th,
.detail-table td {
  padding: 9px 14px;
  white-space: nowrap;
  text-align: left;
  border-bottom: 1px solid var(--table-border);
}
.detail-table th {
  background: var(--table-head-bg);
  color: var(--table-head-text);
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
  backdrop-filter: blur(4px);
}
.detail-table tbody tr:nth-child(even) {
  background: var(--table-row-alt);
}
.detail-table tbody tr:hover {
  background: var(--table-hover);
}
.detail-table tbody tr:last-child td {
  border-bottom: none;
}

/* SQL */
.sql-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.sql-head .card-label {
  margin-bottom: 0;
}
.copy-btn {
  padding: 4px 12px;
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

@media (max-width: 768px) {
  .report-header {
    padding: 12px 16px;
  }
  .report-body {
    padding: 16px 14px;
  }
  .header-placeholder {
    display: none;
  }
  .report-name {
    font-size: 14px;
  }
  .report-time {
    display: none;
  }
  .chart-canvas {
    height: 320px;
  }
}
</style>