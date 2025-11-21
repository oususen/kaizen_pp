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
const selectedProposal = ref(null)
const loading = ref(false)
const message = ref('')

const stageLabel = (value) => stageOptions.find((option) => option.value === value)?.label ?? value

const formatDate = (value) => (value ? new Date(value).toLocaleString('ja-JP') : '')

const statusBadgeClass = (status) => {
  if (status === 'approved') return 'badge-success'
  if (status === 'rejected') return 'badge-danger'
  return 'badge-pending'
}

const statusBadgeText = (status) => {
  if (status === 'approved') return '承認'
  if (status === 'rejected') return '差戻し'
  return '未確認'
}

const loadProposals = async () => {
  loading.value = true
  message.value = ''
  try {
    proposals.value = await fetchProposals(filters)
    if (selectedProposal.value) {
      // 選択中の提案を更新
      const updated = proposals.value.find(p => p.id === selectedProposal.value.id)
      if (updated) {
        selectedProposal.value = updated
      }
    }
  } catch (error) {
    message.value = error.message ?? '一覧の取得に失敗しました'
  } finally {
    loading.value = false
  }
}

const selectProposal = (proposal) => {
  selectedProposal.value = proposal
}

const closeDetail = () => {
  selectedProposal.value = null
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
        <p>提案をクリックすると詳細が表示されます。</p>
      </div>
      <div class="download">
        <label>
          出力期
          <input v-model.number="filters.term" type="number" min="1" placeholder="53" />
        </label>
        <button @click="downloadReport" class="btn-download">Excelダウンロード</button>
      </div>
    </header>

    <div v-if="message" class="alert error">{{ message }}</div>

    <div class="filters">
      <label>
        承認段階
        <select v-model="filters.stage" @change="loadProposals">
          <option v-for="opt in stageOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </label>

      <label>
        ステータス
        <select v-model="filters.status" @change="loadProposals">
          <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </label>

      <label>
        検索
        <input v-model="filters.q" @input="loadProposals" type="text" placeholder="管理No、提案者、テーマ" />
      </label>
    </div>

    <div class="content-layout">
      <div class="proposals-list">
        <div v-if="loading" class="loading">読み込み中...</div>
        <div v-else-if="proposals.length === 0" class="no-data">提案がありません</div>
        <div
          v-else
          v-for="proposal in proposals"
          :key="proposal.id"
          class="proposal-item"
          :class="{ selected: selectedProposal?.id === proposal.id }"
          @click="selectProposal(proposal)"
        >
          <div class="proposal-item-header">
            <span class="management-no">{{ proposal.management_no }}</span>
            <span :class="['status-badge', statusBadgeClass(proposal.current_stage === 'completed' ? 'approved' : proposal.supervisor_status)]">
              {{ proposal.current_stage === 'completed' ? '完了' : statusBadgeText(proposal.supervisor_status) }}
            </span>
          </div>
          <h3 class="proposal-title">{{ proposal.deployment_item }}</h3>
          <div class="proposal-meta">
            <span>提案者: {{ proposal.proposer_detail?.name || proposal.proposer_name }}</span>
            <span>部門: {{ proposal.department_detail?.name }}</span>
          </div>
          <div class="proposal-date">提出: {{ formatDate(proposal.submitted_at) }}</div>
        </div>
      </div>

      <div v-if="selectedProposal" class="proposal-detail">
        <div class="detail-header">
          <h2>提案詳細</h2>
          <button @click="closeDetail" class="btn-close">×</button>
        </div>

        <div class="detail-content">
          <div class="detail-section">
            <h3>基本情報</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <label>管理No</label>
                <span>{{ selectedProposal.management_no }}</span>
              </div>
              <div class="detail-item">
                <label>提出日時</label>
                <span>{{ formatDate(selectedProposal.submitted_at) }}</span>
              </div>
              <div class="detail-item">
                <label>提案者</label>
                <span>{{ selectedProposal.proposer_detail?.name || selectedProposal.proposer_name }}</span>
              </div>
              <div class="detail-item">
                <label>部門</label>
                <span>{{ selectedProposal.department_detail?.name }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h3>テーマ</h3>
            <p>{{ selectedProposal.deployment_item }}</p>
          </div>

          <div class="detail-section">
            <h3>問題点</h3>
            <p class="text-content">{{ selectedProposal.problem_summary }}</p>
          </div>

          <div class="detail-section">
            <h3>改善案</h3>
            <p class="text-content">{{ selectedProposal.improvement_plan }}</p>
          </div>

          <div v-if="selectedProposal.improvement_result" class="detail-section">
            <h3>改善結果</h3>
            <p class="text-content">{{ selectedProposal.improvement_result }}</p>
          </div>

          <div class="detail-section">
            <h3>効果</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <label>削減時間</label>
                <span>{{ selectedProposal.reduction_hours }} Hr/月</span>
              </div>
              <div class="detail-item">
                <label>効果額</label>
                <span>¥{{ (selectedProposal.effect_amount || 0).toLocaleString() }}/月</span>
              </div>
            </div>
          </div>

          <div v-if="selectedProposal.before_image_path || selectedProposal.after_image_path" class="detail-section">
            <h3>画像</h3>
            <div class="images-grid">
              <div v-if="selectedProposal.before_image_path" class="image-item">
                <label>改善前</label>
                <img :src="selectedProposal.before_image_path" alt="改善前" />
              </div>
              <div v-if="selectedProposal.after_image_path" class="image-item">
                <label>改善後</label>
                <img :src="selectedProposal.after_image_path" alt="改善後" />
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h3>承認状況</h3>
            <div class="approvals-grid">
              <div class="approval-item">
                <label>班長</label>
                <span :class="['badge', statusBadgeClass(selectedProposal.supervisor_status)]">
                  {{ statusBadgeText(selectedProposal.supervisor_status) }}
                </span>
              </div>
              <div class="approval-item">
                <label>係長</label>
                <span :class="['badge', statusBadgeClass(selectedProposal.chief_status)]">
                  {{ statusBadgeText(selectedProposal.chief_status) }}
                </span>
              </div>
              <div class="approval-item">
                <label>課長/部長</label>
                <span :class="['badge', statusBadgeClass(selectedProposal.manager_status)]">
                  {{ statusBadgeText(selectedProposal.manager_status) }}
                </span>
              </div>
              <div class="approval-item">
                <label>改善委員</label>
                <span :class="['badge', statusBadgeClass(selectedProposal.committee_status)]">
                  {{ statusBadgeText(selectedProposal.committee_status) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="no-selection">
        <p>提案を選択すると詳細が表示されます</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.download {
  display: flex;
  gap: 0.8rem;
  align-items: flex-end;
}

.download label {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.9rem;
}

.download input {
  width: 80px;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
}

.btn-download {
  padding: 0.5rem 1rem;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}

.btn-download:hover {
  background: #059669;
}

.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.filters label {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-weight: 600;
}

.filters select,
.filters input {
  padding: 0.6rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
}

.content-layout {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 1.5rem;
  min-height: 600px;
}

.proposals-list {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow-y: auto;
  max-height: 70vh;
  background: #f9fafb;
}

.loading,
.no-data {
  padding: 2rem;
  text-align: center;
  color: #6b7280;
}

.proposal-item {
  padding: 1rem;
  border-bottom: 1px solid #e5e7eb;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
}

.proposal-item:hover {
  background: #f3f4f6;
}

.proposal-item.selected {
  background: #dbeafe;
  border-left: 4px solid #3b82f6;
}

.proposal-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.management-no {
  font-weight: 600;
  color: #3b82f6;
  font-size: 0.9rem;
}

.status-badge {
  padding: 0.25rem 0.6rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-success {
  background: #d1fae5;
  color: #065f46;
}

.badge-danger {
  background: #fee2e2;
  color: #991b1b;
}

.badge-pending {
  background: #fef3c7;
  color: #92400e;
}

.proposal-title {
  font-size: 1rem;
  margin: 0.5rem 0;
  color: #1f2937;
  font-weight: 600;
}

.proposal-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.85rem;
  color: #6b7280;
}

.proposal-date {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: #9ca3af;
}

.proposal-detail {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  overflow-y: auto;
  max-height: 70vh;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 2px solid #e5e7eb;
  position: sticky;
  top: 0;
  background: white;
  z-index: 10;
}

.detail-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #1f2937;
}

.btn-close {
  width: 32px;
  height: 32px;
  border: none;
  background: #ef4444;
  color: white;
  border-radius: 50%;
  font-size: 1.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.btn-close:hover {
  background: #dc2626;
}

.detail-content {
  padding: 1.5rem;
}

.detail-section {
  margin-bottom: 2rem;
}

.detail-section h3 {
  font-size: 1.1rem;
  color: #374151;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e5e7eb;
}

.detail-section p {
  margin: 0;
  color: #4b5563;
  line-height: 1.6;
}

.text-content {
  white-space: pre-wrap;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.detail-item label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #6b7280;
}

.detail-item span {
  color: #1f2937;
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.image-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.image-item label {
  font-weight: 600;
  color: #374151;
}

.image-item img {
  width: 100%;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.approvals-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.approval-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 8px;
}

.approval-item label {
  font-weight: 600;
  color: #374151;
  font-size: 0.9rem;
}

.approval-item .badge {
  text-align: center;
}

.no-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  color: #9ca3af;
  font-style: italic;
}

.alert {
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.alert.error {
  background: #fee2e2;
  color: #991b1b;
}

@media (max-width: 1024px) {
  .content-layout {
    grid-template-columns: 1fr;
  }

  .proposal-detail {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 1000;
    max-height: 100vh;
    border-radius: 0;
  }
}
</style>
