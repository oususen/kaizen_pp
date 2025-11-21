import { reactive } from 'vue'
import { fetchCurrentEmployee, loginUser, logoutUser } from '../api/client'

const state = reactive({
  isAuthenticated: false,
  user: null,
  employee: null,
  permissions: [],
  loading: false,
  error: '',
  initialized: false,
})

const setAuth = (payload) => {
  if (payload?.username) {
    // UserProfileベースのユーザー（新システム）
    state.user = payload.username
    state.employee = {
      name: payload.name || payload.username,
      profile: payload.profile,
      permissions: payload.permissions || []
    }
    state.permissions = payload.permissions || []
  } else if (payload?.employee) {
    // 従来のEmployeeベースのユーザー
    state.employee = payload.employee
    state.user = payload.username ?? payload.employee?.name ?? null
    state.permissions = payload.employee?.permissions ?? []
  } else if (payload) {
    // その他の形式
    state.employee = payload
    state.user = payload?.name ?? null
    state.permissions = payload?.permissions ?? []
  } else {
    state.employee = null
    state.user = null
    state.permissions = []
  }
  state.isAuthenticated = Boolean(state.employee)
}

const init = async () => {
  if (state.initialized) return
  state.loading = true
  try {
    const employee = await fetchCurrentEmployee()
    setAuth(employee)
  } catch (error) {
    state.error = error.message ?? ''
  } finally {
    state.initialized = true
    state.loading = false
  }
}

const login = async (credentials) => {
  state.loading = true
  state.error = ''
  try {
    const result = await loginUser(credentials)
    setAuth(result)
    return result
  } catch (error) {
    state.error = error.message ?? 'ログインに失敗しました'
    throw error
  } finally {
    state.loading = false
  }
}

const logout = async () => {
  state.loading = true
  try {
    await logoutUser()
  } catch (error) {
    console.error(error)
  } finally {
    state.loading = false
    setAuth(null)
  }
}

const defaultViewAllow = new Set(['submit', 'proposals'])

const isAdmin = () => {
  const role = state.employee?.profile?.role || state.employee?.role
  return role === 'admin'
}

const canView = (resource) => {
  if (isAdmin()) return true
  const perm = state.permissions.find((p) => p.resource === resource)
  if (perm) return perm.can_view
  return defaultViewAllow.has(resource)
}

const canEdit = (resource) => {
  if (isAdmin()) return true
  const perm = state.permissions.find((p) => p.resource === resource)
  return perm ? perm.can_edit : false // Default edit is閉じる
}

export const useAuth = () => ({
  state,
  init,
  login,
  logout,
  canView,
  canEdit,
})

