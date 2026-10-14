# SurveyJar · 本地问卷工具

<img src="docs/public/logo.svg" width="96" height="96" alt="SurveyJar 标志">

当前版本：**0.1.0**。

在本机创建、导入和填写问卷，管理研究项目与批量作答，导出计分宽表。使用 Python 标准库、SQLite 和原生 HTML/CSS/JavaScript，无第三方依赖，无须安装 npm 或构建前端。

**[文档网站与图文使用指南 →](https://zh1peng.github.io/surveyjar/)**

## 启动

安装 Python 3.10 或更新版本，在 Windows 双击 `启动SurveyJar.cmd`，或在项目根目录运行：

```sh
python server.py
```

浏览器自动打开 http://127.0.0.1:8765 。关闭命令窗口即可停止服务。首次启动自动创建空数据库。

## 使用

1. 新建问卷，或导入 TXT、JSON、DOCX 后核对题目和计分规则。
2. 单独填写，或在「项目与批量填写」安排多份问卷的填写顺序。
3. 在「收集结果」预览并导出 CSV。

通用导入模板见 [examples](examples/)，完整操作与计分说明见 [使用指南](docs/usage.md)。演示题目只用于说明程序格式，不是经过验证的测量工具。专业量表的版本、使用授权及计分规则需自行核对。

## 目录

```text
surveyjar/
├── server.py                # 启动入口、HTTP API 和数据库访问
├── import_questionnaire.py  # TXT / DOCX 解析
├── scoring.py               # 题目、维度和总分计算
├── reporting.py             # 合并宽表导出
├── web/                     # 浏览器界面
├── tests/                   # 使用构造数据的单元测试
├── examples/                # 可共享的通用导入模板
├── docs/                    # 使用与开发文档
├── 启动SurveyJar.cmd         # Windows 启动入口
├── data/                    # 本地数据库及备份，不上传
└── local/                   # 本地研究材料和记录，不上传
```

后端只有四个模块，保留平铺布局和原启动命令。当前没有打包发布需求，因此不引入 `src/` 安装步骤、依赖管理器或额外框架。

## 本地研究与程序同步

Git 只跟踪程序、测试、模板和文档。`.gitignore` 排除 `data/`、`local/`、`exports/`、虚拟环境及缓存。

问卷、项目设置、正式答卷和填写草稿保存在 `data/questionnaires.sqlite3`。个人文档放入 `local/materials/`，研究修改记录放入 `local/notes/`，导出结果放入 `exports/` 或项目目录以外。

GitHub 上的程序仓库不备份本地研究数据。更换电脑时，应另外迁移数据库和研究材料。
