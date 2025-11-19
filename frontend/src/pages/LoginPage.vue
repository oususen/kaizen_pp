<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuth()

const form = reactive({
  username: '',
  password: '',
})
const message = ref('')

const submit = async () => {
  message.value = ''
  if (!form.username || !form.password) {
    message.value = 'ユーザー名とパスワードを入力してください'
    return
  }
  try {
    await auth.login({ username: form.username, password: form.password })
    const redirect = route.query.redirect ?? '/submit'
    router.replace(redirect)
  } catch (error) {
    message.value = auth.state.error || error.message
  }
}
</script>

<template>
  <section class="login-card">
    <h1>改善提案 ログイン</h1>
    <p class="hint">社内アカウントでサインインしてください。</p>
    <div v-if="message" class="alert">{{ message }}</div>
    <form @submit.prevent="submit">
      <label>
        ユーザー名
        <input v-model.trim="form.username" type="text" autocomplete="username" />
      </label>
      <label>
        パスワード
        <input v-model="form.password" type="password" autocomplete="current-password" />
      </label>
      <button type="submit" :disabled="auth.state.loading">
        {{ auth.state.loading ? '送信中…' : 'ログイン' }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.login-card {
  max-width: 360px;
  margin: 4rem auto;
  padding: 2rem;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.15);
}
form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
}
label {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
input {
  padding: 0.6rem 0.8rem;
  border-radius: 8px;
  border: 1px solid #d4dbe5;
}
button {
  padding: 0.7rem;
  border-radius: 8px;
  border: none;
  background: #2563eb;
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
}
.alert {
  background: #fee2e2;
  color: #991b1b;
  padding: 0.5rem 0.8rem;
  border-radius: 8px;
}
.hint {
  color: #4b5563;
}
</style>
