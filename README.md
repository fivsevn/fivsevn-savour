# fivsevn Savour

五月七日的美食分享。保留原 `/foodie/` 的手机聊天界面，内容、照片和构建程序由此仓库独立管理。

正式网址：[savour.fivsevn.com](https://savour.fivsevn.com/)。

## 内容与图片

一张照片对应一个帖子：`savour/YYYY/MM/{id}/index.md` 与同目录 `assets/`。`index.md` 的 frontmatter 保存不可变 ID、带时区的日期、图片、作者和状态；分隔线后的 Markdown 是可编辑正文。正文只在单帖的第二条消息气泡显示。没有正文就不显示额外气泡。无需 tags。

```yaml
id: 2026-10-29-120000-example
date: '2026-10-29T12:00:00+08:00'
title: 29 Oct, 2026 12:00
author: 五月七日
status: published
image: assets/photo.jpg
alt: 一碗刚煮好的面
```

目录中的年月必须与 `date` 一致，文件夹名必须与 `id` 一致。发布后保持 ID、年月和日期不变；改正文不会改变 URL。`status: hidden` 或 `draft` 隐藏帖子；删除整个帖子目录即删除记录。每次构建重新生成站点，已隐藏或删除内容不再保留于新部署产物中。公开 Git 历史仍保留过去提交。

添加多张照片时，辅助脚本为每张分别建帖，同批说明复制到各帖：

```sh
python scripts/add_post.py a.jpg b.jpg c.jpg --date '2026-10-29T12:00:00+08:00' --text-file caption.md
```

之后可分别修改各个 `index.md`。图片仅放在各帖 `assets/`，正文不再插入第二张照片。原图保留原始字节；构建生成 WebP 展示图，点击详情照片可访问自托管原图。头像和字体位于 `site-assets/`。

## 本地构建与检查

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s scripts -p 'test_*.py'
python scripts/build.py
python scripts/check.py
python -m http.server 8000 --directory _site
```

输出 `_site/` 不提交。首页、`feed/2/` 等分页和 `page/YYYY/MM/{id}/` 单帖都来自同一份内容。列表按真实日期和 ID 倒序排列，每页 11 帖。默认空路径用于正式独立域名；`--base-path /fivsevn-savour` 可构建 GitHub 项目路径版本。Actions 自动读取 Pages 的实际 base path。切换 Pages 域名后必须重新运行构建，避免旧路径残留。构建不会创建 CNAME 或更改 DNS。

列表和首尾锁屏使用统一尺寸的手机外框，整列居中。桌面为 400 × 720，小屏至少保留 570px 高度以完整展示消息。首页只随整页滚动，照片按比例适应剩余空间。详情外框从顶部约 28px 开始，并限制在可见屏幕内；页面外层不滚动，只有聊天内容可以滚动。短内容保留空白，顶部返回箭头回到来源分页和帖子位置。消息、链接与正文统一使用摄取进度的 9px 字号，消息间距为 22px。

`site.json` 可以调整分页大小、电量和进度范围。手机时间为合法 HH:MM，电量默认 0–100，进度默认在 0–999.9999 范围内随机，显示三位小数且百分号紧贴数字；每台手机独立，在每次文档加载时生成一次。滚动和停留不会重抽。锁屏状态栏电量与 Charged 一致。数字预留宽度，不影响真实发布日期和 URL。

## 迁移来源与核对

- [完整逐帖清单](migration/README.md)、[机器可读清单](migration/inventory.json)、[图片来源与校验值](migration/assets.json)。
- 2026-10-29 盘点 12 页、125 个帖子和 125 张照片；逐个单帖检查未发现额外正文。第 13 页为空。
- 原日期链接文字与 WordPress 发布元数据存在差异，分别保存在 `title` 与 `date`，没有推测修正。`archive_url`、`legacy` 保留原链接、WP ID、原分页与图片归属。
- 原 `foodie/eastwindx1/IMG_7310.jpg` 未出现在发布清单，复制到 `migration/unassigned/`，不生成无日期帖子，也不进入网站构建。
- 所有运行时图片和字体都由此站点提供。旧 WordPress 和 `fivsevn-assets` 仅用于首次只读迁移，未删除、移动或改写任何旧资源。
- 同源历史日期路径会跳转到对应新帖子；`?query-18-page=N` 可进入对应分页。旧 `fivsevn.com` 域名的链接仍由旧站正常提供，不在本次更改。
- 原对话附件未提供像素数据；设计依据是实时旧网页、原 HTML/CSS 和浏览器比对。

首次导入使用校验值固定的 `scripts/restore_assets.py` 复制原始文件，完成后写入 `.migration-assets-complete`。正常构建完全离线，缺图会直接报错，不从旧站补图。此脚本不会写入任何来源仓库。

## 发布

GitHub Pages 使用 **GitHub Actions** 作为 Source。推送 `main` 后执行测试、构建、全部内部引用和图片检查，再部署。用户于 2026-10-29 在 Pages 中配置正式域名 `savour.fivsevn.com`；部署使用该域名根路径。DNS 和 HTTPS 证书由域名服务与 GitHub Pages 管理。

构建产生 `build-receipt.json`，记录实际部署文件的 SHA-256。检查线上页面时应验证首页、最后分页、单帖、展示图和原图，而非仅依赖工作流显示成功。
