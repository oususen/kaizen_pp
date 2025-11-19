<script setup>
const navItems = [
  { to: '/submit', label: '提出フォーム' },
  { to: '/proposals', label: '提出済み一覧' },
  { to: '/approvals', label: '承認センター' },
  { to: '/confirmed', label: '確認済み一覧' },
  { to: '/reports', label: 'レポート' },
]
</script>

<template>
  <div class="layout">
    <aside>
      <h1>改善提案</h1>
      <nav>
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="nav-link" active-class="active">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  min-height: 100vh;
  background: #f4f6f8;
}
aside {
  background: #111827;
  color: #f8fafc;
  padding: 2rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}
aside h1 {
  margin: 0;
  font-size: 1.5rem;
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
  padding: 2rem;
}
@media (max-width: 960px) {
  .layout {
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
