import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import { useTheme } from './composables/useTheme'
import router from './router'

useTheme()
createApp(App).use(router).mount('#app')
