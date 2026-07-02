import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { setTokens, clearTokens, getAccessToken, getRefreshToken } from '../api/client.js'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const isAuthenticated = computed(() => !!getAccessToken())

  async function register(email, password, fullName) {
    const res = await api.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    })
    return res.data
  }

  async function login(email, password) {
    const res = await api.post('/auth/login', { email, password })
    setTokens(res.data.access_token, res.data.refresh_token)
    await fetchUser()
  }

  async function fetchUser() {
    try {
      const res = await api.get('/auth/me')
      user.value = res.data
    } catch {
      user.value = null
    }
  }

  function logout() {
    const rt = getRefreshToken()
    if (rt) {
      api.post('/auth/logout', { refresh_token: rt }).catch(() => {})
    }
    clearTokens()
    user.value = null
  }

  return { user, isAuthenticated, register, login, fetchUser, logout }
})
