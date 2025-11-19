<script setup>
import { ref } from 'vue'
import { exportTermReport } from '../api/client'

const term = ref('')
const message = ref('')
const downloading = ref(false)

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
  <section class="card reports">
    <header class="section-header">
      <div>
        <h2>📊 レポート出力</h2>
        <p>期を指定して Excel レポートをダウンロードします。</p>
      </div>
    </header>

    <div v-if="message" class="alert error">{{ message }}</div>

    <div class="report-form">
      <label>
        期 (例: 53)
        <input v-model.number="term" type="number" min="1" placeholder="53" />
      </label>
      <button :disabled="downloading" @click="download">
        {{ downloading ? '生成中…' : 'ダウンロード' }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.report-form {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  max-width: 400px;
}
input {
  padding: 0.6rem;
  border-radius: 8px;
  border: 1px solid #d4dbe5;
  font-size: 1rem;
}
button {
  padding: 0.7rem 1.4rem;
  border-radius: 8px;
  border: none;
  background: #1d4ed8;
  color: white;
}
button:disabled {
  opacity: 0.6;
}
</style>
