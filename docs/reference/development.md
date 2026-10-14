# 开发与文档

问卷工具与文档站各自运行。维护文档不会给 Python 工具增加 Node.js 依赖。

## 运行工具与测试

```sh
python server.py
```

在项目根目录执行回归测试：

```sh
python -m unittest discover -s tests -v
node --test tests/test_web.cjs
```

测试使用构造数据和临时数据库，不依赖本机研究问卷。

## 预览文档

文档使用 VitePress 1.6.4。准备 Node.js 22 或更新版本，在根目录执行：

```sh
npm ci
npm run docs:dev
```

打开终端显示的 `/surveyjar/` 地址。修改 Markdown 后页面自动更新。

## 构建文档

```sh
npm run docs:build
npm run docs:preview
```

产物在 `docs/.vitepress/dist/`。构建时检查文档中的站内链接；缓存、产物和 `node_modules/` 不提交到 Git。

## 文档结构

```text
docs/
├── index.md                 # 首页
├── guide/                   # 面向使用者的操作说明
├── reference/               # 版本与开发说明
├── public/logo.svg          # 文档标志与 favicon
└── .vitepress/
    ├── config.mjs           # 导航、搜索、中文界面
    └── theme/               # 配色和版式
```

应用使用 `web/logo.svg`，文档使用 `docs/public/logo.svg`。两处是同一标志的静态副本；修改品牌资源时同步更新两处。

## 托管路径

文档使用 GitHub Pages 托管，访问地址为 [SurveyJar 文档](https://zh1peng.github.io/surveyjar/)，项目路径配置为 `/surveyjar/`。

GitHub Pages 使用 GitHub Actions 作为构建来源。更新文档并推送到 `main` 后，在 Actions 中手动运行 **Deploy documentation** 即可重新发布。

程序仓库与文档站均为公开。文档构建仅处理 `docs/`，不会打包 `data/` 或 `local/`。

导航与部署设置参考 [VitePress 官方文档](https://vitepress.dev/guide/deploy)。
