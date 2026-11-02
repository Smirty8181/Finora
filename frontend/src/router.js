import { createRouter, createWebHistory } from 'vue-router'
import HomePage from './views/HomePage.vue'
import AccountPage from './views/AccountPage.vue'
import StaffPage from './views/StaffPage.vue'
import StaticDemoAccountPage from './views/StaticDemoAccountPage.vue'
import StaticDemoStaffPage from './views/StaticDemoStaffPage.vue'
import { IS_STATIC_DEMO } from './config'

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/account', name: 'account', component: IS_STATIC_DEMO ? StaticDemoAccountPage : AccountPage },
    { path: '/staff', name: 'staff', component: IS_STATIC_DEMO ? StaticDemoStaffPage : StaffPage },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
