<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import * as echarts from 'echarts'
import StatCard from '@/components/StatCard.vue'
import { getAdminDashboard, getSystemOverview, type AdminDashboardStats } from '@/api/admin'
import { getIndustryDistribution, getScoreDistribution } from '@/api/risk'
import { getServerStatus, getHealth } from '@/api/monitor'

const overview = ref<any>(null)
const server = ref<any>(null)
const health = ref<any>(null)
const adminDashboard = ref<AdminDashboardStats | null>(null)

const trendChartRef = ref<HTMLElement>()
const callsChartRef = ref<HTMLElement>()
const scoreChartRef = ref<HTMLElement>()
const industryChartRef = ref<HTMLElement>()

// 图表实例复用：避免每次 dispose+init 导致重绘异常 / 画布重叠
const chartInstances = new Map<string, echarts.ECharts>()
let timer: any = null

function getChart(key: string, el?: HTMLElement): echarts.ECharts | null {
  if (!el) return null
  let chart = chartInstances.get(key)
  if (!chart) {
    chart = echarts.init(el)
    chartInstances.set(key, chart)
  }
  return chart
}

function fmtTime(sec: number): string {
  const d = Math.floor(sec / 86400)
  const h = Math.floor((sec % 86400) / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return d > 0 ? `${d}天${h}小时` : `${h}小时${m}分`
}

function renderTrend(data: any[]) {
  const chart = getChart('trend', trendChartRef.value)
  if (!chart) return
  chart.setOption(
    {
      tooltip: { trigger: 'axis' },
      legend: { data: ['评估次数', '平均评分'], top: 0, itemWidth: 16, itemHeight: 10, textStyle: { fontSize: 12 } },
      grid: { top: 42, right: 44, bottom: 48, left: 52 },
      xAxis: {
        type: 'category',
        data: data.map((d) => d.date.slice(5)),
        axisLabel: { fontSize: 11, color: '#909399', interval: 0, rotate: 30 },
        axisLine: { lineStyle: { color: '#dcdfe6' } },
      },
      yAxis: [
        {
          type: 'value',
          name: '次数',
          minInterval: 1,
          nameTextStyle: { color: '#909399', fontSize: 11 },
          splitLine: { lineStyle: { color: '#f0f2f5' } },
        },
        {
          type: 'value',
          name: '评分',
          min: 0,
          max: 1000,
          nameTextStyle: { color: '#909399', fontSize: 11 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '评估次数',
          type: 'line',
          smooth: true,
          data: data.map((d) => d.count),
          itemStyle: { color: '#2c6e49' },
          lineStyle: { width: 2 },
          symbolSize: 6,
          areaStyle: { opacity: 0.15 },
        },
        {
          // 无记录的日期用 null，避免平均评分线在 0 处与次数线重叠
          name: '平均评分',
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          data: data.map((d) => (d.count > 0 ? d.avgScore : null)),
          itemStyle: { color: '#e6a23c' },
          lineStyle: { width: 2 },
          symbolSize: 6,
          connectNulls: false,
        },
      ],
    },
    { notMerge: true }
  )
}

function renderScoreDist(data: any[]) {
  const chart = getChart('score', scoreChartRef.value)
  if (!chart) return
  chart.setOption(
    {
      tooltip: { trigger: 'axis' },
      grid: { top: 20, right: 20, bottom: 30, left: 50 },
      xAxis: { type: 'category', data: data.map((d) => d.range), axisLabel: { fontSize: 11, color: '#909399' } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f0f2f5' } } },
      series: [
        {
          type: 'bar',
          data: data.map((d) => ({
            value: d.count,
            itemStyle: {
              color: d.range.includes('800')
                ? '#67c23a'
                : d.range.includes('700') || d.range.includes('600')
                  ? '#e6a23c'
                  : '#f56c6c',
              borderRadius: [4, 4, 0, 0],
            },
          })),
          barWidth: 30,
        },
      ],
    },
    { notMerge: true }
  )
}

function renderIndustry(data: any[]) {
  const chart = getChart('industry', industryChartRef.value)
  if (!chart) return
  chart.setOption(
    {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0 },
      series: [
        {
          type: 'pie',
          radius: ['40%', '68%'],
          center: ['50%', '46%'],
          data: data.map((d) => ({ name: d.name, value: d.value })),
          label: { formatter: '{b}\n{d}%' },
          itemStyle: { borderRadius: 6 },
        },
      ],
    },
    { notMerge: true }
  )
}

function renderEngineUsage(data: AdminDashboardStats['engineUsage']['daily']) {
  const chart = getChart('engineUsage', callsChartRef.value)
  if (!chart) return
  chart.setOption(
    {
      tooltip: { trigger: 'axis' },
      legend: { data: ['专家引擎调用', '数据层融合应用'], top: 0 },
      grid: { top: 42, right: 24, bottom: 42, left: 48 },
      xAxis: { type: 'category', data: data.map((item) => item.date.slice(5)), axisLabel: { color: '#909399' } },
      yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#f0f2f5' } } },
      series: [
        {
          name: '专家引擎调用',
          type: 'bar',
          data: data.map((item) => item.expertCalls),
          itemStyle: { color: '#4361ee' },
        },
        {
          name: '数据层融合应用',
          type: 'bar',
          data: data.map((item) => item.dataLayerApplications),
          itemStyle: { color: '#e6a23c' },
        },
      ],
    },
    { notMerge: true }
  )
}

async function load() {
  // 各接口独立容错：单个接口失败不影响其他数据的刷新
  const [ov, srv, hlt, stats] = await Promise.allSettled([
    getSystemOverview(),
    getServerStatus(),
    getHealth(),
    getAdminDashboard(14),
  ])
  if (ov.status === 'fulfilled') overview.value = ov.value
  if (srv.status === 'fulfilled') server.value = srv.value
  if (hlt.status === 'fulfilled') health.value = hlt.value
  if (stats.status === 'fulfilled') adminDashboard.value = stats.value
  await nextTick()

  // 图表数据（单个失败时保留上次渲染）
  try {
    const [industry, scoreDist] = await Promise.all([getIndustryDistribution(), getScoreDistribution()])
    renderIndustry(industry)
    renderScoreDist(scoreDist)
    if (stats.status === 'fulfilled') {
      renderTrend(stats.value.assessmentTrend)
      renderEngineUsage(stats.value.engineUsage.daily)
    }
    chartInstances.forEach((c) => c.resize())
  } catch {
    // 忽略
  }
}

function handleResize() {
  chartInstances.forEach((c) => c.resize())
}

onMounted(() => {
  load()
  timer = setInterval(load, 10000)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  window.removeEventListener('resize', handleResize)
  chartInstances.forEach((c) => c.dispose())
  chartInstances.clear()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>系统概览</h1>
      <p>涉农信贷风控后端 · 全平台运行状态（每 10 秒自动刷新）</p>
    </div>

    <div class="metric-grid">
      <StatCard title="用户数" :value="overview?.users ?? '-'" icon="User" color="#2c6e49" />
      <StatCard title="评估记录" :value="overview?.records ?? '-'" unit="条" icon="Document" color="#4c956c" />
      <StatCard title="模型版本" :value="overview?.models ?? '-'" unit="个" icon="Cpu" color="#4361ee" />
      <StatCard
        title="API 调用（今日）"
        :value="overview?.apiLogsToday ?? '-'"
        unit="次"
        icon="Connection"
        color="#e76f51"
      />
      <StatCard title="CPU 使用率" :value="server ? server.cpu.percent + '%' : '-'" icon="Monitor" color="#e6a23c" />
      <StatCard title="内存使用率" :value="server ? server.memory.percent + '%' : '-'" icon="Coin" color="#9b5de5" />
    </div>

    <div v-if="adminDashboard" class="metric-grid business-metrics">
      <StatCard
        title="近 14 天评估"
        :value="adminDashboard.assessmentTotal"
        unit="次"
        icon="DataAnalysis"
        color="#4c956c"
      />
      <StatCard
        title="平均数据完整度"
        :value="
          adminDashboard.averageCompleteness == null ? '-' : (adminDashboard.averageCompleteness * 100).toFixed(1) + '%'
        "
        icon="CircleCheck"
        color="#4361ee"
      />
      <StatCard
        title="账号评估用户"
        :value="adminDashboard.userBehavior.activeUsers"
        unit="人"
        icon="UserFilled"
        color="#9b5de5"
      />
      <StatCard
        title="专家引擎调用"
        :value="adminDashboard.engineUsage.expertCalls"
        unit="次"
        icon="Cpu"
        color="#e76f51"
      />
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">近 14 天评估趋势</h3>
          <div ref="trendChartRef" style="width: 100%; height: 320px" />
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">信用评分分布</h3>
          <div ref="scoreChartRef" style="width: 100%; height: 320px" />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">行业分布</h3>
          <div ref="industryChartRef" style="width: 100%; height: 300px" />
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">服务健康</h3>
          <div class="health-grid">
            <div
              v-for="item in [
                { label: '后端服务', value: health?.service, ok: health?.service === 'ok' },
                { label: '数据库', value: health?.database, ok: health?.database === 'ok' },
                {
                  label: '信用模型',
                  value: health?.modelExists ? `已加载 ${health?.modelVersion}` : '未加载',
                  ok: health?.modelExists,
                },
              ]"
              :key="item.label"
              class="health-item"
            >
              <el-icon :size="20" :color="item.ok ? '#67c23a' : '#f56c6c'">
                <CircleCheckFilled v-if="item.ok" />
                <CircleCloseFilled v-else />
              </el-icon>
              <div>
                <div class="health-label">{{ item.label }}</div>
                <div class="health-value" :style="{ color: item.ok ? '#67c23a' : '#f56c6c' }">{{ item.value }}</div>
              </div>
            </div>
            <div class="health-item">
              <el-icon :size="20" color="#2c6e49"><Timer /></el-icon>
              <div>
                <div class="health-label">运行时长</div>
                <div class="health-value">{{ server ? fmtTime(server.uptimeSeconds) : '-' }}</div>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row v-if="adminDashboard" :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :md="14">
        <div class="info-card">
          <h3 class="card-title">近 14 天实际评估引擎调用</h3>
          <p class="chart-note">
            专家评估 {{ adminDashboard.engineUsage.expertCalls }} 次，数据层融合应用
            {{ adminDashboard.engineUsage.dataLayerApplications }} 次；调用有记录
            {{ adminDashboard.engineUsage.trackedAssessments }} 条评估，旧记录未跟踪
            {{ adminDashboard.engineUsage.untrackedAssessments }} 条。
          </p>
          <p class="chart-note">
            接口日志另记录 {{ adminDashboard.assessmentApiRequests.total }} 次 POST /risk/assess-dynamic 请求，其中
            {{ adminDashboard.assessmentApiRequests.succeeded }} 次 HTTP 2xx、{{
              adminDashboard.assessmentApiRequests.failed
            }}
            次非 2xx；包含校验失败请求。 另有 {{ adminDashboard.assessmentApiRequests.unknown }} 次缺少业务码的请求。
          </p>
          <div ref="callsChartRef" style="width: 100%; height: 300px" />
        </div>
      </el-col>
      <el-col :xs="24" :md="10">
        <div class="info-card">
          <h3 class="card-title">评估与账号行为</h3>
          <div class="behavior-summary">
            <span>近 14 天均分 {{ adminDashboard.averageScore }}</span>
            <span
              >低 / 中 / 高风险 {{ adminDashboard.lowRiskCount }} / {{ adminDashboard.midRiskCount }} /
              {{ adminDashboard.highRiskCount }}</span
            >
            <span>否决 {{ adminDashboard.vetoCount }} 次</span>
            <span>规则触发 {{ adminDashboard.overrideCount }} 次</span>
          </div>
          <div class="behavior-summary">
            <span>账号评估 {{ adminDashboard.userBehavior.registeredAssessments }} 次</span>
            <span>匿名评估 {{ adminDashboard.userBehavior.anonymousAssessments }} 次</span>
            <span>活跃账号 {{ adminDashboard.userBehavior.activeUsers }} 个</span>
          </div>
          <el-table :data="adminDashboard.userBehavior.topUsers" size="small" max-height="235">
            <el-table-column prop="username" label="用户" min-width="130" show-overflow-tooltip />
            <el-table-column prop="assessmentCount" label="评估次数" width="100" align="right" />
          </el-table>
          <p class="chart-note">根据评估记录的账号归属统计，匿名评估单独计数。</p>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.health-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;

  .health-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px;
    background: #f7f9fb;
    border-radius: 8px;

    .health-label {
      font-size: 12px;
      color: #909399;
    }

    .health-value {
      font-size: 15px;
      font-weight: 600;
      color: #303133;
    }
  }
}

.business-metrics {
  margin-top: 16px;
}

.chart-note {
  color: #909399;
  font-size: 12px;
  margin: -4px 0 8px;
}

.behavior-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  color: #606266;
  font-size: 13px;
  margin-bottom: 12px;
}
</style>
