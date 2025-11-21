<script setup>
import { ref } from 'vue'
import { fetchAnalytics, exportTermReport } from '../api/client'

const term = ref('')
const message = ref('')
const loading = ref(false)
const downloading = ref(false)
const analyticsData = ref(null)

const loadAnalytics = async () => {
  if (!term.value) {
    message.value = '期を入力してください'
    return
  }
  loading.value = true
  message.value = ''
  analyticsData.value = null
  try {
    analyticsData.value = await fetchAnalytics(term.value)
  } catch (error) {
    message.value = error.message ?? 'データの取得に失敗しました'
  } finally {
    loading.value = false
  }
}

const download = async () => {
  if (!term.value) {
    message.value = '期を入力してください'
    return
  }
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
    message.value = error.message ?? 'レポートの生成に失敗しました'
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <section class="card analytics">
    <header class="section-header">
      <div>
        <h2>📊 分析・レポート</h2>
        <p>期を指定して集計データを表示・ダウンロードします。</p>
      </div>
    </header>

    <div v-if="message" class="alert error">{{ message }}</div>

    <div class="controls">
      <label>
        期 (例: 53)
        <input v-model.number="term" type="number" min="1" placeholder="53" @keyup.enter="loadAnalytics" />
      </label>
      <button :disabled="loading" @click="loadAnalytics" class="btn-primary">
        {{ loading ? '読み込み中…' : '表示' }}
      </button>
      <button :disabled="downloading" @click="download" class="btn-secondary">
        {{ downloading ? '生成中…' : 'Excelダウンロード' }}
      </button>
    </div>

    <div v-if="analyticsData" class="results">
      <h3>部署別氏名一覧</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>部署</th>
              <th>提案者</th>
              <th>件数</th>
              <th>平均マインド</th>
              <th>平均アイデア</th>
              <th>平均ヒント</th>
              <th>削減時間合計</th>
              <th>効果額合計</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in analyticsData.person_summary" :key="i">
              <td>{{ row['部署'] }}</td>
              <td>{{ row['提案者'] }}</td>
              <td>{{ row['件数'] }}</td>
              <td>{{ row['平均マインド'] }}</td>
              <td>{{ row['平均アイデア'] }}</td>
              <td>{{ row['平均ヒント'] }}</td>
              <td>{{ row['削減時間合計[Hr/月]'] }}</td>
              <td>{{ Number(row['効果額合計[¥/月]']).toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3>特殊ポイント判定 (部署別月次集計)</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>部署</th>
              <th v-for="key in Object.keys(analyticsData.department_summary[0] || {}).filter(k => k !== '部署' && k !== '年間合計')" :key="key">
                {{ key }}
              </th>
              <th>年間合計</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in analyticsData.department_summary" :key="i">
              <td>{{ row['部署'] }}</td>
              <td v-for="key in Object.keys(row).filter(k => k !== '部署' && k !== '年間合計')" :key="key">
                {{ row[key] }}
              </td>
              <td>{{ row['年間合計'] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<style scoped>
.controls {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  margin-bottom: 2rem;
}
input {
  padding: 0.6rem;
  border-radius: 8px;
  border: 1px solid #d4dbe5;
  font-size: 1rem;
  width: 100px;
}
button {
  padding: 0.7rem 1.4rem;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-weight: bold;
}
.btn-primary {
  background: #1d4ed8;
  color: white;
}
.btn-secondary {
  background: #10b981;
  color: white;
}
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.results h3 {
  margin-top: 2rem;
  margin-bottom: 1rem;
  border-left: 4px solid #1d4ed8;
  padding-left: 0.5rem;
}

.table-wrapper {
  overflow-x: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

th, td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

th {
  background-color: #f9fafb;
  font-weight: 600;
  white-space: nowrap;
}

tr:hover {
  background-color: #f3f4f6;
}
</style>
