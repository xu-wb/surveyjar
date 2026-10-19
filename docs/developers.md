---
title: 开发者
description: 认识 SurveyJar 的开发与维护者，访问开发者主页和项目仓库。
outline: false
---

<script setup>
import { VPTeamMembers } from 'vitepress/theme'
import { withBase } from 'vitepress'

const members = [
  {
    avatar: 'https://github.com/xu-wb.png',
    name: 'Aster',
    title: '主要开发、维护与测试',
    desc: '参与 SurveyJar 的功能开发、维护与测试。',
    links: [
      { icon: 'github', link: 'https://github.com/xu-wb' }
    ]
  },
  {
    avatar: withBase('/team/zh1peng.png'),
    name: 'zh1peng',
    title: '项目指导与维护',
    desc: '<a href="https://zh1peng.top/" target="_blank" rel="noreferrer">访问个人主页 ↗</a><br><a href="https://github.com/zh1peng" target="_blank" rel="noreferrer">访问 GitHub 主页 ↗</a>',
    links: [{ icon: 'github', link: 'https://github.com/zh1peng' }]
  }
]
</script>

# 开发者

认识 SurveyJar 的开发与维护者，了解各自的职责与分工。

<div class="developer-cards">
  <VPTeamMembers :members="members" />
</div>

项目源码、问题反馈与开发记录可在 [SurveyJar GitHub 仓库](https://github.com/zh1peng/surveyjar) 查看。

<style scoped>
.developer-cards {
  margin: 32px 0;
}
</style>
