<script setup>
import { ref, onMounted, computed } from 'vue'
import { fetchMyProfile, updateMyProfile, fetchDepartments } from '../api/client'

const loading = ref(false)
const saving = ref(false)
const message = ref('')
const success = ref('')
const profile = ref(null)
const departments = ref([])

const loadDepartments = async () => {
  try {
    departments.value = await fetchDepartments()
  } catch (error) {
    message.value = error.message ?? '部署データの取得に失敗しました'
  }
}

const loadProfile = async () => {
  loading.value = true
  message.value = ''
  try {
    profile.value = await fetchMyProfile()
  } catch (error) {
    message.value = error.message ?? 'プロフィール取得に失敗しました'
  } finally {
    loading.value = false
  }
}

const form = ref({
  username: '',
  name: '',
  email: '',
  role: '',
  responsible_department: '',
  profile_email: '',
  smtp_host: '',
  smtp_port: '',
  smtp_user: '',
  smtp_password: '',
})

const fillForm = () => {
  if (!profile.value) return
  form.value.username = profile.value.username || ''
  form.value.name = profile.value.name || ''
  form.value.email = profile.value.email || ''
  form.value.role = profile.value.profile?.role_display || profile.value.profile?.role || ''
  form.value.responsible_department = profile.value.profile?.responsible_department || ''
  form.value.profile_email = profile.value.profile?.email || ''
  form.value.smtp_host = profile.value.profile?.smtp_host || ''
  form.value.smtp_port = profile.value.profile?.smtp_port || ''
  form.value.smtp_user = profile.value.profile?.smtp_user || ''
  form.value.smtp_password = ''
}

const roleLabel = computed(() => form.value.role || '（未設定）')

const save = async () => {
  saving.value = true
  message.value = ''
  success.value = ''
  try {
    const payload = {
      first_name: form.value.name,
      email: form.value.email,
      profile_email: form.value.profile_email,
      profile_responsible_department: form.value.responsible_department || null,
      smtp_host: form.value.smtp_host,
      smtp_port: form.value.smtp_port || null,
      smtp_user: form.value.smtp_user,
      smtp_password: form.value.smtp_password || '',
    }
    const updated = await updateMyProfile(payload)
    profile.value = updated
    fillForm()
    success.value = 'プロフィールを更新しました'
  } catch (error) {
    message.value = error.message ?? '更新に失敗しました'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadProfile(), loadDepartments()])
  fillForm()
})
</script>

<template>
  <section class="card profile">
    <header class="section-header">
      <div>
        <h2>プロフィール編集</h2>
        <p>ユーザー基本情報と送信元メール/SMTP設定を更新できます。</p>
      </div>
    </header>

    <div v-if="message" class="alert error">{{ message }}</div>
    <div v-if="success" class="alert success">{{ success }}</div>
    <div v-if="loading" class="loading">読み込み中...</div>

    <div v-if="!loading" class="form-grid">
      <label>
        ログインID
        <input type="text" :value="form.username" disabled />
      </label>

      <label>
        ユーザー名
        <input v-model="form.name" type="text" placeholder="氏名" />
      </label>

      <label>
        受信メールアドレス（通知受信用）
        <input v-model="form.email" type="email" placeholder="user@example.com" />
      </label>

      <label>
        役職
        <input type="text" :value="roleLabel" disabled />
      </label>

      <label>
        担当部署
        <select v-model="form.responsible_department">
          <option value="">選択してください</option>
          <option v-for="dept in departments" :key="dept.id" :value="dept.id">
            {{ dept.name }}
          </option>
        </select>
        <small>役職に応じた担当部署を設定してください</small>
      </label>

      <label>
        送信元メールアドレス（送信チェック用）
        <input v-model="form.profile_email" type="email" placeholder="smtp sender email" />
      </label>

      <div class="section-span">
        <h3>SMTP設定</h3>
        <div class="grid-2">
          <label>
            SMTPホスト
            <input v-model="form.smtp_host" type="text" placeholder="smtp.example.com" />
          </label>
          <label>
            ポート
            <input v-model="form.smtp_port" type="number" min="1" placeholder="587" />
          </label>
          <label>
            SMTPユーザー
            <input v-model="form.smtp_user" type="text" placeholder="smtp user" />
          </label>
          <label>
            SMTPパスワード
            <input v-model="form.smtp_password" type="password" autocomplete="new-password" />
          </label>
        </div>
      </div>

      <div class="actions">
        <button class="btn primary" :disabled="saving" @click="save">
          {{ saving ? '更新中...' : '更新する' }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.profile {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem 1.5rem;
}
label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-weight: 600;
}
input, select {
  padding: 0.7rem 0.8rem;
  border-radius: 10px;
  border: 1px solid #d4dbe5;
  font-size: 1rem;
}
input[disabled] {
  background: #f3f4f6;
}
.section-span {
  grid-column: 1 / -1;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.grid-2 {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}
.actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
}
.btn {
  padding: 0.75rem 1.4rem;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  font-weight: 700;
}
.btn.primary {
  background: #1d4ed8;
  color: #fff;
}
.alert {
  padding: 0.8rem 1rem;
  border-radius: 10px;
}
.alert.error { background: #fff1f2; color: #b91c1c; border: 1px solid #fecdd3; }
.alert.success { background: #ecfdf3; color: #166534; border: 1px solid #bbf7d0; }
.loading {
  color: #6b7280;
}
</style>
