import { createRouter, createWebHistory } from 'vue-router'
import SubmitForm from '../pages/SubmitForm.vue'
import ProposalList from '../pages/ProposalList.vue'
import ApprovalCenter from '../pages/ApprovalCenter.vue'
import ConfirmedList from '../pages/ConfirmedList.vue'
import ReportsPage from '../pages/ReportsPage.vue'

const routes = [
  { path: '/', redirect: '/submit' },
  { path: '/submit', component: SubmitForm, meta: { title: '提出フォーム' } },
  { path: '/proposals', component: ProposalList, meta: { title: '提出済み一覧' } },
  { path: '/approvals', component: ApprovalCenter, meta: { title: '承認センター' } },
  { path: '/confirmed', component: ConfirmedList, meta: { title: '確認済み一覧' } },
  { path: '/reports', component: ReportsPage, meta: { title: 'レポート' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  if (to.meta?.title) {
    document.title = `改善提案 - ${to.meta.title}`
  }
})

export default router
