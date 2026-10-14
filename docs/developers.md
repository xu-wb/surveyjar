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
    avatar: withBase('/team/zh1peng.png'),
    name: 'zh1peng',
    title: '开发与维护',
    desc: 'SurveyJar 项目维护者。<br><a href="https://github.com/zh1peng" target="_blank" rel="noreferrer">访问 GitHub 主页 ↗</a>',
    links: [{ icon: 'github', link: 'https://github.com/zh1peng' }]
  }
]
</script>

# 开发者

认识 SurveyJar 的开发与维护者，通过卡片中的链接访问个人主页。

<div class="developer-cards">
  <VPTeamMembers :members="members" />
</div>

项目源码、问题反馈与开发记录可在 [SurveyJar GitHub 仓库](https://github.com/zh1peng/surveyjar) 查看。

<style scoped>
.developer-cards {
  margin: 32px 0;
}
</style>
