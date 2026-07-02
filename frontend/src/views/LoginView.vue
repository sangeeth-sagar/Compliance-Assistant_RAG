<template>
  <div class="auth-container">
    <!-- Animated background mesh blobs -->
    <div class="bg-blob blob-1"></div>
    <div class="bg-blob blob-2"></div>
    
    <div class="auth-card glass-panel-premium animated-card">
      <div class="auth-header">
        <div class="sentinel-badge">
          <!-- Glowing Shield Lock SVG Badge -->
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="shield-lock-icon">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            <rect x="9" y="11" width="6" height="5" rx="1"/>
            <path d="M12 11V9a2 2 0 1 1 4 0v2"/>
          </svg>
        </div>
        <h1 class="auth-title">Compliance Sentinel</h1>
        <p class="auth-subtitle">Sign in to your secure workspace</p>
      </div>

      <form @submit.prevent="handleLogin" class="auth-form">
        <div class="form-group">
          <label class="form-label">Email Address</label>
          <div class="input-wrapper">
            <span class="input-icon">
              <!-- Envelope Icon -->
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                <polyline points="22,6 12,13 2,6"/>
              </svg>
            </span>
            <input 
              v-model="email" 
              type="email" 
              required 
              class="form-input" 
              placeholder="name@company.com" 
            />
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Password</label>
          <div class="input-wrapper">
            <span class="input-icon">
              <!-- Lock Icon -->
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </span>
            <input 
              v-model="password" 
              type="password" 
              required 
              class="form-input" 
              placeholder="••••••••" 
            />
          </div>
        </div>

        <div v-if="error" class="error-container">
          <svg class="error-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <p class="error-text">{{ error }}</p>
        </div>

        <button type="submit" class="btn-action btn-primary-glowing" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          <span>{{ loading ? 'Securing Connection...' : 'Sign In' }}</span>
        </button>
      </form>

      <div class="auth-footer">
        <p>
          Don't have an account? 
          <router-link to="/register" class="link-switch">Register</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    router.push({ name: 'app' })
  } catch (e) {
    error.value = e.response?.data?.detail || 'Authentication failed. Please verify credentials.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  width: 100%;
  padding: 20px;
  background-color: #08090c;
  overflow: hidden;
  box-sizing: border-box;
}

/* Background animated mesh/gradient blobs */
.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.15;
  z-index: 0;
  animation: float 16s infinite alternate ease-in-out;
}

.blob-1 {
  width: 400px;
  height: 400px;
  background: var(--accent-primary);
  top: -10%;
  left: 10%;
  animation-duration: 20s;
}

.blob-2 {
  width: 350px;
  height: 350px;
  background: #bc3efc;
  bottom: 5%;
  right: 15%;
  animation-duration: 16s;
  animation-delay: -4s;
}

@keyframes float {
  0% {
    transform: translate(0, 0) scale(1);
  }
  50% {
    transform: translate(40px, 30px) scale(1.15);
  }
  100% {
    transform: translate(-30px, -20px) scale(0.9);
  }
}

/* Premium Glassmorphic card */
.glass-panel-premium {
  position: relative;
  width: 100%;
  max-width: 440px;
  background: rgba(18, 22, 30, 0.6);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 48px 40px;
  box-shadow: 
    0 20px 40px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  z-index: 1;
  box-sizing: border-box;
  transition: border-color 0.3s, box-shadow 0.3s;
}

.glass-panel-premium:hover {
  border-color: rgba(56, 139, 253, 0.25);
  box-shadow: 
    0 20px 40px rgba(0, 0, 0, 0.5),
    0 0 30px rgba(47, 129, 247, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

/* Card entry animation */
.animated-card {
  animation: slideIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Header & branding */
.auth-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: 36px;
}

.sentinel-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  background: radial-gradient(circle at center, rgba(47, 129, 247, 0.15) 0%, rgba(8, 9, 12, 0) 70%);
  border: 1px solid rgba(47, 129, 247, 0.25);
  border-radius: 16px;
  color: var(--accent-primary);
  margin-bottom: 16px;
  box-shadow: 0 0 15px rgba(47, 129, 247, 0.2);
}

.shield-lock-icon {
  width: 28px;
  height: 28px;
}

.auth-title {
  font-size: 1.6rem;
  font-weight: 800;
  margin: 0;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.auth-subtitle {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin: 6px 0 0 0;
  font-weight: 400;
}

/* Form controls */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-normal);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
}

.input-icon {
  position: absolute;
  left: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  color: var(--text-muted);
  pointer-events: none;
  transition: color 0.2s;
}

.form-input {
  width: 100%;
  padding: 12px 14px 12px 42px;
  background: rgba(13, 15, 20, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  color: var(--text-bright);
  font-size: 0.95rem;
  outline: none;
  box-sizing: border-box;
  transition: all 0.2s ease;
}

.form-input:focus {
  border-color: var(--accent-primary);
  background: rgba(13, 15, 20, 0.9);
  box-shadow: 0 0 12px rgba(47, 129, 247, 0.15);
}

.form-input:focus + .input-icon,
.input-wrapper:focus-within .input-icon {
  color: var(--accent-primary);
}

/* Error message containers */
.error-container {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255, 90, 96, 0.08);
  border: 1px solid rgba(255, 90, 96, 0.15);
  border-radius: 10px;
  padding: 12px 16px;
  margin-top: 4px;
}

.error-icon {
  width: 18px;
  height: 18px;
  color: var(--risk-high);
  flex-shrink: 0;
}

.error-text {
  font-size: 0.85rem;
  color: #ff858a;
  margin: 0;
  line-height: 1.4;
}

/* Call to Action Button */
.btn-action {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  height: 48px;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  box-sizing: border-box;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.btn-primary-glowing {
  background: linear-gradient(135deg, #388bfd 0%, #1f6feb 100%);
  color: #ffffff;
  box-shadow: 0 4px 14px rgba(31, 111, 235, 0.3);
}

.btn-primary-glowing:hover:not(:disabled) {
  background: linear-gradient(135deg, #58a6ff 0%, #388bfd 100%);
  box-shadow: 0 6px 20px rgba(31, 111, 235, 0.45);
  transform: translateY(-1px);
}

.btn-primary-glowing:active:not(:disabled) {
  transform: translateY(1px) scale(0.98);
  box-shadow: 0 2px 8px rgba(31, 111, 235, 0.2);
}

.btn-primary-glowing:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}

/* Spinner loader */
.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #ffffff;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Footer / Switch links */
.auth-footer {
  margin-top: 32px;
  text-align: center;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.auth-footer p {
  margin: 0;
}

.link-switch {
  color: var(--accent-primary);
  font-weight: 600;
  margin-left: 4px;
  transition: color 0.2s;
  position: relative;
}

.link-switch::after {
  content: '';
  position: absolute;
  width: 100%;
  transform: scaleX(0);
  height: 1px;
  bottom: -2px;
  left: 0;
  background-color: var(--accent-primary);
  transform-origin: bottom right;
  transition: transform 0.25s ease-out;
}

.link-switch:hover {
  color: #58a6ff;
}

.link-switch:hover::after {
  transform: scaleX(1);
  transform-origin: bottom left;
  background-color: #58a6ff;
}
</style>
