<script setup>
import { ref, computed, onMounted } from 'vue'
import { fetchConfirmed, fetchDepartments, fetchProposals } from '../api/client'

const proposals = ref([])
const selectedProposal = ref(null)
const loading = ref(false)
const message = ref('')
const departments = ref([])
const contributorsOf = (proposal) => {
  const list = proposal?.contributors || []
  return list
    .filter((c) => c.is_primary !== true)
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


const showFilters = ref(false)

// フィルタ設定
const filters = ref({
  q: '',
  term: '',
  quarter: '',
  department: '',
  proposal_classification: '',
  mindset_score_min: '',
  idea_score_min: '',
  hint_score_min: '',
  submitted_at_from: '',
  submitted_at_to: '',
})

const classificationOptions = [
  { value: '保留提案', label: '保留提案' },
  { value: '努力提案', label: '努力提案' },
  { value: 'アイディア提案', label: 'アイディア提案' },
  { value: '優秀提案', label: '優秀提案' },
]

const formatDate = (value) => (value ? new Date(value).toLocaleDateString('ja-JP') : '')

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

const loadData = async () => {
  loading.value = true
  message.value = ''
  try {
    // フィルタパラメータを構築
    const params = {
      status: 'completed',
      ...Object.fromEntries(
        Object.entries(filters.value).filter(([_, value]) => value !== '' && value !== null)
      ),
    }

    // APIを直接呼び出してフィルタを適用
    proposals.value = await fetchProposals(params)

    if (selectedProposal.value) {
      const updated = proposals.value.find((p) => p.id === selectedProposal.value.id)
      selectedProposal.value = updated || null
    }
  } catch (error) {
    message.value = error.message ?? 'データ取得に失敗しました'
  } finally {
    loading.value = false
  }
}

const loadDepartments = async () => {
  try {
    departments.value = await fetchDepartments({ level: 'division' })
  } catch (error) {
    console.error('部門データの取得に失敗:', error)
  }
}

const applyFilters = () => {
  loadData()
}

const resetFilters = () => {
  filters.value = {
    q: '',
    term: '',
    quarter: '',
    department: '',
    proposal_classification: '',
    mindset_score_min: '',
    idea_score_min: '',
    hint_score_min: '',
    submitted_at_from: '',
    submitted_at_to: '',
  }
  loadData()
}

const toggleFilters = () => {
  showFilters.value = !showFilters.value
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

onMounted(async () => {
  await loadDepartments()
  await loadData()
})
</script>

<template>
  <section class="card">
    <div class="section-header">
      <div>
        <h2>✔️ 確認済み一覧</h2>
        <p>承認完了した提案の詳細を確認できます。</p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="toggleFilters">
          {{ showFilters ? 'フィルタを閉じる' : 'フィルタを開く' }}
        </button>
        <button class="ghost" @click="loadData">再読み込み</button>
      </div>
    </div>

    <div v-if="showFilters" class="filter-panel">
      <h3>フィルタ条件</h3>
      <div class="filter-grid">
        <div class="filter-item">
          <label>検索（管理No・提案者・テーマ）</label>
          <input v-model="filters.q" type="text" placeholder="キーワード検索" />
        </div>

        <div class="filter-item">
          <label>期</label>
          <input v-model="filters.term" type="number" placeholder="例: 1" min="1" />
        </div>

        <div class="filter-item">
          <label>四半期</label>
          <select v-model="filters.quarter">
            <option value="">すべて</option>
            <option value="1">第1四半期</option>
            <option value="2">第2四半期</option>
            <option value="3">第3四半期</option>
            <option value="4">第4四半期</option>
          </select>
        </div>

        <div class="filter-item">
          <label>部門</label>
          <select v-model="filters.department">
            <option value="">すべて</option>
            <option v-for="dept in departments" :key="dept.id" :value="dept.id">
              {{ dept.name }}
            </option>
          </select>
        </div>

        <div class="filter-item">
          <label>提案判定</label>
          <select v-model="filters.proposal_classification">
            <option value="">すべて</option>
            <option v-for="opt in classificationOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div class="filter-item">
          <label>マインドセット（以上）</label>
          <input v-model.number="filters.mindset_score_min" type="number" min="1" max="10" placeholder="例: 5" />
        </div>

        <div class="filter-item">
          <label>アイデア工夫（以上）</label>
          <input v-model.number="filters.idea_score_min" type="number" min="1" max="10" placeholder="例: 5" />
        </div>

        <div class="filter-item">
          <label>みんなのヒント（以上）</label>
          <input v-model.number="filters.hint_score_min" type="number" min="1" max="10" placeholder="例: 5" />
        </div>

        <div class="filter-item">
          <label>提出日（開始）</label>
          <input v-model="filters.submitted_at_from" type="date" />
        </div>

        <div class="filter-item">
          <label>提出日（終了）</label>
          <input v-model="filters.submitted_at_to" type="date" />
        </div>
      </div>

      <div class="filter-actions">
        <button class="btn-primary" @click="applyFilters">フィルタ適用</button>
        <button class="btn-secondary" @click="resetFilters">リセット</button>
      </div>
    </div>

    <div v-if="message" class="alert error">{{ message }}</div>
    <div v-if="loading" class="placeholder">読み込み中...</div>

    <div v-else class="content-layout">
      <div class="proposals-list">
        <div v-if="proposals.length === 0" class="no-data">確認済みの提案がありません</div>
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
            <span class="badge badge-success">確認済み</span>
          </div>
          <h3 class="proposal-title">{{ proposal.deployment_item }}</h3>
          <div class="proposal-meta">
            <span>提案者: {{ proposal.proposer_detail?.name || proposal.proposer_name }}</span>
            <span>部署: {{ proposal.department_detail?.name }}</span>
          </div>
          <div class="proposal-date">提出: {{ formatDate(proposal.submitted_at) }}</div>
        </div>
      </div>

      <div v-if="selectedProposal" class="proposal-detail">
        <div class="detail-header">
          <h2>提案詳細</h2>
          <button @click="closeDetail" class="btn-back">← 戻る</button>
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
                <label>部署</label>
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
                <span>\{{ (selectedProposal.effect_amount || 0).toLocaleString() }}/月</span>
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
                <span :class="['badge', 'badge-' + (selectedProposal.supervisor_status || 'pending')]">
                  {{ selectedProposal.supervisor_status === 'approved' ? '承認' : selectedProposal.supervisor_status === 'rejected' ? '差戻し' : '未確認' }}
                </span>
                <div v-if="stageApproval('supervisor')" class="approval-info">
                  <small>承認者: {{ stageApproval('supervisor').confirmed_name || '-' }}</small>
                  <small>日時: {{ formatDate(stageApproval('supervisor').confirmed_at) }}</small>
                  <small class="comment">コメント: {{ stageApproval('supervisor').comment || 'コメント未入力' }}</small>
                </div>
              </div>
              <div class="approval-item">
                <label>係長</label>
                <span :class="['badge', 'badge-' + (selectedProposal.chief_status || 'pending')]">
                  {{ selectedProposal.chief_status === 'approved' ? '承認' : selectedProposal.chief_status === 'rejected' ? '差戻し' : '未確認' }}
                </span>
                <div v-if="stageApproval('chief')" class="approval-info">
                  <small>承認者: {{ stageApproval('chief').confirmed_name || '-' }}</small>
                  <small>日時: {{ formatDate(stageApproval('chief').confirmed_at) }}</small>
                  <small class="comment">コメント: {{ stageApproval('chief').comment || 'コメント未入力' }}</small>
                </div>
              </div>
              <div class="approval-item">
                <label>課長/部長</label>
                <span :class="['badge', 'badge-' + (selectedProposal.manager_status || 'pending')]">
                  {{ selectedProposal.manager_status === 'approved' ? '承認' : selectedProposal.manager_status === 'rejected' ? '差戻し' : '未確認' }}
                </span>
                <div v-if="stageApproval('manager')" class="approval-info">
                  <small>承認者: {{ stageApproval('manager').confirmed_name || '-' }}</small>
                  <small>日時: {{ formatDate(stageApproval('manager').confirmed_at) }}</small>
                  <small class="comment">コメント: {{ stageApproval('manager').comment || 'コメント未入力' }}</small>
                </div>
              </div>
              <div class="approval-item">
                <label>改善委員</label>
                <span :class="['badge', 'badge-' + (selectedProposal.committee_status || 'pending')]">
                  {{ selectedProposal.committee_status === 'approved' ? '承認' : selectedProposal.committee_status === 'rejected' ? '差戻し' : '未確認' }}
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
        <p>提案を選択して詳細を表示してください</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.filter-panel {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.filter-panel h3 {
  margin: 0 0 1rem 0;
  color: #374151;
  font-size: 1.1rem;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-item label {
  font-size: 0.9rem;
  font-weight: 500;
  color: #4b5563;
}

.filter-item input,
.filter-item select {
  padding: 0.6rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.95rem;
  background: white;
}

.filter-item input:focus,
.filter-item select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.filter-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.btn-primary {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.95rem;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn-secondary {
  background: #6b7280;
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.95rem;
}

.btn-secondary:hover {
  background: #4b5563;
}

.content-layout {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 1.5rem;
  min-height: 500px;
}

.proposals-list {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
  overflow-y: auto;
  max-height: 70vh;
}

.proposal-item {
  padding: 1rem;
  border-bottom: 1px solid #e5e7eb;
  cursor: pointer;
  background: white;
  transition: background 0.2s;
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

.badge {
  padding: 0.25rem 0.6rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-success {
  background: #d1fae5;
  color: #065f46;
}

.proposal-title {
  font-size: 1rem;
  margin: 0.3rem 0;
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
  margin-top: 0.3rem;
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
  padding: 1.2rem;
  border-bottom: 2px solid #e5e7eb;
  position: sticky;
  top: 0;
  background: white;
  z-index: 10;
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

.detail-content {
  padding: 1.2rem;
}

.detail-section {
  margin-bottom: 1.8rem;
}

.detail-section h3 {
  font-size: 1.05rem;
  color: #374151;
  margin: 0 0 0.8rem 0;
  padding-bottom: 0.4rem;
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
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.image-item {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.image-item img {
  width: 100%;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
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

.placeholder {
  padding: 1rem;
  text-align: center;
  color: #6b7280;
}

.scores span {
  margin-right: 0.6rem;
  font-size: 0.9rem;
}

.approvals-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.approval-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.approval-item label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #374151;
}

.badge-approved {
  background: #d1fae5;
  color: #065f46;
}

.badge-rejected {
  background: #fee2e2;
  color: #991b1b;
}

.badge-pending {
  background: #fef3c7;
  color: #92400e;
}

.approval-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 0.3rem;
}

.approval-info small {
  font-size: 0.8rem;
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
