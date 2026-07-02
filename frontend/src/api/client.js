import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

let accessToken = null
let refreshToken = null
let refreshTimer = null

export function setTokens(access, refresh) {
  accessToken = access
  refreshToken = refresh
  scheduleRefresh()
}

export function clearTokens() {
  accessToken = null
  refreshToken = null
  if (refreshTimer) {
    clearTimeout(refreshTimer)
    refreshTimer = null
  }
}

export function getAccessToken() {
  return accessToken
}

export function getRefreshToken() {
  return refreshToken
}

function scheduleRefresh() {
  if (refreshTimer) clearTimeout(refreshTimer)
  if (!refreshToken) return
  const delay = 9 * 60 * 1000
  refreshTimer = setTimeout(async () => {
    if (!refreshToken) return
    try {
      const res = await axios.post(`${API_BASE}/auth/refresh`, {
        refresh_token: refreshToken,
      })
      setTokens(res.data.access_token, res.data.refresh_token)
    } catch {
      clearTokens()
      window.location.href = '/login'
    }
  }, delay)
}

client.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry && refreshToken) {
      originalRequest._retry = true
      try {
        const res = await axios.post(`${API_BASE}/auth/refresh`, {
          refresh_token: refreshToken,
        })
        setTokens(res.data.access_token, res.data.refresh_token)
        originalRequest.headers.Authorization = `Bearer ${res.data.access_token}`
        return client(originalRequest)
      } catch {
        clearTokens()
        window.location.href = '/login'
        return Promise.reject(error)
      }
    }
    return Promise.reject(error)
  }
)

export default client
