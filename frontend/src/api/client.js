const API_BASE = (import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8001/api').replace(/\/$/, '')

const buildUrl = (path) => {
  const normalized = path.replace(/^\//, '')
  return `${API_BASE}/${normalized}`
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
    throw new Error(detail || 'サーバーエラーが発生しました')
  }
  return handleResponse(response)
}

export const fetchDepartments = () => request('/departments/')

export const fetchCurrentEmployee = async () => {
  try {
    return await request('/employees/me/')
  } catch (error) {
    return null
  }
}

export const fetchProposals = async (params = {}) => {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
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
  Object.entries(payload).forEach(([key, value]) => {
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

export const fetchConfirmed = () => fetchProposals({ status: 'completed' })
