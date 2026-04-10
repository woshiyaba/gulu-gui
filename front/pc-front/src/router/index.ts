import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import BodyMatchView from '@/views/BodyMatchView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/body-match', component: BodyMatchView },
    {
      path: '/pokemon/:name',
      component: () => import('@/views/PokemonDetailView.vue'),
    },
  ],
})

export default router
