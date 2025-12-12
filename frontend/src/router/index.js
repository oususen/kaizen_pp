import { createRouter, createWebHistory } from 'vue-router'
import SubmitForm from '../pages/SubmitForm.vue'
import ProposalList from '../pages/ProposalList.vue'
import ApprovalCenter from '../pages/ApprovalCenter.vue'
import ConfirmedList from '../pages/ConfirmedList.vue'
import ReportsPage from '../pages/ReportsPage.vue'
import PermissionSettings from '../pages/PermissionSettings.vue'
import UserManagement from '../pages/UserManagement.vue'
import EmployeeManagement from '../pages/EmployeeManagement.vue'
import ProfilePage from '../pages/ProfilePage.vue'
import LoginPage from '../pages/LoginPage.vue'
import { useAuth } from '../stores/auth'

const routes = [
  { path: '/', component: SubmitForm, meta: { title: '提出フォーム' } },
  { path: '/login', component: LoginPage, meta: { requiresAuth: false, title: 'ログイン' } },
  { path: '/submit', component: SubmitForm, meta: { title: '提出フォーム' } },
  { path: '/proposals', component: ProposalList, meta: { title: '提出一覧' } },
  { path: '/proposals/edit', component: ProposalList, meta: { title: '提案編集' } },
  { path: '/approvals', component: ApprovalCenter, meta: { title: '承認センター' } },
  { path: '/confirmed', component: ConfirmedList, meta: { title: '確認済み一覧' } },
  { path: '/reports', component: ReportsPage, meta: { title: 'レポート' } },
  { path: '/permissions', component: PermissionSettings, meta: { title: '権限設定' } },
  { path: '/users', component: UserManagement, meta: { title: 'ユーザー管理' } },
  { path: '/employees', component: EmployeeManagement, meta: { title: '従業員管理' } },
  { path: '/profile', component: ProfilePage, meta: { title: 'プロフィール' } },
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

  // Permission-based access control
  const resourceMap = {
    '/': 'submit',
    '/submit': 'submit',
    '/proposals': 'proposals',
    '/proposals/edit': 'proposals',
    '/approvals': 'approvals',
    '/confirmed': 'confirmed',
    '/reports': 'reports',
    '/permissions': 'permissions',
    '/users': 'user_management',
    '/employees': 'employee_management',
    '/profile': 'profile',
  }

  const firstAllowedPath = () => {
    return Object.entries(resourceMap).find(([, res]) => auth.canView(res))?.[0] || '/login'
  }

  const resource = resourceMap[to.path]
  if (resource && !auth.canView(resource)) {
    return next(firstAllowedPath())
  }

  if (to.path === '/') {
    return next(firstAllowedPath())
  }

  return next()
})

router.afterEach((to) => {
  if (to.meta?.title) {
    document.title = `改善提案 - ${to.meta.title}`
  }
})

export default router
