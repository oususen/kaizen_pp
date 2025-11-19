<script setup>
import { ref, onMounted } from 'vue'
import { fetchConfirmed } from '../api/client'

const proposals = ref([])
const loading = ref(false)
const message = ref('')

const loadData = async () => {
  loading.value = true
  try {
    proposals.value = await fetchConfirmed()
  } catch (error) {
    message.value = error.message ?? 'データ取得に失敗しました'
  } finally {
    loading.value = false
  }
}

const formatDate = (value) => (value ? new Date(value).toLocaleDateString() : '')

onMounted(loadData)
</script>

<template>
  <section class="card">
    <div class="section-header">
      <div>
        <h2>🎉 確認済み一覧</h2>
        <p>すべての承認が完了した改善提案です。</p>
      </div>
      <button class="ghost" @click="loadData">再読み込み</button>
    </div>

    <div v-if="message" class="alert error">{{ message }}</div>
    <div v-if="loading" class="placeholder">読み込み中…</div>

    <div v-else class="confirmed-list">
      <article v-for="proposal in proposals" :key="proposal.id" class="proposal">
        <header>
          <div>
            <h3>{{ proposal.deployment_item }}</h3>
            <p>#{{ proposal.management_no }} / {{ proposal.proposer_name }} / {{ formatDate(proposal.submitted_at) }}</p>
          </div>
          <div class="scores" v-if="proposal.mindset_score">
            <span>マインド: {{ proposal.mindset_score }}</span>
            <span>アイデア: {{ proposal.idea_score }}</span>
            <span>ヒント: {{ proposal.hint_score }}</span>
          </div>
        </header>
        <p>{{ proposal.problem_summary }}</p>
      </article>
      <p v-if="!proposals.length" class="placeholder">まだ確認済みの提案がありません。</p>
    </div>
  </section>
</template>

<style scoped>
.confirmed-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.proposal {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 1rem;
}
.proposal header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}
.scores span {
  font-size: 0.85rem;
  margin-right: 0.6rem;
}
</style>
