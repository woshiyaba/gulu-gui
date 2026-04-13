import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import BodyMatchView from '@/views/BodyMatchView.vue'
import SkillStoneView from '@/views/SkillStoneView.vue'
import SkillListView from '@/views/SkillListView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/body-match', component: BodyMatchView },
    { path: '/skill-stones', component: SkillStoneView },
    { path: '/skills', component: SkillListView },
    {
      path: '/pokemon/:name',
      component: () => import('@/views/PokemonDetailView.vue'),
    },
  ],
})

export default router
