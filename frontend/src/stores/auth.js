import { reactive } from 'vue'
import { fetchCurrentEmployee, loginUser, logoutUser } from '../api/client'

const state = reactive({
  isAuthenticated: false,
  user: null,
  employee: null,
  loading: false,
  error: '',
  initialized: false,
})

const setAuth = (payload) => {
  if (payload?.employee) {
    state.employee = payload.employee
    state.user = payload.username ?? payload.employee?.name ?? null
  } else if (payload) {
    state.employee = payload
    state.user = payload?.name ?? null
  } else {
    state.employee = null
    state.user = null
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

export const useAuth = () => ({
  state,
  init,
  login,
  logout,
})
