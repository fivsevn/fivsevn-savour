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
updated: '2026-11-01'
metadata_updated: '2026-11-01'
---

# 上传图片

1. [选择图片](https://github.com/fivsevn/fivsevn-savour/upload/main/trigger_imgs)，保留原文件名。
2. 配文写在提交的详细说明中，提交到 `main`；每张图片生成一帖。
3. 等待 [Actions](https://github.com/fivsevn/fivsevn-savour/actions/workflows/build.yml) 成功，查看 [Savour](https://savour.fivsevn.com/)。

支持 JPG/JPEG、PNG、WebP、GIF、HEIC/HEIF，自动保存为 WebP。手机上传前先拉取最新 `main`，线上核验成功后入口原图自动清理。

旧帖在 `savour/年/月/编号/index.md` 修改，重新上传会生成新帖。[维护说明](../README.md)
