import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import BodyMatchView from '@/views/BodyMatchView.vue'
import SkillStoneView from '@/views/SkillStoneView.vue'
import SkillListView from '@/views/SkillListView.vue'
import { getOpsToken } from '@/api/ops'

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
    {
      path: '/map',
      component: () => import('@/views/MapView.vue'),
    },
    {
      path: '/ops/login',
      component: () => import('@/views/ops/OpsLoginView.vue'),
    },
    {
      path: '/ops',
      component: () => import('@/views/ops/OpsLayoutView.vue'),
      meta: { requiresOpsAuth: true },
      children: [
        {
          path: '',
          redirect: '/ops/home',
        },
        {
          path: 'home',
          component: () => import('@/views/ops/OpsHomeView.vue'),
        },
        {
          path: 'dicts',
          component: () => import('@/views/ops/OpsDictsView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  if (!to.meta.requiresOpsAuth) return true
  return getOpsToken() ? true : '/ops/login'
})

export default router
