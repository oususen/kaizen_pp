<script setup>
import { ref, computed, onMounted } from 'vue'
import { exportTermReport, fetchAnalytics, fetchDepartments } from '../api/client'
import BarChart from '../components/BarChart.vue'
import LineChart from '../components/LineChart.vue'

const term = ref('')
const department = ref('')
const month = ref('')
const departments = ref([])
const message = ref('')
const messageType = ref('info')
const downloading = ref(false)
const loadingAnalytics = ref(false)
const analytics = ref(null)
const lastTermKey = 'kaizen:reports:last-term'
const fiscalMonths = [10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9]

const numberOrZero = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : 0
}

const personSummary = computed(() => analytics.value?.person_summary ?? [])
const departmentSummary = computed(() => analytics.value?.department_summary ?? [])
const hasAnalytics = computed(() => personSummary.value.length > 0 || departmentSummary.value.length > 0)

const summaryMetrics = computed(() => {
  if (!personSummary.value.length) return null
  return {
    totalProposals: personSummary.value.reduce((acc, cur) => acc + numberOrZero(cur['件数']), 0),
    totalEffectAmount: personSummary.value.reduce((acc, cur) => acc + numberOrZero(cur['効果額合計[¥/月]']), 0),
    totalReductionHours: personSummary.value.reduce((acc, cur) => acc + numberOrZero(cur['削減時間合計[Hr/月]']), 0),
  }
})

const topIndividuals = computed(() => {
  return personSummary.value
    .map(row => ({
      name: row['提案者'] || '未設定',
      department: row['部署'] || '未設定',
      proposals: numberOrZero(row['件数']),
      effect: numberOrZero(row['効果額合計[¥/月]']),
      reduction: numberOrZero(row['削減時間合計[Hr/月]']),
    }))
    .sort((a, b) => b.effect - a.effect || b.reduction - a.reduction || b.proposals - a.proposals)
    .slice(0, 3)
})

const departmentLeaders = computed(() => {
  return departmentSummary.value
    .map(row => ({
      department: row['部署'] || '未設定',
      total: numberOrZero(row['年間合計']),
    }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 5)
})

const departmentChartData = computed(() => {
  if (!departmentSummary.value.length) return null
  return {
    labels: departmentSummary.value.map(d => d['部署']),
    datasets: [
      {
        label: '年間累計件数',
        backgroundColor: '#2563eb',
        borderRadius: 8,
        data: departmentSummary.value.map(d => numberOrZero(d['年間合計'])),
      },
    ],
  }
})

const monthKeys = computed(() => {
  if (!departmentSummary.value.length) return []
  const sample = departmentSummary.value[0]
  return Object.keys(sample).filter(key => key !== '部署' && key !== '年間合計')
})

const monthNumberFromKey = (key) => {
  const match = String(key).match(/(\d{1,2})/)
  return match ? Number(match[1]) : null
}

const visibleMonthKeys = computed(() => {
  if (!month.value) return monthKeys.value
  const selected = Number(month.value)
  if (!Number.isFinite(selected)) return monthKeys.value
  return monthKeys.value.filter((key) => monthNumberFromKey(key) === selected)
})

const monthlyChartData = computed(() => {
  if (!departmentSummary.value.length) return null
  if (!visibleMonthKeys.value.length) return null
  const totals = visibleMonthKeys.value.map(monthKey => ({
    month: monthKey,
    total: departmentSummary.value.reduce((acc, dept) => acc + numberOrZero(dept[monthKey]), 0),
  }))
  return {
    labels: totals.map(t => t.month),
    datasets: [
      {
        label: '月別件数',
        backgroundColor: '#10b981',
        borderColor: '#10b981',
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: '#0f766e',
        data: totals.map(t => t.total),
      },
    ],
  }
})



const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
  },
  scales: {
    y: { beginAtZero: true, ticks: { precision: 0 } },
  },
}

const lineChartOptions = {
  ...chartOptions,
  plugins: {
    legend: { display: true, position: 'bottom' },
  },
}

const ensureTerm = () => {
  if (!term.value) {
    message.value = '期を入力してください'
    messageType.value = 'error'
    return false
  }
  return true
}

const loadDepartments = async () => {
  try {
    const results = await fetchDepartments({ page_size: 200 })
    console.log('[ReportsPage] fetchDepartments response:', results)
    const names = Array.isArray(results) ? results.map((d) => d.name).filter(Boolean) : []
    console.log('[ReportsPage] department names:', names)
    departments.value = Array.from(new Set(names)).sort()
  } catch (e) {
    console.error('[ReportsPage] Error loading departments:', e)
  }
}

const loadAnalytics = async () => {
  if (!ensureTerm()) return
  loadingAnalytics.value = true
  analytics.value = null
  message.value = ''
  try {
    const data = await fetchAnalytics({
      term: term.value,
      department: department.value || undefined,
      month: month.value || undefined,
    })
    analytics.value = data
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(lastTermKey, String(term.value))
    }
    messageType.value = 'info'
    message.value = 'データを取得しました'
  } catch (error) {
    messageType.value = 'error'
    message.value = error.message ?? 'データの取得に失敗しました'
  } finally {
    loadingAnalytics.value = false
  }
}

const download = async () => {
  if (!ensureTerm()) return
  downloading.value = true
  message.value = ''
  try {
    const blob = await exportTermReport(term.value)
    const url = window.URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `kaizen_term_${term.value}.xlsx`
    anchor.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    messageType.value = 'error'
    message.value = error.message ?? 'レポートの出力に失敗しました'
  } finally {
    downloading.value = false
  }
}

onMounted(() => {
  loadDepartments()
  if (typeof localStorage === 'undefined') return
  const saved = localStorage.getItem(lastTermKey)
  if (saved) {
    const parsed = Number(saved)
    term.value = Number.isNaN(parsed) ? saved : parsed
  }
})
</script>

<template>
  <section class="reports">
    <div class="card hero">
      <div class="hero__copy">
        <p class="eyebrow">Reports &amp; Insights</p>
        <h2>期別レポート</h2>
        <p class="lede">
          期を指定して改善提案の提出状況とインパクトを一目で把握できます。ダウンロードと可視化をワンクリックで。
        </p>
        <div class="controls">
          <label class="term-input">
            <span>期 (例: 52)</span>
            <input v-model.number="term" type="number" min="1" placeholder="53" @keyup.enter="loadAnalytics" />
          </label>
          <label class="term-input">
            <span>部門フィルタ</span>
            <select v-model="department">
              <option value="">すべて</option>
              <option v-for="dept in departments" :key="dept" :value="dept">{{ dept }}</option>
            </select>
          </label>
                    <label class="term-input">
            <span>月フィルタ (任意)</span>
            <select v-model.number="month">
              <option value="">すべて</option>
              <option v-for="m in fiscalMonths" :key="m" :value="m">{{ m }}月</option>
            </select>
          </label>
          <div class="hero__actions">
            <button class="btn primary" :disabled="loadingAnalytics" @click="loadAnalytics">
              {{ loadingAnalytics ? '解析中...' : 'データを表示' }}
            </button>
            <button class="btn ghost" :disabled="downloading" @click="download">
              {{ downloading ? '書き出し中...' : 'Excelレポート出力' }}
            </button>
          </div>
        </div>
        <p class="helper">入力した期で集計を行い、結果を画面表示またはExcelで保存できます。</p>
      </div>
      <div class="hero__badge">
        <div class="pill">最新集計</div>
        <h3 v-if="summaryMetrics">{{ summaryMetrics.totalProposals.toLocaleString() }}件</h3>
        <p v-if="summaryMetrics">この期の改善件数</p>
        <p v-else class="placeholder">データ未取得</p>
      </div>
    </div>

    <div v-if="message" class="alert" :class="messageType">
      {{ message }}
    </div>

    <div v-if="summaryMetrics" class="kpi-grid">
      <div class="card kpi">
        <p class="label">提出件数</p>
        <h3>{{ summaryMetrics.totalProposals.toLocaleString() }}件</h3>
        <small>対象期に登録された改善数</small>
      </div>
      <div class="card kpi">
        <p class="label">効果金額</p>
        <h3>\{{ summaryMetrics.totalEffectAmount.toLocaleString() }}</h3>
        <small>削減・効果の金額集計</small>
      </div>
      <div class="card kpi">
        <p class="label">削減時間</p>
        <h3>{{ summaryMetrics.totalReductionHours.toLocaleString() }}h</h3>
        <small>削減された時間の合計</small>
      </div>
    </div>

    <div v-if="hasAnalytics" class="insight-grid">
      <div class="card chart-card">
        <div class="section-title">
          <h3>部門別 件数</h3>
          <span class="chip">年間累計</span>
        </div>
        <div class="chart-wrapper">
          <BarChart v-if="departmentChartData" :chart-data="departmentChartData" :chart-options="chartOptions" />
          <div v-else class="placeholder">部門データがありません</div>
        </div>
      </div>
      <div class="card chart-card">
        <div class="section-title">
          <h3>月別トレンド</h3>
          <span class="chip">提出推移</span>
        </div>
        <div class="chart-wrapper">
          <LineChart v-if="monthlyChartData" :chart-data="monthlyChartData" :chart-options="lineChartOptions" />
          <div v-else class="placeholder">月別データがありません</div>
        </div>
      </div>
      <div class="card ranking">
        <div class="section-title">
          <h3>インパクトリーダー</h3>
          <span class="chip">効果金額 Top3</span>
        </div>
        <ul>
          <li v-for="leader in topIndividuals" :key="leader.name + leader.department">
            <div>
              <p class="name">{{ leader.name }}</p>
              <p class="meta">{{ leader.department }} / {{ leader.proposals }}件 / {{ leader.reduction }}h 削減</p>
            </div>
            <strong>\{{ leader.effect.toLocaleString() }}</strong>
          </li>
          <li v-if="!topIndividuals.length" class="placeholder">データを取得してください</li>
        </ul>
      </div>
      <div class="card ranking">
        <div class="section-title">
          <h3>部門ランキング</h3>
          <span class="chip">提出件数 Top5</span>
        </div>
        <ul>
          <li v-for="(dept, index) in departmentLeaders" :key="dept.department">
            <div>
              <p class="name">{{ dept.department }}</p>
              <p class="meta">提出 {{ dept.total }}件</p>
            </div>
            <span class="pill subtle">#{{ index + 1 }}</span>
          </li>
          <li v-if="!departmentLeaders.length" class="placeholder">部門データを取得してください</li>
        </ul>
      </div>
    </div>

    <div v-if="hasAnalytics" class="tables">
      <div class="card table-card">
        <div class="section-title">
          <h3>個人別サマリー</h3>
          <span class="chip">件数・効果</span>
        </div>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>部署</th>
                <th>氏名</th>
                <th>件数</th>
                <th>マインド</th>
                <th>アイデア</th>
                <th>ヒント</th>
                <th>評価ポイント</th>
                <th>提案ポイント</th>
                <th>削減時間 (h/年)</th>
                <th>効果金額 (円)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in personSummary" :key="index">
                <td>{{ row['部署'] }}</td>
                <td>{{ row['提案者'] }}</td>
                <td>{{ row['件数'] }}</td>
                <td>{{ row['平均マインド'] }}</td>
                <td>{{ row['平均アイデア'] }}</td>
                <td>{{ row['平均ヒント'] }}</td>
                <td>{{ numberOrZero(row['合計ポイント']).toLocaleString() }}</td>
                <td>{{ numberOrZero(row['提案ポイント']).toLocaleString() }}</td>
                <td>{{ row['削減時間合計[Hr/月]'] }}</td>
                <td>{{ numberOrZero(row['効果額合計[¥/月]']).toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card table-card">
        <div class="section-title">
          <h3>部門別サマリー</h3>
          <span class="chip">月別件数</span>
        </div>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>部門</th>
                <th v-for="key in visibleMonthKeys" :key="key">{{ key }}</th>
                <th>年間合計</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in departmentSummary" :key="index">
                <td>{{ row['部署'] }}</td>
                <td v-for="key in visibleMonthKeys" :key="key">{{ row[key] }}</td>
                <td>{{ row['年間合計'] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-else-if="!loadingAnalytics" class="empty">
      <p class="placeholder">期を入力して「データを表示」を押すとレポートが表示されます。</p>
    </div>
  </section>
</template>

<style scoped>
.reports {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.hero {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  background: linear-gradient(135deg, #0f172a, #1d4ed8);
  color: #eef2ff;
  border: none;
}

.hero__copy h2 {
  margin: 0.25rem 0;
  font-size: 1.8rem;
}

.lede {
  margin-top: 0.3rem;
  color: #cbd5ff;
  max-width: 640px;
}

.controls {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1rem;
  align-items: end;
  margin: 1.5rem 0 0.8rem 0;
}

.term-input {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-weight: 600;
}

.term-input input {
  padding: 0.8rem;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  font-size: 1rem;
}

.term-input select {
  padding: 0.8rem;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  font-size: 1rem;
}

.term-input select option {
  background: #fff;
  color: #0f172a;
}

.term-input input::placeholder {
  color: rgba(255, 255, 255, 0.7);
}

.hero__actions {
  display: flex;
  gap: 0.8rem;
  justify-content: flex-end;
}

.btn {
  padding: 0.8rem 1.4rem;
  border-radius: 12px;
  border: 1px solid transparent;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  transition: transform 0.1s ease, opacity 0.1s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn.primary {
  background: #fff;
  color: #0f172a;
}

.btn.ghost {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.5);
  color: #fff;
}

.btn:not(:disabled):hover {
  transform: translateY(-1px);
}

.helper {
  margin: 0.2rem 0 0;
  color: #dbeafe;
}

.hero__badge {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 14px;
  padding: 1rem 1.25rem;
  align-self: flex-end;
}

.hero__badge h3 {
  margin: 0.4rem 0 0.2rem;
  font-size: 2.25rem;
}

.eyebrow {
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-size: 0.9rem;
  color: #a5b4fc;
  margin: 0;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.75rem;
  background: rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  font-size: 0.85rem;
  color: #eef2ff;
}

.pill.subtle {
  background: #e5ebff;
  color: #1d4ed8;
}

.alert {
  padding: 0.9rem 1rem;
  border-radius: 10px;
  border: 1px solid transparent;
}

.alert.info {
  background: #ecf4ff;
  border-color: #bfdbfe;
  color: #1e3a8a;
}

.alert.error {
  background: #fff1f2;
  border-color: #fecdd3;
  color: #b91c1c;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.kpi {
  border: 1px solid #e5e7eb;
}

.kpi .label {
  color: #6b7280;
  margin: 0;
}

.kpi h3 {
  margin: 0.3rem 0 0.2rem;
  font-size: 1.8rem;
}

.kpi small {
  color: #6b7280;
}

.insight-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1rem;
}

.chart-card,
.ranking {
  border: 1px solid #e5e7eb;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.6rem;
}

.chip {
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  background: #eef2ff;
  color: #1d4ed8;
  font-size: 0.8rem;
}

.chart-wrapper {
  height: 280px;
}

.ranking ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.ranking li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.7rem 0.4rem;
  border-bottom: 1px solid #f1f5f9;
}

.ranking li:last-child {
  border-bottom: none;
}

.name {
  margin: 0;
  font-weight: 700;
  color: #111827;
}

.meta {
  margin: 0.1rem 0 0;
  color: #6b7280;
  font-size: 0.9rem;
}

.tables {
  display: grid;
  grid-template-columns: 2fr 1.2fr;
  gap: 1rem;
}

.table-card {
  border: 1px solid #e5e7eb;
}

.table-wrapper {
  overflow-x: auto;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
}

th,
td {
  padding: 0.9rem 0.8rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

th {
  background: #f8fafc;
  font-weight: 700;
  white-space: nowrap;
}

tbody tr:hover {
  background: #f3f4f6;
}

.placeholder {
  color: #9ca3af;
}

.empty {
  text-align: center;
  padding: 2rem 0;
}

@media (max-width: 1024px) {
  .controls {
    grid-template-columns: 1fr;
  }
  .hero__actions {
    justify-content: flex-start;
  }
  .tables {
    grid-template-columns: 1fr;
  }
}
</style>
