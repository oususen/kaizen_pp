const defaultApiBase = () => {
  // Use same host as the frontend so images and APIs work when accessed from other PCs
  if (typeof window !== 'undefined' && window.location?.origin) {
    return `${window.location.origin}/api`
  }
  return 'http://10.0.1.194:8001/api'
}

const API_BASE = (import.meta.env.VITE_API_BASE ?? defaultApiBase()).replace(/\/$/, '')

const buildUrl = (path) => {
  const normalized = path.replace(/^\//, '')
  return `${API_BASE}/${normalized}`
}

const getCsrfToken = () => {
  const name = 'csrftoken'
  const cookies = document.cookie.split(';')
  for (let cookie of cookies) {
    const trimmed = cookie.trim()
    if (trimmed.startsWith(name + '=')) {
      return trimmed.substring(name.length + 1)
    }
  }
  return null
}

const handleResponse = async (response) => {
  if (response.status === 204) {
    return null
  }
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    return response.json()
  }
  return response.blob()
}

const request = async (path, options = {}) => {
  const config = { credentials: 'include', ...options }
  const isFormData = config.body instanceof FormData
  config.headers = config.headers ?? {}

  // Add CSRF token for non-GET requests
  if (config.method && config.method !== 'GET') {
    const csrfToken = getCsrfToken()
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken
    }
  }

  if (!isFormData && config.body && !(config.body instanceof Blob)) {
    config.headers['Content-Type'] = 'application/json'
    config.body = typeof config.body === 'string' ? config.body : JSON.stringify(config.body)
  }
  const response = await fetch(buildUrl(path), config)
  if (!response.ok) {
    let detail
    try {
      const data = await response.json()
      detail = data.detail ?? JSON.stringify(data)
    } catch (error) {
      detail = response.statusText
    }
    // Provide more specific error messages
    if (response.status === 401) {
      throw new Error('認証が必要です。ログインしてください。')
    } else if (response.status === 403) {
      throw new Error('この操作を実行する権限がありません。')
    } else if (response.status === 404) {
      throw new Error('リソースが見つかりませんでした。')
    }
    throw new Error(detail || 'サーバーエラーが発生しました')
  }
  return handleResponse(response)
}

export const fetchDepartments = async (params = {}) => {
  const search = new URLSearchParams()
  Object.entries({ page_size: 200, ...params }).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.append(key, value)
    }
  })
  const query = search.toString()
  const path = query ? `/departments/?${query}` : '/departments/'
  const data = await request(path)
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

export const fetchCurrentEmployee = async () => {
  try {
    return await request('/employees/me/')
  } catch (error) {
    return null
  }
}

export const fetchMyProfile = async () => {
  return request('/users/me/')
}

export const updateMyProfile = async (payload) => {
  return request('/users/me/', {
    method: 'PATCH',
    body: payload,
  })
}

export const fetchProposals = async (params = {}) => {
  const search = new URLSearchParams()
  Object.entries({ page_size: 200, ...params }).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.append(key, value)
    }
  })
  const query = search.toString()
  const path = query ? `/improvement-proposals/?${query}` : '/improvement-proposals/'
  const data = await request(path)
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

export const createProposal = (payload) => {
  const formData = new FormData()
  const appendFiles = (files, key) => {
    if (Array.isArray(files)) {
      files.forEach((file) => {
        if (file instanceof File || file instanceof Blob) {
          formData.append(key, file)
        }
      })
    }
  }
  appendFiles(payload.before_images, 'before_images')
  appendFiles(payload.after_images, 'after_images')
  Object.entries(payload).forEach(([key, value]) => {
    if (key === 'before_images' || key === 'after_images') {
      return
    }
    if (key === 'contributors') {
      if (value !== undefined) {
        const contributorsJson = JSON.stringify(value)
        console.log('[client.js] Appending contributors to FormData:', contributorsJson)
        formData.append('contributors', contributorsJson)
      } else {
        console.log('[client.js] Contributors is undefined, not appending to FormData')
      }
      return
    }
    if (value === undefined || value === null || value === '') {
      return
    }
    if (key === 'before_image' || key === 'after_image') {
      if (value instanceof File) {
        formData.append(key, value)
      }
    } else {
      formData.append(key, value)
    }
  })
  return request('/improvement-proposals/', {
    method: 'POST',
    body: formData,
  })
}

export const updateProposal = (id, payload) => {
  const formData = new FormData()
  const appendFiles = (files, key) => {
    if (Array.isArray(files)) {
      files.forEach((file) => {
        if (file instanceof File || file instanceof Blob) {
          formData.append(key, file)
        }
      })
    }
  }
  appendFiles(payload.before_images, 'before_images')
  appendFiles(payload.after_images, 'after_images')

  Object.entries(payload).forEach(([key, value]) => {
    if (key === 'before_images' || key === 'after_images') return
    if (value === undefined || value === null || value === '') return
    if (key === 'contributors') {
      const contributorsJson = JSON.stringify(value)
      formData.append('contributors', contributorsJson)
      return
    }
    if (key === 'before_image' || key === 'after_image') {
      if (value instanceof File) {
        formData.append(key, value)
      }
    } else {
      formData.append(key, value)
    }
  })

  return request(`/improvement-proposals/${id}/`, {
    method: 'PATCH',
    body: formData,
  })
}

export const deleteProposal = (id) =>
  request(`/improvement-proposals/${id}/`, {
    method: 'DELETE',
  })

export const approveProposal = (id, payload) =>
  request(`/improvement-proposals/${id}/approve/`, {
    method: 'POST',
    body: payload,
  })

export const exportTermReport = async (term) => {
  const response = await fetch(buildUrl(`/improvement-proposals/export/?term=${term}`), {
    credentials: 'include',
  })
  if (!response.ok) {
    throw new Error('レポートの生成に失敗しました')
  }
  return response.blob()
}

export const fetchAnalytics = async (params) => {
  const query = new URLSearchParams()
  if (typeof params === 'number' || typeof params === 'string') {
    query.append('term', params)
  } else {
    if (!params?.term) throw new Error('term is required')
    query.append('term', params.term)
    if (params.department) query.append('department', params.department)
    if (params.month !== undefined && params.month !== null && params.month !== '') {
      query.append('month', params.month)
    }
  }
  return request(`/improvement-proposals/analytics/?${query.toString()}`)
}

export const fetchConfirmed = () => fetchProposals({ status: 'completed' })
export const loginUser = (credentials) =>
  request('/auth/login/', {
    method: 'POST',
    body: credentials,
  })

export const logoutUser = () =>
  request('/auth/logout/', {
    method: 'POST',
  })
export const fetchEmployees = async (params = {}) => {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.append(key, value)
    }
  })
  const query = search.toString()
  const path = query ? `/employees/?${query}` : '/employees/'
  const data = await request(path)
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

export const fetchUsers = async (params = {}) => {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.append(key, value)
    }
  })
  const query = search.toString()
  const path = query ? `/users/?${query}` : '/users/'
  const data = await request(path)
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

export const fetchPermissions = async (params = {}) => {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.append(key, value)
    }
  })
  const query = search.toString()
  const path = query ? `/permissions/?${query}` : '/permissions/'
  const data = await request(path)
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

export const updatePermission = (id, payload) =>
  request(`/permissions/${id}/`, {
    method: 'PUT',
    body: payload,
  })

export const createPermission = (payload) =>
  request('/permissions/', {
    method: 'POST',
    body: payload,
  })

export const deletePermission = (id) =>
  request(`/permissions/${id}/`, {
    method: 'DELETE',
  })

export const createUser = (payload) =>
  request('/users/', {
    method: 'POST',
    body: payload,
  })

export const updateUser = (id, payload) =>
  request(`/users/${id}/`, {
    method: 'PATCH',
    body: payload,
  })

export const deleteUser = (id) =>
  request(`/users/${id}/`, {
    method: 'DELETE',
  })

export const createEmployee = (payload) =>
  request('/employees/', {
    method: 'POST',
    body: payload,
  })

export const updateEmployee = (id, payload) =>
  request(`/employees/${id}/`, {
    method: 'PATCH',
    body: payload,
  })

export const deleteEmployee = (id) =>
  request(`/employees/${id}/`, {
    method: 'DELETE',
  })

