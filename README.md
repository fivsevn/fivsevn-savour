# savour.fivsevn

The photo archive and static-site backend for [savour.fivsevn.com](https://savour.fivsevn.com/), 五月七日's food-sharing site.

Upload photos to [`trigger_imgs/`](trigger_imgs/). The repository converts them to WebP, saves one editable post per image, builds the phone-chat interface, and publishes through GitHub Pages. The [image inbox guide](trigger_imgs/README.md) provides concise everyday instructions in Chinese; this README covers publishing and maintenance in English.

## Repository layout

```text
trigger_imgs/                      Temporary image-upload inbox
  README.md                        Chinese daily upload guide; not a post
savour/YYYY/MM/{id}/
  index.md                         Metadata and editable Markdown caption
  assets/                          The post's archived WebP photo
unpublished/                       Retained photos without a reliable publication date
site-assets/                       Shared avatar, fonts, CSS, and browser behavior
site-data/
  history.json                     Established order and same-origin path aliases
  originals.json                   Checksums of retained archive and shared assets
.publishing/
  state.json                       Upload cursor and processed image events
  webp-conversion.json              Receipt for the last saved-image conversion batch
  deployed.json                    File hashes from the last verified public deployment
scripts/
  image_codec.py                   Shared validation and WebP conversion
  normalize_images.py              Normalize saved photos and update their references
  ingest_github.py                  Import committed inbox snapshots into post packages
  add_post.py                      Optional local post-creation helper
  build.py                         Generate feed, pagination, post pages, and aliases
  check.py                         Validate images, checksums, and internal references
  verify_live.py                   Verify the public deployment against its build receipt
  image_inbox.py                   Clear matching originals after verified publication
  test_*.py                        Content, conversion, ingestion, and cleanup tests
.github/workflows/build.yml        Build and deploy Savour workflow
site.json                          Site title, pagination, and decorative-number ranges
requirements.txt                   Pinned Python dependencies
_site/                             Generated deployment artifact; ignored by Git
```

Edit saved packages under `savour/`. Generated HTML and display thumbnails belong to `_site/` and are rebuilt from source. All runtime images and fonts are served by this site; building and publishing do not contact WordPress or the retired assets repository.

## Publish images

### Upload through GitHub

1. Open the [image upload page](https://github.com/fivsevn/fivsevn-savour/upload/main/trigger_imgs).
2. Select one or more photos. Keep their original filenames; no timestamp, conversion, or folder creation is needed on your device.
3. Use the commit summary for an operation label. Put an optional Markdown caption in **extended description**, below the summary line. Leave it empty for image-only posts.
4. Commit directly to `main`.
5. Wait for [Build and deploy Savour](https://github.com/fivsevn/fivsevn-savour/actions/workflows/build.yml) to succeed, then check the [website](https://savour.fivsevn.com/), the individual post, and its large image.

Each image becomes a separate post. Images uploaded in the same commit share its caption. The summary line does not become post text. No tags are required.

### Use Working Copy or a phone shortcut

Configure the shortcut to use **fivsevn-savour**, save images into `trigger_imgs/`, and commit and push to this repository's `main` branch. If the shortcut collects a caption, write it to the commit's extended description.

Before each upload, pull the latest `main`. The publishing bot creates commits containing new packages, publication state, and inbox cleanup; the next pull brings those changes back to the phone. Then save, commit, and push the new photos. This repository supplies the publishing automation, not the shortcut itself.

### Dates, names, and duplicate handling

- Publication time comes from the upload commit's **committer timestamp**, converted to `Asia/Shanghai` and saved with its UTC offset. EXIF dates, original filenames, and workflow start times do not determine it.
- A package ID combines that timestamp with a digest of the upload commit and path. Its directory is `savour/YYYY/MM/{id}/`.
- Archived media is named `assets/YYYYMMDD-HHMMSS-NN.webp`. Uploaded paths are sorted to assign stable batch numbers.
- The same commit and path is processed once. Retrying it does not duplicate a post or overwrite a caption edited afterward.
- Uploading the same filename or identical image bytes in a **new commit** creates a new post. To edit an existing post, edit its saved package instead of uploading it again.
- Existing historical IDs, dates, captions, ordering, and post URLs remain stable. Image conversion changes the media filename and reference, not the post identity.

## Image conversion and storage

Supported inputs are JPG/JPEG, PNG, WebP, GIF, HEIC, and HEIF, with case-insensitive extensions. Unicode filenames and nested inbox folders are supported.

| Input | Archived WebP behavior |
| --- | --- |
| JPEG and HEIC/HEIF photos | Quality 85, original display dimensions, corrected orientation, retained ICC color profile and applicable EXIF metadata |
| PNG graphics | Lossless WebP with transparency; animated PNG frames and timing are retained |
| GIF animations | Lossless animated WebP retaining frames, timing, transparency, and loop behavior |
| Existing WebP | Validated and retained byte-for-byte; no archive recompression |

MPO and HEIF auxiliary images, such as phone HDR gain maps, are treated as still-photo data rather than animation frames. Saved packages contain archived WebP media, not an additional JPEG/PNG copy. Previous uploads remain recoverable from Git history.

For static images larger than 1400 pixels on their longest edge, the website build creates a smaller `display.webp` thumbnail in `_site/`. The archived WebP remains untouched, and the individual post links to that larger image. Smaller WebP images and animations are served directly. Generated display thumbnails are not committed to the content archive.

`normalize_images.py` also handles saved packages added manually, including hidden and draft posts. It validates the whole batch, stages converted files, updates image references and retained-asset checksums, and replaces old-format files only as part of the complete transaction. An unchanged WebP archive is left alone. Its conversion receipt is retained on subsequent runs that need no conversion.

## Captions and saved posts

A package contains one `index.md` and its own `assets/` directory:

```yaml
---
id: 2026-10-29-120000-example
date: '2026-10-29T12:00:00+08:00'
title: 29 Oct, 2026 12:00
author: 五月七日
status: published
image: assets/20261029-120000-01.webp
alt: A bowl of freshly cooked noodles
---

Write the caption here. **Markdown** and [named links](https://example.com/) are supported.
```

The frontmatter `image` is the post's single photo. Keep caption text after the closing `---`; do not insert another Markdown image into the body. On the individual page, the photo appears as one chat message and a nonempty caption as another. An empty caption produces no extra bubble.

| Field | Meaning |
| --- | --- |
| `id` | Stable identity; must match the package directory name |
| `date` | Fixed publication timestamp with a timezone offset; its year and month must match the parent directories |
| `title` | Displayed date label or heading, separate from the saved timestamp |
| `author` | Author name; generated uploads use 五月七日 |
| `status` | `published`, `hidden`, or `draft` |
| `image` | Package-relative photo path inside `assets/` |
| `alt` | Alternative text for the photo |

To revise a caption, edit the saved `index.md`, commit, and push. Keep the ID and date unchanged to preserve the permalink and chronological position. Change `status` to `hidden` or `draft` to exclude a post from the website; delete its entire package directory to remove it. These operations do not erase the public repository's Git history.

The source archive has no tag requirement or tag-filter pages. Historic WordPress/source URL fields are not part of current post frontmatter.

## Publishing and inbox cleanup

The workflow runs on relevant pushes to `main` and supports manual runs. It serializes publication and checks out the latest branch with complete Git history.

1. Install pinned dependencies and run the test suite.
2. Normalize saved photos, then import unprocessed inbox changes from their immutable Git commit snapshots.
3. Read the actual Pages base path, build the site, and validate source integrity and generated references.
4. Commit saved packages, updated checksums, conversion records, and the upload cursor together, using an ordinary non-force push.
5. Upload the artifact and deploy it through GitHub Pages.
6. Compare the public build receipt and required page/media bytes with the local artifact.
7. Confirm that no newer remote commit has arrived, clear only matching verified inbox originals, and record the verified deployment.

Import and deployment happen in the same workflow run. Publishing-bot commits do not need to trigger a second build to finish the original upload.

The inbox is temporary. An original is removed only when its archived package has been saved and publicly verified. Cleanup checks the uploaded source digest and the saved WebP digest separately. A failed conversion, build, deployment, or verification retains the inbox file. A newer upload or a changed saved image is not cleared on the strength of an older matching event.

The source commit cursor and per-event records prevent retries from recreating posts. They also preserve manual caption edits. The newest event owns a reused inbox path, including when the new bytes happen to match an earlier upload.

## Recover from a failed run

Start with the failed step in [Actions](https://github.com/fivsevn/fivsevn-savour/actions/workflows/build.yml). Retry the latest relevant workflow after resolving the cause; do not upload the same photo again solely to retry a deployment.

| Failure | What to do |
| --- | --- |
| Invalid or unsupported input | Replace or remove the bad inbox file and push. A superseded invalid historical upload can then be skipped; a current invalid upload still blocks its batch. |
| A newer commit arrived or a push was rejected | Let the latest queued run continue, or rerun against the latest `main`. Pull bot commits before the next phone upload. Do not force-push over them. |
| Public deployment or media verification failed | Check Pages and rerun the latest workflow. Matching inbox originals remain until verification succeeds. |
| A retained image checksum changed | Restore an accidental change. For a deliberate replacement of an image tracked by `site-data/originals.json`, review and update that entry's path, byte count, and SHA-256. |
| The upload cursor is missing or no longer on main's first-parent history | Review or restore Git history before changing publication state. Do not blindly reset the cursor to replay uploads. |

## Local development and maintenance

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s scripts -p 'test_*.py'
python scripts/normalize_images.py
python scripts/build.py
python scripts/check.py
python -m http.server 8000 --directory _site
```

The default build uses the domain root. Use `--base-path /fivsevn-savour` for a GitHub project-path preview and pass the same value to `scripts/check.py`. Production Actions reads the configured Pages path automatically. Build output is generated under `_site/` and should not be committed.

For optional local package creation:

```sh
python scripts/add_post.py meal.jpg dessert.heic \
  --date '2026-10-29T12:00:00+08:00' --text-file caption.md
```

The helper converts each input to WebP and creates a separate package. Normal GitHub/phone uploading does not require running it.

### Settings and state

- `site.json` controls the site title, feed page size, and random battery/progress ranges.
- `site-data/history.json` retains the established order for equal-time historic posts and same-origin path aliases. It does not supply external media.
- `site-data/originals.json` verifies the retained archive photos, avatar, and fonts. Its photo entries now refer to archived WebP files.
- `unpublished/IMG_7310.webp` has no reliable original publication date. It is retained without creating an undated post.
- `.publishing/state.json` records the Git cursor, event identities, source digests, saved WebP digests, and package paths. Do not hand-reset it during routine maintenance.
- `.publishing/webp-conversion.json` records the last saved-image conversion batch; a no-op normalization does not rewrite it.
- `.publishing/deployed.json` records the last verified public file hashes. `_site/build-receipt.json` describes the current artifact, and `_site/.verified.json` is a local verification marker used before cleanup.

### Phone interface

Feed phones have uniform frames and the page scrolls as a whole. The individual page keeps one frame within the visible viewport and scrolls its chat area when needed; its header arrow returns to the source feed and post position.

Decorative time, battery, and eating progress are randomized independently for each phone once per document load. Progress has three decimal places, such as `704.739%`. Staying on the page, scrolling, or resizing does not redraw these values. Real publication dates and URLs never use the decorative random numbers.

GitHub Pages manages the custom domain and HTTPS. The build does not create DNS records or change domain settings. Flux provides a reference for repository publishing conventions; Savour's phone interface and implementation remain independent.
