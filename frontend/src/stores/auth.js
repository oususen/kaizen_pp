import { reactive } from 'vue'
import { fetchCurrentEmployee, loginUser, logoutUser } from '../api/client'

const state = reactive({
  isAuthenticated: false,
  user: null, // ユーザー名
  profile: null, // ユーザープロファイル（新旧統一）
  permissions: [],
  loading: false,
  error: '',
  initialized: false,
})

const deriveDisplayName = (payload) => {
  if (!payload) return null
  return (
    payload.name ||
    payload.profile?.name ||
    payload.username ||
    payload.employee?.name ||
    payload.employee_name ||
    null
  )
}

const setAuth = (payload) => {
  if (!payload) {
    // ログアウト
    state.profile = null
    state.user = null
    state.permissions = []
    state.isAuthenticated = false
    return
  }

  const displayName = deriveDisplayName(payload)

  // 旧システムのレスポンス形式: { username, employee: {...} }
  // 新形式 (state.profile) に統一するため変換する
  if (payload?.employee) {
    const emp = payload.employee
    // 旧形式を新形式に変換
    state.user = payload.username ?? emp.name ?? null
    state.profile = {
      ...(payload.profile || {}),
      name: displayName || emp.name,
      role: emp.profile?.role || emp.role,
      responsible_department: emp.profile?.responsible_department || emp.department,
      responsible_department_detail: emp.profile?.responsible_department_detail || emp.department_detail,
      // 旧システム用の後方互換フィールド
      _legacy: emp,
    }
    state.permissions = emp.permissions || []
  }
  // 新レスポンス形式: { username, profile: {...}, permissions: [...] }
  else if (payload?.username) {
    state.user = payload.username
    state.profile = {
      ...(payload.profile || {}),
      name: displayName || payload.username,
    }
    state.permissions = payload.permissions || []
  }
  // その他の形式
  else {
    const fallbackName = displayName || payload.name || payload.username || null
    state.user = payload.username ?? fallbackName
    state.profile = {
      ...(payload.profile || {}),
      name: fallbackName,
      role: payload.role,
      responsible_department: payload.department,
    }
    state.permissions = payload.permissions || []
  }

  state.isAuthenticated = Boolean(state.user)
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
  return state.profile?.role === 'admin'
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
  return perm ? perm.can_edit : false
}

export const useAuth = () => ({
  state,
  init,
  login,
  logout,
  canView,
  canEdit,
})
