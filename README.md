---
id: savour-readme
title: Savour

module: savour
submodule: root
topic: guide

type: note
status: active
canonical: true

summary: Savour 发布与维护。

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

# Savour

[savour.fivsevn.com](https://savour.fivsevn.com/)：饮食照片与随记，直接从本仓库发布。

## 发布与修改

1. 上传照片到 [`trigger_imgs/`](trigger_imgs/)，每张生成一帖。配文写在提交的详细说明中。
2. 提交到 `main`，等待 [Actions](https://github.com/fivsevn/fivsevn-savour/actions/workflows/build.yml) 成功后查看网页。手机上传前先拉取最新 `main`。
3. 旧帖直接修改 `savour/年/月/编号/index.md`；图片放在同包的 `assets/`。保留 `id`、目录和 `extra.published_at`。

隐藏设 `status: hidden`，恢复设 `status: published`、`visibility: public`；删除时移除整个发布包。重新上传图片会生成新帖。

## 维护

- `site-assets/`、`site.json`：界面素材与站点设置。
- `site-data/`：原始素材校验、历史排序和旧路径别名。
- `unpublished/`：尚未确定发布日期的照片。
- `.publishing/`：上传处理进度和已验证部署记录。
- `scripts/`、`schemas/`：发布、校验与构建。
- `_site/`：构建结果，不提交。

Actions 自动转换为 WebP、保存发布包、部署并核验线上文件，成功后清理匹配的入口原图。失败查看对应步骤后重跑；不要清空发布进度。

```sh
pip install -r requirements.txt
python -m unittest discover -s scripts -p 'test_*.py'
node scripts/test_navigation.mjs
python scripts/build.py
python scripts/check.py
python -m http.server 8000 --directory _site
```
