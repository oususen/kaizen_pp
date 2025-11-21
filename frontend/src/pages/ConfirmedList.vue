<script setup>
import { ref, computed, onMounted } from 'vue'
import { fetchConfirmed } from '../api/client'

const proposals = ref([])
const selectedProposal = ref(null)
const loading = ref(false)
const message = ref('')

const formatDate = (value) => (value ? new Date(value).toLocaleString('ja-JP') : '')

const loadData = async () => {
  loading.value = true
  message.value = ''
  try {
    proposals.value = await fetchConfirmed()
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

onMounted(loadData)
</script>

<template>
  <section class="card">
    <div class="section-header">
      <div>
        <h2>✔️ 確認済み一覧</h2>
        <p>承認完了した提案の詳細を確認できます。</p>
      </div>
      <button class="ghost" @click="loadData">再読み込み</button>
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
                <label>部署</label>
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
                <span>\{{ (selectedProposal.effect_amount || 0).toLocaleString() }}/月</span>
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

          <div v-if="selectedProposal.mindset_score" class="detail-section">
            <h3>採点</h3>
            <div class="scores">
              <span>マインド: {{ selectedProposal.mindset_score }}</span>
              <span>アイデア: {{ selectedProposal.idea_score }}</span>
              <span>ヒント: {{ selectedProposal.hint_score }}</span>
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

.btn-close {
  width: 32px;
  height: 32px;
  border: none;
  background: #ef4444;
  color: white;
  border-radius: 50%;
  font-size: 1.4rem;
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
