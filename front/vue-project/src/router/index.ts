import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    {
      path: '/pokemon/:name',
      component: () => import('@/views/PokemonDetailView.vue'),
    },
  ],
})

export default router
