---
id: savour-trigger-imgs-readme
title: savour 图片入口

module: savour
submodule: guide
topic: guide

type: note
status: active
canonical: true

summary: savour 图片发布入口。

parents: []
related: []

tags:
- savour

audience:
- self
- internal
languages:
- zh

maturity: evolving
confidence: null

visibility: public
source_of_truth: site

filename_policy: entrypoint

created: null
updated: '2026-11-05'
metadata_updated: '2026-11-05'
---
# savour 图片入口

把图片上传到 **`fivsevn/fivsevn-savour` 的 `trigger_imgs/`**，提交并推送到 `main` 即可发布。

1. 每批保存前，先在 Working Copy 或 GitHub Desktop 同步该仓库的最新 `main`。
2. 确认快捷指令把图片保存到该本地仓库根目录的 `trigger_imgs/`，保留手机原文件名；电脑上传也放入同一目录。
3. 在 Working Copy 或 GitHub Desktop 中提交并推送到 `main`。配文写在提交的 **可选详细说明（extended description）** 中，支持 Markdown；留空则只发图。仅打开 app 或复制提交信息不等于已经推送。
4. 等待 [Build and deploy Savour](https://github.com/fivsevn/fivsevn-savour/actions/workflows/build.yml) 完成，打开 [savour](https://savour.fivsevn.com/) 核对图片和配文。

> **格式与批量**：支持 JPG/JPEG、PNG、WebP、GIF、HEIC/HEIF。一次上传多张，每张各发一帖，共用这次配文。
>
> **自动处理**：按上传提交的北京时间命名、转为 WebP、自动补齐统一资料、逐图建帖并发布；核验线上页面和图片后清理入口原图，日常发布不改写 Git 历史。失败时保留原图，同次提交重跑会沿用已有帖子。
>
> **修改旧帖**：编辑 `savour/` 下对应帖子的 `index.md`；重新上传图片会生成新帖。

Git 历史清理仅在手动运行 `workflow_dispatch` 并勾选 `compact_image_history=true` 时执行，默认 `false`。维护后 Working Copy 和电脑副本需重新对齐或克隆，不要合并旧历史。

[构建与维护](../README.md#publish-images)
