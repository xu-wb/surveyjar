---
title: 本地创建、填写与整理研究问卷
---

<div class="brand-intro">
  <img src="/logo.svg" alt="SurveyJar 标志：罐子中的勾选答卷" width="150" height="150">
  <div class="wordmark">Survey<span>Jar</span></div>
  <span class="edition">LOCAL QUESTIONNAIRE WORKSPACE · 0.1.0</span>
</div>

<h1 class="home-title">把问卷与回答，<br>有条理地留在本机。</h1>

<p class="intro">SurveyJar 是一个本地问卷工作台。把 TXT、JSON 或 Word 文档整理为可填写的问卷，配置计分和维度，按项目收集多份答卷，再导出供分析使用的宽表。工具使用 Python 和 SQLite，运行时无需联网。</p>

<div class="quick-links">
  <a href="./guide/getting-started.html">安装与快速开始 →</a>
  <a href="./guide/importing.html">导入已有问卷</a>
</div>

## 工作流程

<div class="workflow">
  <div><span>01 / PREPARE</span><strong>整理问卷</strong><small>导入文档或新建题目</small></div>
  <div><span>02 / CONFIGURE</span><strong>核对规则</strong><small>题型、反向与维度</small></div>
  <div><span>03 / COLLECT</span><strong>填写与保存</strong><small>草稿自动保存到本机</small></div>
  <div><span>04 / EXPORT</span><strong>导出宽表</strong><small>每次项目作答一行</small></div>
</div>

一份问卷可以单独填写，也可以加入项目，让同一位参与者按顺序完成多份问卷。问卷规则随作答保存，之后调整计分时仍能区分本次导出使用哪套规则。

## 安装后运行

安装 Python 3.10 或更新版本后，在项目根目录运行：

```sh
python server.py
```

Windows 也可以双击 **启动SurveyJar.cmd**。浏览器会打开 `http://127.0.0.1:8765`；保持服务窗口运行，关闭窗口即可停止。

::: tip 两套运行环境
使用问卷工具只需要 Python。Node.js 和 npm 仅用于维护、预览这份 VitePress 文档。
:::

## 从这里继续

| 你想做什么 | 阅读哪一页 |
| --- | --- |
| 第一次创建并填写问卷 | [安装与快速开始](./guide/getting-started) |
| 从 Word、TXT 或 JSON 开始 | [导入问卷](./guide/importing) |
| 调整题型、选项或共同题目 | [编辑与题型](./guide/questionnaires) |
| 设置反向、维度和总分 | [计分与维度](./guide/scoring) |
| 让同一被试连续填写多份问卷 | [项目与批量填写](./guide/projects) |
| 整理可供分析的数据表 | [结果与宽表导出](./guide/results) |
| 备份或换电脑 | [保存、备份与迁移](./guide/data) |

::: info 使用范围
SurveyJar 适合同一台电脑上的本地收集。它不提供在线发布、远程填写、研究人员权限或数据库加密；计分规则由使用者配置，程序不判断量表的有效性。
:::

<div class="doc-signature">SurveyJar 0.1.0 · 徐弋：主要开发、维护与测试 · zh1peng：项目指导与维护 · 数据保存在你的电脑上</div>
