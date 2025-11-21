import { createRouter, createWebHistory } from 'vue-router'
import SubmitForm from '../pages/SubmitForm.vue'
import ProposalList from '../pages/ProposalList.vue'
import ApprovalCenter from '../pages/ApprovalCenter.vue'
import ConfirmedList from '../pages/ConfirmedList.vue'
import ReportsPage from '../pages/ReportsPage.vue'
import AnalyticsPage from '../pages/AnalyticsPage.vue'
import LoginPage from '../pages/LoginPage.vue'
import { useAuth } from '../stores/auth'

const routes = [
  { path: '/', redirect: '/submit' },
  { path: '/login', component: LoginPage, meta: { requiresAuth: false, title: 'ログイン' } },
  { path: '/submit', component: SubmitForm, meta: { title: '提出フォーム' } },
  { path: '/proposals', component: ProposalList, meta: { title: '提出済み一覧' } },
  { path: '/approvals', component: ApprovalCenter, meta: { title: '承認センター' } },
  { path: '/confirmed', component: ConfirmedList, meta: { title: '確認済み一覧' } },
  { path: '/reports', component: ReportsPage, meta: { title: 'レポート' } },
  { path: '/analytics', component: AnalyticsPage, meta: { title: '分析・レポート' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const auth = useAuth()
  if (!auth.state.initialized) {
    await auth.init()
  }
  if (to.meta?.requiresAuth === false) {
    if (to.path === '/login' && auth.state.isAuthenticated) {
      return next('/submit')
    }
    return next()
  }
  if (!auth.state.isAuthenticated) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }
  return next()
})

router.afterEach((to) => {
  if (to.meta?.title) {
    document.title = `改善提案 - ${to.meta.title}`
  }
})

export default router
