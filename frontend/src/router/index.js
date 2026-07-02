import { createRouter, createWebHistory } from 'vue-router'
import { getAccessToken } from '../api/client.js'

import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import AppView from '../views/AppView.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginView },
  { path: '/register', name: 'register', component: RegisterView },
  { path: '/', name: 'app', component: AppView, meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !getAccessToken()) {
    return { name: 'login' }
  }
  if ((to.name === 'login' || to.name === 'register') && getAccessToken()) {
    return { name: 'app' }
  }
})

export default router
