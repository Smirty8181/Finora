import { createRouter, createWebHistory } from 'vue-router'
import HomePage from './views/HomePage.vue'
import AccountPage from './views/AccountPage.vue'
import StaffPage from './views/StaffPage.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/account', name: 'account', component: AccountPage },
    { path: '/staff', name: 'staff', component: StaffPage },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
