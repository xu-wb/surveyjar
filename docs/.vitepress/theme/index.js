import DefaultTheme from 'vitepress/theme'
import AnnotatedScreenshot from './AnnotatedScreenshot.vue'
import './style.css'

export default {
  extends: DefaultTheme,
  enhanceApp({app}) {
    app.component('AnnotatedScreenshot', AnnotatedScreenshot)
  },
}
