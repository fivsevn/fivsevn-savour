# savour.fivsevn

五月七日的美食分享：[savour.fivsevn.com](https://savour.fivsevn.com/)。代码、照片和内容均由这个仓库独立管理。

## 上传即发布

1. 打开 [trigger_imgs/ 上传入口](https://github.com/fivsevn/fivsevn-savour/upload/main/trigger_imgs)。
2. 选择照片，提交到 `main`。一次可以上传多张。
3. 等待 Actions 完成；仓库会自动命名、建文件夹、发布，并在核验线上内容后清空已处理的入口图片。

支持 JPG/JPEG、PNG、WebP、GIF、HEIC/HEIF，也支持中文文件名和子文件夹。**一张照片就是一则帖子**。上传后自动转换为 WebP，改名为 `YYYYMMDD-HHMMSS-NN.webp`；帖子目录只保存归档 WebP。照片保留尺寸、方向和色彩信息，使用质量 85；PNG/GIF 使用无损转换并保留透明、动画和播放时间。已有 WebP 在归档中保留原字节，不重复压缩。网页对超过 1400px 的静态照片另生成适合显示的缩略图。

发布时间取上传提交的时间，转换为北京时间，之后保持固定。文件名、EXIF 和任务启动时间不决定发布日期。同一次上传重跑不会重复发帖，也不会覆盖已经手工修改的正文；新提交再次上传同名或同一张照片，视为新的发布。

想配文字时，在 GitHub 提交界面的 **可选详细说明（extended description）** 里填写 Markdown；同次上传的每张照片都会收到这段正文。第一行提交摘要不会变成正文。也可以先上传，再单独编辑各帖 `index.md`。不需要 tags。

失败时入口图片保留，打开 [Actions](https://github.com/fivsevn/fivsevn-savour/actions/workflows/build.yml) 查看原因并重新运行；不要为重试再次上传相同图片。若发布期间又有新上传，后续任务会继续读取，旧任务不会覆盖或清走新图片。

## 编辑、隐藏和删除

每帖位于 `savour/YYYY/MM/{id}/`，内有 `index.md` 和自己的 `assets/`：

```yaml
---
id: 2026-10-29-120000-example
date: '2026-10-29T12:00:00+08:00'
title: 29 Oct, 2026 12:00
author: 五月七日
status: published
image: assets/20261029-120000-01.webp
alt: 一碗刚煮好的面
---

这里填写正文，可使用 Markdown 和链接。
```

发布后保持 ID、年月和日期不变，网址就不会变化。正文在详情页的另一条消息里显示，没有正文则不显示空气泡。`status: hidden` 或 `draft` 隐藏帖子；删除整个帖子文件夹即可删除记录。正常 Git 历史仍可用于恢复误删。

本地批量添加也可使用 `scripts/add_post.py`；日常 GitHub 上传无需运行任何脚本。

## 页面和构建

列表手机等高、居中，首页随整页滚动；详情使用可见屏幕空间，只有聊天区域可滚动，顶部箭头返回来源分页。消息字号统一为 9px，间距为 22px。每次打开独立随机时间、电量和三位小数的摄取进度，例如 `704.739%`；停留、滚动或调整窗口不会重抽。随机范围和分页大小位于 `site.json`，真实发布日期不会随机。

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s scripts -p 'test_*.py'
python scripts/build.py
python scripts/check.py
python -m http.server 8000 --directory _site
```

输出 `_site/` 不提交。默认空路径用于正式域名，`--base-path /fivsevn-savour` 支持项目路径预览；Actions 自动读取 Pages 的实际路径。工作流在同一次运行内完成导入、保存帖子与游标、部署、公开字节核验和入口清理。全部图片与字体均由本站提供，构建不访问 WordPress 或旧图片仓库。

`site-data/history.json` 只保存既有排序和同源旧路径的跳转映射，保持历史网址和顺序稳定；`site-data/originals.json` 校验保留的图片和公共资源。帖子中不再保留旧来源 URL 或 WordPress 字段。`unpublished/IMG_7310.webp` 尚无可靠发布日期，保留归档 WebP 但不自动发布。

`.publishing/state.json` 是上传事件游标及已保存图片摘要，不要手工重置。`.publishing/deployed.json` 记录已核验的线上文件，用于确认发布后再清理入口；这些记录不显示在网页上。GitHub Pages 域名和 HTTPS 继续由 Pages 管理，构建不修改 DNS。

图片转换与源文件清理同一次提交完成，失败不会提交半套转换。上传入口的原文件在公开页面与归档 WebP 都核验成功后清走；Git 历史仍可恢复之前上传的原文件。
