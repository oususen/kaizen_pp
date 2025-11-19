<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useAuth } from './stores/auth'
import { computed } from 'vue'

const navItems = [
  { to: '/submit', label: '提出フォーム' },
  { to: '/proposals', label: '提出済み一覧' },
  { to: '/approvals', label: '承認センター' },
  { to: '/confirmed', label: '確認済み一覧' },
  { to: '/reports', label: 'レポート' },
]

const auth = useAuth()
const router = useRouter()

const userLabel = computed(() => auth.state.employee?.name ?? auth.state.user ?? '未ログイン')

const handleLogout = async () => {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="layout" :class="{ 'layout--auth': auth.state.isAuthenticated }">
    <aside v-if="auth.state.isAuthenticated">
      <h1>改善提案</h1>
      <nav>
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="nav-link" active-class="active">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main>
      <header class="top-bar">
        <div class="user-info" v-if="auth.state.isAuthenticated">
          <span>{{ userLabel }}</span>
          <button class="ghost" @click="handleLogout">ログアウト</button>
        </div>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  background: #f4f6f8;
}
.layout--auth {
  display: grid;
  grid-template-columns: 260px 1fr;
}
aside {
  background: #111827;
  color: #f8fafc;
  padding: 2rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}
nav {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.nav-link {
  color: #cbd5f5;
  text-decoration: none;
  padding: 0.4rem 0.2rem;
  border-radius: 6px;
}
.nav-link.active {
  background: rgba(59, 130, 246, 0.2);
  color: #fff;
}
main {
  padding: 1.5rem;
}
.top-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 1rem;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
button {
  cursor: pointer;
}
button.ghost {
  background: transparent;
  border: 1px solid #cbd5f5;
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  color: #1f2937;
}
@media (max-width: 960px) {
  .layout--auth {
    grid-template-columns: 1fr;
  }
  aside {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
  nav {
    flex-direction: row;
    flex-wrap: wrap;
  }
}
</style>
