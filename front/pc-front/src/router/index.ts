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
      path: '/pokemon-marks',
      component: () => import('@/views/PokemonMarksView.vue'),
    },
    {
      path: '/lineups',
      component: () => import('@/views/PokemonLineupsView.vue'),
    },
    {
      path: '/lineups/:id',
      component: () => import('@/views/PokemonLineupDetailView.vue'),
    },
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
        {
          path: 'pokemon',
          component: () => import('@/views/ops/OpsPokemonView.vue'),
        },
        {
          path: 'evolution-chains',
          component: () => import('@/views/ops/OpsEvolutionChainsView.vue'),
        },
        {
          path: 'users',
          component: () => import('@/views/ops/OpsUsersView.vue'),
        },
        {
          path: 'skills',
          component: () => import('@/views/ops/OpsSkillsView.vue'),
        },
        {
          path: 'skill-stones',
          component: () => import('@/views/ops/OpsSkillStonesView.vue'),
        },
        {
          path: 'banners',
          component: () => import('@/views/ops/OpsBannersView.vue'),
        },
        {
          path: 'personalities',
          component: () => import('@/views/ops/OpsPersonalitiesView.vue'),
        },
        {
          path: 'pokemon-lineups',
          component: () => import('@/views/ops/OpsPokemonLineupsView.vue'),
        },
        {
          path: 'resonance-magic',
          component: () => import('@/views/ops/OpsResonanceMagicView.vue'),
        },
        {
          path: 'pokemon-marks',
          component: () => import('@/views/ops/OpsPokemonMarksView.vue'),
        },
        {
          path: 'marks',
          component: () => import('@/views/ops/OpsMarksView.vue'),
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
