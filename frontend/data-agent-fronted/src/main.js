import { createApp } from 'vue'
import './styles/themes.css'
import App from './App.vue'
import { defaultThemeKey, isValidTheme } from './themes.js'

// 挂载前先应用主题，避免首屏闪烁
const saved = localStorage.getItem('da-theme')
const initTheme = isValidTheme(saved) ? saved : defaultThemeKey
document.documentElement.setAttribute('data-theme', initTheme)

createApp(App).mount('#app')