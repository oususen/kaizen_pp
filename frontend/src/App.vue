<script setup>
import { ref, reactive, onMounted, computed } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api'

const stageOptions = [
  { value: 'supervisor', label: '班長' },
  { value: 'chief', label: '係長' },
  { value: 'manager', label: '課長/部長' },
  { value: 'committee', label: '改善委員' },
]

const statusOptions = [
  { value: 'pending', label: '未確認' },
  { value: 'approved', label: '承認' },
  { value: 'rejected', label: '差戻し' },
]

const departments = ref([])
const proposals = ref([])
const loading = ref(false)
const message = ref('')
const selectedStage = ref('')
const selectedStatus = ref('')

const proposalForm = reactive({
  management_no: '',
  title: '',
  proposer_name: '',
  proposer_email: '',
  department: '',
  team_name: '',
  problem: '',
  idea: '',
  expected_effect: '',
  contribution_business: '',
  reduction_hours: '',
  effect_amount: '',
})

const approvalForm = reactive({
  proposalId: null,
  stage: '',
  status: 'approved',
  comment: '',
  mindset: 3,
  idea: 3,
  hint: 3,
})

const currentSummary = computed(() => {
  const total = proposals.value.length
  const approved = proposals.value.filter((p) => p.committee_status === 'approved').length
  return `登録件数: ${total} 件 / 最終承認: ${approved} 件`
})

const fetchJSON = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail ?? 'リクエストに失敗しました')
  }
  return response.json()
}

const loadDepartments = async () => {
  const data = await fetchJSON(`${API_BASE}/departments/`)
  departments.value = data
}

const loadProposals = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (selectedStage.value) params.set('stage', selectedStage.value)
    if (selectedStatus.value) params.set('status', selectedStatus.value)
    const list = await fetchJSON(`${API_BASE}/proposals/?${params.toString()}`)
    proposals.value = list.results ?? list
  } catch (error) {
    message.value = error.message
  } finally {
    loading.value = false
  }
}

const resetProposalForm = () => {
  Object.assign(proposalForm, {
    management_no: new Date().getTime().toString(),
    title: '',
    proposer_name: '',
    proposer_email: '',
    department: '',
    team_name: '',
    problem: '',
    idea: '',
    expected_effect: '',
    contribution_business: '',
    reduction_hours: '',
    effect_amount: '',
  })
}

const submitProposal = async () => {
  if (!proposalForm.title || !proposalForm.proposer_name || !proposalForm.department) {
    message.value = '必須項目を入力してください'
    return
  }
  try {
    await fetchJSON(`${API_BASE}/proposals/`, {
      method: 'POST',
      body: JSON.stringify(proposalForm),
    })
    message.value = '提案を登録しました'
    resetProposalForm()
    loadProposals()
  } catch (error) {
    message.value = error.message
  }
}

const openApprovalForm = (proposal, stage) => {
  approvalForm.proposalId = proposal.id
  approvalForm.stage = stage
  approvalForm.status = proposal[`${stage}_status`] ?? 'approved'
  approvalForm.comment = proposal[`${stage}_comment`] ?? ''
  approvalForm.mindset = proposal.manager_mindset_score ?? 3
  approvalForm.idea = proposal.manager_idea_score ?? 3
  approvalForm.hint = proposal.manager_hint_score ?? 3
}

const submitApproval = async () => {
  if (!approvalForm.proposalId || !approvalForm.stage) return
  try {
    const payload = {
      stage: approvalForm.stage,
      status: approvalForm.status,
      comment: approvalForm.comment,
    }
    if (approvalForm.stage === 'manager') {
      payload.score = {
        mindset: Number(approvalForm.mindset),
        idea: Number(approvalForm.idea),
        hint: Number(approvalForm.hint),
      }
    }
    await fetchJSON(`${API_BASE}/proposals/${approvalForm.proposalId}/approve/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    message.value = '承認ステータスを更新しました'
    approvalForm.proposalId = null
    await loadProposals()
  } catch (error) {
    message.value = error.message
  }
}

const stageLabel = (proto) => {
  const stage = proto.current_stage
  const found = stageOptions.find((opt) => opt.value === stage)
  return found ? found.label : '完了'
}

onMounted(async () => {
  await loadDepartments()
  resetProposalForm()
  await loadProposals()
})
</script>

<template>
  <main class="page">
    <header>
      <h1>改善提案ワークフロー</h1>
      <p class="summary">{{ currentSummary }}</p>
      <p v-if="message" class="message">{{ message }}</p>
    </header>

    <section class="card">
      <h2>新規提案登録</h2>
      <form @submit.prevent="submitProposal" class="grid">
        <label>
          管理No
          <input v-model="proposalForm.management_no" required />
        </label>
        <label>
          タイトル*
          <input v-model="proposalForm.title" required />
        </label>
        <label>
          提案者*
          <input v-model="proposalForm.proposer_name" required />
        </label>
        <label>
          メール
          <input v-model="proposalForm.proposer_email" type="email" />
        </label>
        <label>
          部門*
          <select v-model="proposalForm.department" required>
            <option value="">選択してください</option>
            <option v-for="dept in departments" :key="dept.id" :value="dept.id">
              {{ dept.name }} ({{ dept.level }})
            </option>
          </select>
        </label>
        <label>
          担当班
          <input v-model="proposalForm.team_name" />
        </label>
        <label class="span">
          困りごと・問題点*
          <textarea v-model="proposalForm.problem" required rows="3" />
        </label>
        <label class="span">
          改善案*
          <textarea v-model="proposalForm.idea" required rows="3" />
        </label>
        <label class="span">
          期待される効果
          <textarea v-model="proposalForm.expected_effect" rows="2" />
        </label>
        <label>
          削減時間(時間)
          <input v-model="proposalForm.reduction_hours" type="number" step="0.5" min="0" />
        </label>
        <label>
          効果額(円/月)
          <input v-model="proposalForm.effect_amount" type="number" min="0" />
        </label>
        <label class="span">
          貢献事業
          <input v-model="proposalForm.contribution_business" />
        </label>
        <div class="span actions">
          <button type="submit">登録</button>
          <button type="button" class="ghost" @click="resetProposalForm">リセット</button>
        </div>
      </form>
    </section>

    <section class="card">
      <h2>提案一覧</h2>
      <div class="filters">
        <label>
          ステージ
          <select v-model="selectedStage" @change="loadProposals">
            <option value="">全て</option>
            <option v-for="opt in stageOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </label>
        <label>
          ステータス
          <select v-model="selectedStatus" @change="loadProposals">
            <option value="">全て</option>
            <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </label>
      </div>

      <table class="proposals">
        <thead>
          <tr>
            <th>管理No</th>
            <th>タイトル</th>
            <th>提案者</th>
            <th>部門</th>
            <th>現ステージ</th>
            <th>進捗</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7">読み込み中...</td>
          </tr>
          <tr v-else-if="!proposals.length">
            <td colspan="7">データがありません</td>
          </tr>
          <tr v-for="proposal in proposals" :key="proposal.id">
            <td>{{ proposal.management_no }}</td>
            <td>{{ proposal.title }}</td>
            <td>{{ proposal.proposer_name }}</td>
            <td>{{ proposal.department_detail?.name }}</td>
            <td>{{ stageLabel(proposal) }}</td>
            <td>
              班長: {{ proposal.supervisor_status }} /
              係長: {{ proposal.chief_status }} /
              課長: {{ proposal.manager_status }} /
              委員: {{ proposal.committee_status }}
            </td>
            <td class="actions">
              <button
                v-for="opt in stageOptions"
                :key="`${proposal.id}-${opt.value}`"
                @click="openApprovalForm(proposal, opt.value)"
              >
                {{ opt.label }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="approvalForm.proposalId" class="card">
      <h2>承認入力</h2>
      <p>ステージ: {{ stageOptions.find((s) => s.value === approvalForm.stage)?.label }}</p>
      <div class="approval-form">
        <label>
          ステータス
          <select v-model="approvalForm.status">
            <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </label>
        <label class="span">
          コメント
          <textarea v-model="approvalForm.comment" rows="3" />
        </label>
        <template v-if="approvalForm.stage === 'manager'">
          <label>マインドセット
            <input v-model="approvalForm.mindset" type="number" min="1" max="5" />
          </label>
          <label>アイデア工夫
            <input v-model="approvalForm.idea" type="number" min="1" max="5" />
          </label>
          <label>みんなのヒント
            <input v-model="approvalForm.hint" type="number" min="1" max="5" />
          </label>
        </template>
        <div class="span actions">
          <button @click="submitApproval">保存</button>
          <button type="button" class="ghost" @click="approvalForm.proposalId = null">閉じる</button>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
:global(body) {
  font-family: 'Segoe UI', 'Hiragino Kaku Gothic ProN', Meiryo, sans-serif;
  margin: 0;
  background: #f4f6f8;
  color: #1f2933;
}
.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem 4rem;
}
header {
  text-align: center;
  margin-bottom: 1rem;
}
.summary {
  font-weight: 600;
}
.message {
  color: #c81e1e;
}
.card {
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
  margin-bottom: 1.5rem;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}
.grid label {
  display: flex;
  flex-direction: column;
  font-size: 0.9rem;
  font-weight: 600;
  gap: 0.3rem;
}
.grid input,
.grid select,
.grid textarea {
  padding: 0.5rem;
  border: 1px solid #d5dce3;
  border-radius: 6px;
  font-size: 1rem;
}
.grid .span {
  grid-column: 1 / -1;
}
.actions {
  display: flex;
  gap: 0.5rem;
}
button {
  padding: 0.6rem 1rem;
  border-radius: 6px;
  border: none;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  font-size: 0.9rem;
}
button.ghost {
  background: #e2e8f0;
  color: #1f2933;
}
button:hover {
  opacity: 0.9;
}
.filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}
.filters label {
  display: flex;
  flex-direction: column;
  font-size: 0.85rem;
  gap: 0.3rem;
}
.filters select {
  padding: 0.4rem;
  border-radius: 6px;
}
.proposals {
  width: 100%;
  border-collapse: collapse;
}
.proposals th,
.proposals td {
  border-bottom: 1px solid #e5e7eb;
  padding: 0.6rem;
  font-size: 0.9rem;
}
.proposals th {
  background: #f8fafc;
  text-align: left;
}
.proposals td.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
.approval-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}
.approval-form label {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
</style>
