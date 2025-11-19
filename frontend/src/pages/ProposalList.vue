<script setup>
import { ref, reactive, onMounted } from 'vue'
import { exportTermReport, fetchProposals } from '../api/client'

const stageOptions = [
  { value: '', label: 'すべて' },
  { value: 'supervisor', label: '班長' },
  { value: 'chief', label: '係長' },
  { value: 'manager', label: '課長/部長' },
  { value: 'committee', label: '改善委員' },
]

const statusOptions = [
  { value: '', label: 'すべて' },
  { value: 'pending', label: '未確認' },
  { value: 'approved', label: '承認済み' },
  { value: 'rejected', label: '差戻し' },
]

const filters = reactive({
  stage: '',
  status: '',
  term: '',
  q: '',
})

const proposals = ref([])
const loading = ref(false)
const message = ref('')

const stageLabel = (value) => stageOptions.find((option) => option.value === value)?.label ?? value

const formatDate = (value) => (value ? new Date(value).toLocaleString() : '')

const statusBadge = (proposal, stage) => proposal[`${stage}_status`]

const loadProposals = async () => {
  loading.value = true
  message.value = ''
  try {
    proposals.value = await fetchProposals(filters)
  } catch (error) {
    message.value = error.message ?? '一覧の取得に失敗しました'
  } finally {
    loading.value = false
  }
}

const downloadReport = async () => {
  if (!filters.term) {
    message.value = '期を入力してください'
    return
  }
  try {
    const blob = await exportTermReport(filters.term)
    const url = window.URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `kaizen_term_${filters.term}.xlsx`
    anchor.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    message.value = error.message ?? 'レポート出力に失敗しました'
  }
}

onMounted(loadProposals)
</script>

<template>
  <section class="card">
    <header class="section-header">
      <div>
        <h2>📋 提出済み一覧</h2>
        <p>フィルターを選択して改善提案を検索できます。</p>
      </div>
      <div class="download">
        <label>
          出力期
          <input v-model.number="filters.term" type="number" min="1" placeholder="53" />
        </label>
        <button @click="downloadReport">Excel出力</button>
      </div>
    </header>

    <div class="filters">
      <label>
        承認ステージ
        <select v-model="filters.stage" @change="loadProposals">
          <option v-for="option in stageOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>
      <label>
        ステータス
        <select v-model="filters.status" @change="loadProposals">
          <option v-for="option in statusOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>
      <label>
        キーワード
        <input v-model.trim="filters.q" type="text" placeholder="提案者やテーマで検索" @keyup.enter="loadProposals" />
      </label>
      <button class="ghost" @click="loadProposals">再読み込み</button>
    </div>

    <div v-if="message" class="alert error">{{ message }}</div>

    <div v-if="loading" class="placeholder">読み込み中です…</div>
    <table v-else class="proposals">
      <thead>
        <tr>
          <th>管理No</th>
          <th>提出日時</th>
          <th>提案者</th>
          <th>部門</th>
          <th>テーマ</th>
          <th v-for="option in stageOptions" v-if="option.value" :key="option.value">{{ option.label }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="proposal in proposals" :key="proposal.id">
          <td>{{ proposal.management_no }}</td>
          <td>{{ formatDate(proposal.submitted_at) }}</td>
          <td>{{ proposal.proposer_name }}</td>
          <td>{{ proposal.department_detail?.name ?? '' }}</td>
          <td class="title">{{ proposal.deployment_item }}</td>
          <td v-for="option in stageOptions" v-if="option.value" :key="option.value">
            <span :class="['badge', statusBadge(proposal, option.value)]">
              {{ statusBadge(proposal, option.value) ?? '---' }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}
.download {
  display: flex;
  gap: 0.6rem;
  align-items: flex-end;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
}
.filters label {
  display: flex;
  flex-direction: column;
  font-size: 0.9rem;
  gap: 0.3rem;
}
input,
select {
  padding: 0.4rem 0.6rem;
  border: 1px solid #cbd5f5;
  border-radius: 6px;
  font-size: 0.95rem;
}
.proposals {
  width: 100%;
  border-collapse: collapse;
}
.proposals th,
.proposals td {
  border-bottom: 1px solid #e5e7eb;
  padding: 0.6rem;
  vertical-align: top;
}
.proposals th {
  background: #f8fafc;
  text-align: left;
}
.title {
  min-width: 220px;
}
.badge {
  display: inline-flex;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  text-transform: uppercase;
  background: #e2e8f0;
}
.badge.approved {
  background: #dcfce7;
  color: #065f46;
}
.badge.pending {
  background: #fef3c7;
  color: #92400e;
}
.badge.rejected {
  background: #fee2e2;
  color: #991b1b;
}
.placeholder {
  padding: 1rem;
  text-align: center;
  color: #6b7280;
}
</style>
