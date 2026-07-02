<template>
  <div class="auth-container">
    <div class="auth-card glass-panel">
      <h1 class="logo-text" style="text-align:center;margin-bottom:8px;">Compliance Sentinel</h1>
      <p style="text-align:center;color:var(--text-muted);margin-bottom:24px;">Create your account</p>
      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label>Full Name</label>
          <input v-model="fullName" type="text" class="form-input" placeholder="Jane Doe" />
        </div>
        <div class="form-group">
          <label>Email</label>
          <input v-model="email" type="email" required class="form-input" placeholder="you@example.com" />
        </div>
        <div class="form-group">
          <label>Password</label>
          <input v-model="password" type="password" required class="form-input" placeholder="Min 6 characters" minlength="6" />
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <button type="submit" class="btn btn-primary" style="width:100%;margin-top:12px;" :disabled="loading">
          {{ loading ? 'Creating account...' : 'Register' }}
        </button>
      </form>
      <p style="text-align:center;margin-top:16px;color:var(--text-muted);font-size:0.85rem;">
        Already have an account? <router-link to="/login">Sign in</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const router = useRouter()
const auth = useAuthStore()

const fullName = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    await auth.register(email.value, password.value, fullName.value || undefined)
    await auth.login(email.value, password.value)
    router.push({ name: 'app' })
  } catch (e) {
    error.value = e.response?.data?.detail || 'Registration failed'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 20px;
}
.auth-card {
  width: 100%;
  max-width: 400px;
  padding: 40px 32px;
}
.form-group {
  margin-bottom: 16px;
}
.form-group label {
  display: block;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-muted);
  margin-bottom: 6px;
}
.form-input {
  width: 100%;
  padding: 10px 14px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-normal);
  font-size: 0.9rem;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;
}
.form-input:focus {
  border-color: var(--accent-primary);
}
.error-text {
  color: var(--risk-high);
  font-size: 0.85rem;
  margin: 8px 0 0;
}
</style>
