<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { exportTermReport, fetchProposals, deleteProposal } from '../api/client'
import { useAuth } from '../stores/auth'

const auth = useAuth()
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
const deleteDialogOpen = ref(false)
const proposalToDelete = ref(null)

const stageLabel = (value) => stageOptions.find((option) => option.value === value)?.label ?? value

const contributorsOf = (proposal) => {
  const list = proposal?.contributors || []
  return list
    .filter((c) => c.is_primary !== true) // 主提案者以外
    .map((c, idx) => ({
      key: `${c.employee?.id || c.employee || c.employee_code || idx}`,
      name: c.employee?.name || c.employee_name || '未設定',
      code: c.employee?.code || c.employee_code || '',
      share: c.share_percent ?? '',
      primary: Boolean(c.is_primary),
    }))
}

const formatShare = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(2) : ''
}

const stageApproval = (stage) => {
  const approvals = selectedProposal.value?.approvals || []
  return approvals.find((a) => a.stage === stage)
}

const proposalPointShare = computed(() => {
  const proposal = selectedProposal.value
  const contributors = proposal?.contributors || []
  const shares = contributors
    .map((c) => Number(c.classification_points_share))
    .filter((v) => Number.isFinite(v) && v > 0)
  if (shares.length) {
    const total = shares.reduce((a, b) => a + b, 0)
    return { share: shares[0], total }
  }
  const total = Number(proposal?.classification_points)
  if (!Number.isFinite(total)) return { share: null, total: null }
  const contributorCount = Math.max(contributors.length || 1, 1)
  return { share: total / contributorCount, total }
})

const formatDate = (value) => (value ? new Date(value).toLocaleDateString('ja-JP') : '')

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

const normalizedImages = (kind) => {
  const proposal = selectedProposal.value
  if (!proposal) return []
  const key = `${kind}_images`
  const images = Array.isArray(proposal[key]) ? proposal[key] : []
  if (images.length > 0) return images
  const singlePath = proposal[`${kind}_image_path`]
  return singlePath ? [{ id: `legacy-${kind}`, url: singlePath, path: singlePath, filename: singlePath }] : []
}

const beforeImages = computed(() => normalizedImages('before'))
const afterImages = computed(() => normalizedImages('after'))

const effectDepartments = (proposal) => {
  const raw = proposal?.contribution_business
  if (Array.isArray(raw)) return raw.filter(Boolean).join('、')
  if (typeof raw === 'string') {
    return raw
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
      .join('、')
  }
  return ''
}

// 班長以上の権限チェック
const canDelete = computed(() => {
  const role = auth.state.employee?.profile?.role || auth.state.employee?.role
  const allowedRoles = ['supervisor', 'chief', 'manager', 'committee', 'committee_chair', 'admin']
  return allowedRoles.includes(role)
})

const openDeleteDialog = (proposal) => {
  proposalToDelete.value = proposal
  deleteDialogOpen.value = true
}

const closeDeleteDialog = () => {
  deleteDialogOpen.value = false
  proposalToDelete.value = null
}

const confirmDelete = async () => {
  if (!proposalToDelete.value) return

  const proposalId = proposalToDelete.value.id
  loading.value = true
  message.value = ''
  try {
    await deleteProposal(proposalId)
    message.value = '提案を削除しました'

    // 選択中の提案が削除された場合は選択解除
    if (selectedProposal.value?.id === proposalId) {
      selectedProposal.value = null
    }

    closeDeleteDialog()
    await loadProposals()
  } catch (error) {
    message.value = error.message ?? '削除に失敗しました'
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
          <div class="detail-actions">
            <button v-if="canDelete" @click="openDeleteDialog(selectedProposal)" class="btn-delete">削除</button>
            <button @click="closeDetail" class="btn-back">← 戻る</button>
          </div>
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
              <div class="detail-item span" v-if="contributorsOf(selectedProposal).length">
                <label>共同提案者</label>
                <ul class="contributors">
                  <li v-for="c in contributorsOf(selectedProposal)" :key="c.key">
                    <span class="contrib-name">{{ c.name }} <small v-if="c.code">({{ c.code }})</small></span>
                    <span class="contrib-meta">
                      <span v-if="c.primary" class="pill">主</span>
                      <span v-if="c.share !== ''">{{ formatShare(c.share) }}%</span>
                    </span>
                  </li>
                </ul>
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

          <div v-if="selectedProposal.effect_details" class="detail-section">
            <h3>効果内容・効果算出</h3>
            <p class="text-content">{{ selectedProposal.effect_details }}</p>
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
              <div class="detail-item" v-if="effectDepartments(selectedProposal)">
                <label>効果部門</label>
                <span>{{ effectDepartments(selectedProposal) }}</span>
              </div>
            </div>
          </div>

          <div v-if="beforeImages.length || afterImages.length" class="detail-section">
            <h3>画像</h3>
            <div class="images-grid">
              <div v-for="image in beforeImages" :key="`before-${image.id || image.path}`" class="image-item">
                <label>改善前</label>
                <img :src="image.url || image.path || image" alt="改善前" />
              </div>
              <div v-for="image in afterImages" :key="`after-${image.id || image.path}`" class="image-item">
                <label>改善後</label>
                <img :src="image.url || image.path || image" alt="改善後" />
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
                <div v-if="stageApproval('supervisor')" class="approval-info">
                  <small>承認者: {{ stageApproval('supervisor').confirmed_name || '-' }}</small>
                  <small>日時: {{ formatDate(stageApproval('supervisor').confirmed_at) }}</small>
                  <small class="comment">コメント: {{ stageApproval('supervisor').comment || 'コメント未入力' }}</small>
                </div>
              </div>
              <div class="approval-item">
                <label>係長</label>
                <span :class="['badge', statusBadgeClass(selectedProposal.chief_status)]">
                  {{ statusBadgeText(selectedProposal.chief_status) }}
                </span>
                <div v-if="stageApproval('chief')" class="approval-info">
                  <small>承認者: {{ stageApproval('chief').confirmed_name || '-' }}</small>
                  <small>日時: {{ formatDate(stageApproval('chief').confirmed_at) }}</small>
                  <small class="comment">コメント: {{ stageApproval('chief').comment || 'コメント未入力' }}</small>
                </div>
              </div>
              <div class="approval-item">
                <label>課長/部長</label>
                <span :class="['badge', statusBadgeClass(selectedProposal.manager_status)]">
                  {{ statusBadgeText(selectedProposal.manager_status) }}
                </span>
                <div v-if="stageApproval('manager')" class="approval-info">
                  <small>承認者: {{ stageApproval('manager').confirmed_name || '-' }}</small>
                  <small>日時: {{ formatDate(stageApproval('manager').confirmed_at) }}</small>
                  <small class="comment">コメント: {{ stageApproval('manager').comment || 'コメント未入力' }}</small>
                </div>
              </div>
              <div class="approval-item">
                <label>改善委員</label>
                <span :class="['badge', statusBadgeClass(selectedProposal.committee_status)]">
                  {{ statusBadgeText(selectedProposal.committee_status) }}
                </span>
                <div v-if="stageApproval('committee')" class="approval-info">
                  <small>承認者: {{ stageApproval('committee').confirmed_name || '-' }}</small>
                  <small>日時: {{ formatDate(stageApproval('committee').confirmed_at) }}</small>
                  <small class="comment">コメント: {{ stageApproval('committee').comment || 'コメント未入力' }}</small>
                </div>
              </div>
            </div>
          </div>

          <div v-if="selectedProposal.term || selectedProposal.quarter" class="detail-section">
            <h3>期・四半期</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <label>期</label>
                <span>{{ selectedProposal.term || '-' }}</span>
              </div>
              <div class="detail-item">
                <label>四半期</label>
                <span>{{ selectedProposal.quarter ? `第${selectedProposal.quarter}四半期` : '-' }}</span>
              </div>
            </div>
          </div>

          <div v-if="selectedProposal.mindset_score || selectedProposal.idea_score || selectedProposal.hint_score" class="detail-section">
            <h3>評価基準の結果</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <label>マインドセット</label>
                <span>{{ selectedProposal.mindset_score || '-' }}点</span>
              </div>
              <div class="detail-item">
                <label>アイデア工夫</label>
                <span>{{ selectedProposal.idea_score || '-' }}点</span>
              </div>
              <div class="detail-item">
                <label>みんなのヒント</label>
                <span>{{ selectedProposal.hint_score || '-' }}点</span>
              </div>
              <div class="detail-item">
                <label>合計ポイント</label>
                <span class="total-points">{{ (selectedProposal.mindset_score || 0) + (selectedProposal.idea_score || 0) + (selectedProposal.hint_score || 0) }}点</span>
              </div>
              <div class="detail-item">
                <label>提案ポイント</label>
                <span v-if="proposalPointShare.share !== null">
                  {{ proposalPointShare.share.toFixed(2) }}点
                  <small class="comment">（総計 {{ proposalPointShare.total }}点 を均等割）</small>
                </span>
                <span v-else>-</span>
              </div>
              <div class="detail-item">
                <label>SDGs</label>
                <span>{{ stageApproval('manager')?.sdgs_flag ? '適用' : '未適用' }}</span>
              </div>
              <div class="detail-item">
                <label>安全</label>
                <span>{{ stageApproval('manager')?.safety_flag ? '適用' : '未適用' }}</span>
              </div>
            </div>
          </div>

          <div v-if="selectedProposal.proposal_classification || selectedProposal.committee_classification" class="detail-section">
            <h3>提案判定</h3>
            <div class="detail-grid">
              <div v-if="selectedProposal.proposal_classification" class="detail-item">
                <label>部課長判定</label>
                <span class="classification-badge">{{ selectedProposal.proposal_classification }}</span>
              </div>
              <div v-if="selectedProposal.committee_classification" class="detail-item">
                <label>改善委員判定</label>
                <span class="classification-badge">{{ selectedProposal.committee_classification }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="no-selection">
        <p>提案を選択すると詳細が表示されます</p>
      </div>
    </div>

    <!-- 削除確認ダイアログ -->
    <div v-if="deleteDialogOpen" class="modal-overlay" @click.self="closeDeleteDialog">
      <div class="modal">
        <h2>提案の削除</h2>
        <p class="modal-subtitle">本当にこの提案を削除しますか？</p>
        <div v-if="proposalToDelete" class="delete-confirmation">
          <p><strong>管理No:</strong> {{ proposalToDelete.management_no }}</p>
          <p><strong>テーマ:</strong> {{ proposalToDelete.deployment_item }}</p>
          <p><strong>提案者:</strong> {{ proposalToDelete.proposer_name }}</p>
        </div>
        <div class="modal-actions">
          <button type="button" @click="closeDeleteDialog" class="btn-cancel">キャンセル</button>
          <button type="button" @click="confirmDelete" class="btn-danger">削除する</button>
        </div>
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

.detail-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.btn-back {
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-back:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.btn-delete {
  padding: 0.5rem 1rem;
  border: none;
  background: #ef4444;
  color: white;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-delete:hover {
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

.contributors {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.contrib-name {
  font-weight: 600;
  color: #111827;
}

.contrib-name small {
  color: #6b7280;
}

.contrib-meta {
  display: inline-flex;
  gap: 0.4rem;
  align-items: center;
  margin-left: 0.6rem;
  color: #475569;
  font-size: 0.9rem;
}

.pill {
  display: inline-flex;
  align-items: center;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  background: #e0f2fe;
  color: #0f172a;
  font-size: 0.8rem;
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

.approval-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 0.5rem;
}

.approval-info small {
  font-size: 0.75rem;
  color: #6b7280;
}

.approval-info small.comment {
  color: #374151;
  font-weight: 500;
  margin-top: 0.3rem;
  white-space: pre-wrap;
  line-height: 1.4;
}

.total-points {
  font-weight: 700;
  color: #3b82f6;
  font-size: 1.1rem;
}

.classification-badge {
  display: inline-block;
  padding: 0.4rem 0.8rem;
  background: #dbeafe;
  color: #1e40af;
  border-radius: 6px;
  font-weight: 600;
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

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
}

.modal h2 {
  margin: 0 0 0.5rem 0;
  color: #1f2937;
  font-size: 1.5rem;
}

.modal-subtitle {
  margin: 0 0 1.5rem 0;
  color: #6b7280;
  font-size: 1rem;
}

.delete-confirmation {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.delete-confirmation p {
  margin: 0.5rem 0;
  color: #991b1b;
  font-size: 0.95rem;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.btn-cancel {
  padding: 0.6rem 1.5rem;
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  font-weight: 500;
}

.btn-cancel:hover {
  background: #f3f4f6;
}

.btn-danger {
  padding: 0.6rem 1.5rem;
  border: none;
  background: #ef4444;
  color: white;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  font-weight: 600;
}

.btn-danger:hover {
  background: #dc2626;
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
