# SurveyJar GitHub 同步与本地研究材料

程序仓库：[zh1peng/surveyjar](https://github.com/zh1peng/surveyjar)。默认分支为 `main`，可见性为公开。

## 上传范围

| 内容 | 是否上传 | 说明 |
|---|---|---|
| 四个 Python 模块、`web/`、启动脚本 | 是 | 可复用的程序功能 |
| `tests/` | 是 | 构造数据的导入、计分和报表测试 |
| `examples/` | 是 | 通用模板，不含真实答卷 |
| `README.md`、`docs/`、`.gitignore` | 是 | 使用说明和统一排除规则 |
| `data/` | 否 | 问卷定义、项目设置、答卷、备份和临时渲染文件 |
| `local/` | 否 | 个人研究问卷、文献附件及研究修改记录 |
| `exports/` | 否 | 本地导出文件 |
| `.venv/`、缓存、`.env` | 否 | 本机运行环境和配置 |

通用的迫选题、物质使用题、反向计分和维度功能属于程序。具体研究的题目组合、金额版本、项目名称和参与者回答属于本地研究内容。

## 首次上传

在项目根目录执行。若已经初始化 Git，跳过 `git init`。

```sh
git init -b main
git status --short --untracked-files=all
git add .
git diff --cached --name-only
```

检查暂存清单，只应出现上表中允许上传的内容。然后提交：

```sh
git commit -m "Initial SurveyJar workbench"
```

本项目已配置 `origin`；仅在重新初始化本地仓库时需要添加远程地址。

```sh
git remote add origin https://github.com/zh1peng/surveyjar.git
git push -u origin main
```

本次整理未选定开源许可证；如需允许他人按特定条件复用，再选择并添加 LICENSE。

## 后续更新

关闭程序并备份数据库，在原文件夹执行：

```sh
git pull --ff-only
```

更新已跟踪的程序文件时，未跟踪且被排除的 `data/` 和 `local/` 通常保留。如果你也修改了程序源码，应先提交修改，再处理分支差异；`--ff-only` 遇到分叉会停止。

自己修改程序后，用 `git add .`、`git diff --cached --name-only`、`git commit` 和 `git push` 同步。研究设置请在应用中修改并保存到数据库，不要直接改写共享源码来保存个人题目。

不要使用 `git clean -fdx`，它会删除被忽略的本地文件。不要通过删除整个目录后重新下载程序来更新。

## 本地文件为什么不会上传

`.gitignore` 是共享的排除规则，作用于尚未跟踪的文件。只对自己生效的额外规则也可以写入 `.git/info/exclude`。当前项目用共享规则保护研究目录，其他人克隆后也能沿用。

已经提交过的文件不会因为加入 `.gitignore` 就自动停止跟踪。需要先用 `git rm --cached <文件>` 取消跟踪；这仍不会删除远端历史中的内容。不要用 `assume-unchanged` 或 `skip-worktree` 代替研究数据与程序分离。

`.gitignore` 不是加密，也不阻止手工上传或 `git add -f`。通过 Git 推送程序，不要将整个项目文件夹压缩上传。

## 备份和换电脑

关闭服务后备份 `data/` 与 `local/`。新电脑先克隆程序，再另行复制这两个目录。浏览器 localStorage 中尚未保存的编辑器草稿不包含在数据库备份中，应先在应用里正式保存问卷。

## 结构参考

- [GitHub 官方的文件排除说明](https://docs.github.com/en/get-started/git-basics/ignoring-files)
- [PyPA 示例项目](https://github.com/pypa/sampleproject)，参考代码、测试和根目录说明的职责划分；本项目不需要照搬其发布打包流程。
