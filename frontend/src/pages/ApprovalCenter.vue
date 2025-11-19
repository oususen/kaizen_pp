<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { approveProposal, fetchProposals } from '../api/client'

const stages = [
  { value: 'supervisor', label: '班長' },
  { value: 'chief', label: '係長' },
  { value: 'manager', label: '課長/部長' },
  { value: 'committee', label: '改善委員' },
]

const selectedStage = ref(stages[0].value)
const proposals = ref([])
const loading = ref(false)
const message = ref('')
const dialogOpen = ref(false)
const activeProposal = ref(null)

const form = reactive({
  status: 'approved',
  confirmed_name: '',
  comment: '',
  mindset: 3,
  idea: 3,
  hint: 3,
})

const needsScore = (stage) => ['manager', 'committee'].includes(stage)

const loadProposals = async () => {
  loading.value = true
  message.value = ''
  try {
    proposals.value = await fetchProposals({ stage: selectedStage.value, status: 'pending' })
  } catch (error) {
    message.value = error.message ?? '承認待ち一覧の取得に失敗しました'
  } finally {
    loading.value = false
  }
}

const openDialog = (proposal) => {
  activeProposal.value = proposal
  dialogOpen.value = true
  form.status = 'approved'
  form.confirmed_name = ''
  form.comment = ''
  form.mindset = 3
  form.idea = 3
  form.hint = 3
}

const submitApproval = async () => {
  if (!form.confirmed_name) {
    message.value = '確認者名を入力してください'
    return
  }
  const payload = {
    stage: selectedStage.value,
    status: form.status,
    comment: form.comment,
    confirmed_name: form.confirmed_name,
  }
  if (needsScore(selectedStage.value)) {
    payload.scores = {
      mindset: form.mindset,
      idea: form.idea,
      hint: form.hint,
    }
  }
  try {
    await approveProposal(activeProposal.value.id, payload)
    dialogOpen.value = false
    activeProposal.value = null
    loadProposals()
  } catch (error) {
    message.value = error.message ?? '承認処理に失敗しました'
  }
}

watch(selectedStage, loadProposals)
onMounted(loadProposals)
</script>

<template>
  <section class="card">
    <header class="section-header">
      <div>
        <h2>✅ 承認センター</h2>
        <p>役割ごとの承認待ち提案を処理します。</p>
      </div>
      <div class="stage-tabs">
        <button
          v-for="stage in stages"
          :key="stage.value"
          :class="['tab', { active: selectedStage === stage.value }]"
          @click="selectedStage = stage.value"
        >
          {{ stage.label }}
        </button>
      </div>
    </header>

    <div v-if="message" class="alert error">{{ message }}</div>
    <div v-if="loading" class="placeholder">読み込み中…</div>

    <div v-else class="cards">
      <article v-for="proposal in proposals" :key="proposal.id" class="proposal-card">
        <div class="proposal-head">
          <div>
            <h3>{{ proposal.deployment_item }}</h3>
            <p>#{{ proposal.management_no }} / {{ proposal.proposer_name }}</p>
          </div>
          <small>{{ new Date(proposal.submitted_at).toLocaleString() }}</small>
        </div>
        <p class="body">{{ proposal.problem_summary }}</p>
        <div class="meta">
          <div>
            <span>部門</span>
            <strong>{{ proposal.department_detail?.name ?? '' }}</strong>
          </div>
          <div>
            <span>削減時間</span>
            <strong>{{ proposal.reduction_hours ?? '-' }} Hr</strong>
          </div>
          <div>
            <span>効果額</span>
            <strong>¥{{ (proposal.effect_amount ?? 0).toLocaleString() }}</strong>
          </div>
        </div>
        <button class="approve" @click="openDialog(proposal)">承認/コメント</button>
      </article>
      <p v-if="!proposals.length" class="placeholder">承認待ちの提案はありません。</p>
    </div>
  </section>

  <dialog v-if="dialogOpen" open class="approval-dialog">
    <header>
      <h3>{{ stages.find((s) => s.value === selectedStage)?.label }} 承認</h3>
      <button class="ghost" @click="dialogOpen = false">閉じる</button>
    </header>
    <section v-if="activeProposal" class="dialog-body">
      <p class="title">{{ activeProposal.deployment_item }}</p>
      <textarea v-model="form.comment" rows="3" placeholder="コメント"></textarea>
      <label>
        確認者名*
        <input v-model="form.confirmed_name" type="text" required />
      </label>
      <label>
        ステータス
        <select v-model="form.status">
          <option value="approved">承認</option>
          <option value="rejected">差戻し</option>
        </select>
      </label>
      <div v-if="needsScore(selectedStage)" class="scores">
        <label>マインド
          <input v-model.number="form.mindset" type="number" min="1" max="5" />
        </label>
        <label>アイデア
          <input v-model.number="form.idea" type="number" min="1" max="5" />
        </label>
        <label>ヒント
          <input v-model.number="form.hint" type="number" min="1" max="5" />
        </label>
      </div>
      <footer>
        <button class="approve" @click="submitApproval">保存</button>
      </footer>
    </section>
  </dialog>
</template>

<style scoped>
.stage-tabs {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.tab {
  border: 1px solid #d4dbe5;
  background: #fff;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  cursor: pointer;
}
.tab.active {
  background: #1d4ed8;
  color: #fff;
  border-color: #1d4ed8;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}
.proposal-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.proposal-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.proposal-head h3 {
  margin: 0;
}
.body {
  min-height: 60px;
  color: #4b5563;
}
.meta {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  font-size: 0.85rem;
}
.approve {
  align-self: flex-end;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 8px;
  background: #16a34a;
  color: #fff;
  cursor: pointer;
}
dialog.approval-dialog {
  border: none;
  border-radius: 12px;
  padding: 1.5rem;
  width: min(420px, 90vw);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.25);
}
dialog header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.dialog-body textarea,
.dialog-body input,
.dialog-body select {
  width: 100%;
  margin-bottom: 0.8rem;
  padding: 0.5rem;
  border-radius: 6px;
  border: 1px solid #d1d5db;
}
.scores {
  display: flex;
  gap: 0.8rem;
}
footer {
  text-align: right;
}
</style>
