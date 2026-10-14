import {readFileSync} from 'node:fs'
import {defineConfig} from 'vitepress'

const version = readFileSync(new URL('../../VERSION', import.meta.url), 'utf8').trim()

export default defineConfig({
  lang: 'zh-CN',
  title: 'SurveyJar',
  description: '本地创建、填写和整理研究问卷，让每一份回答都有据可循。',
  base: '/surveyjar/',
  lastUpdated: true,
  markdown: {codeCopyButtonTitle: '复制代码'},
  head: [['link', {rel: 'icon', type: 'image/svg+xml', href: '/surveyjar/logo.svg'}]],
  themeConfig: {
    logo: {src: '/logo.svg', alt: 'SurveyJar 标志'},
    nav: [
      {text: '入门', link: '/guide/getting-started'},
      {text: '使用指南', link: '/guide/importing'},
      {text: '计分与导出', link: '/guide/scoring'},
      {text: `v${version}`, items: [
        {text: '更新记录', link: '/reference/changelog'},
        {text: '开发与文档', link: '/reference/development'},
      ]},
    ],
    sidebar: [
      {text: '入门', items: [
        {text: '首页', link: '/'},
        {text: '工具概述', link: '/guide/introduction'},
        {text: '安装与快速开始', link: '/guide/getting-started'},
      ]},
      {text: '使用指南', items: [
        {text: '导入问卷', link: '/guide/importing'},
        {text: '编辑与题型', link: '/guide/questionnaires'},
        {text: '计分与维度', link: '/guide/scoring'},
        {text: '项目与批量填写', link: '/guide/projects'},
        {text: '结果与宽表导出', link: '/guide/results'},
      ]},
      {text: '数据与参考', items: [
        {text: '保存、备份与迁移', link: '/guide/data'},
        {text: '常见问题', link: '/guide/faq'},
        {text: '更新记录', link: '/reference/changelog'},
        {text: '开发与文档', link: '/reference/development'},
        {text: 'GitHub 同步', link: '/github-sync'},
      ]},
    ],
    outline: {label: '本页目录', level: [2, 3]},
    docFooter: {prev: '上一页', next: '下一页'},
    sidebarMenuLabel: '目录',
    skipToContentLabel: '跳转到正文',
    returnToTopLabel: '返回顶部',
    darkModeSwitchLabel: '主题',
    lightModeSwitchTitle: '切换为浅色',
    darkModeSwitchTitle: '切换为深色',
    lastUpdated: {text: '最后更新', formatOptions: {dateStyle: 'medium'}},
    socialLinks: [{icon: 'github', link: 'https://github.com/zh1peng/surveyjar'}],
    search: {
      provider: 'local',
      options: {locales: {root: {translations: {
        button: {buttonText: '搜索文档', buttonAriaLabel: '搜索文档'},
        modal: {noResultsText: '没有找到相关内容', resetButtonTitle: '清除搜索',
          displayDetails: '显示详细内容',
          footer: {selectText: '选择', navigateText: '切换', closeText: '关闭'}},
      }}}},
    },
  },
})
