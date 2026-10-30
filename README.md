---
id: savour-readme
title: Savour publishing and maintenance

module: savour
submodule: root
topic: guide

type: note
status: active
canonical: true

summary: Publishing, validation, and maintenance for savour.

parents: []
related: []

tags:
- savour

audience:
- self
- internal
languages:
- en

maturity: evolving
confidence: null

visibility: public
source_of_truth: site

filename_policy: entrypoint

created: null
updated: '2026-10-30'
metadata_updated: '2026-10-30'
---
# savour.fivsevn

Savour is the food-and-drink section of [fivsevn.com](https://fivsevn.com/): meals, drinks, and food photos. Its public page is [savour.fivsevn.com](https://savour.fivsevn.com/). This repository holds its content archive and static-site backend.

Upload photos to [`trigger_imgs/`](trigger_imgs/). The repository converts them to WebP, saves one editable post per image, builds the phone-chat interface, and publishes through GitHub Pages. The [image inbox guide](trigger_imgs/README.md) provides concise everyday instructions in Chinese; this README covers publishing and maintenance in English.

## Repository layout

```text
trigger_imgs/                      Temporary image-upload inbox
  README.md                        Chinese daily upload guide
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
  site_post_metadata.py            Shared metadata normalization and schema validation
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
schemas/                           Local copies of the shared core and site-post schemas
site.json                          Site title, pagination, and decorative-number ranges
requirements.txt                   Pinned Python dependencies
_site/                             Generated deployment artifact; ignored by Git
```

Edit saved packages under `savour/`. Generated HTML and display thumbnails belong to `_site/` and are rebuilt from source. The site serves its own images and fonts.

## Publish images

### Upload through GitHub

1. Open the [image upload page](https://github.com/fivsevn/fivsevn-savour/upload/main/trigger_imgs).
2. Select one or more photos and keep their original filenames. The repository handles naming, conversion, and post folders.
3. Use the commit summary for an operation label. Put an optional Markdown caption in **extended description**, below the summary line. Leave it empty for image-only posts.
4. Commit directly to `main`.
5. Wait for [Build and deploy Savour](https://github.com/fivsevn/fivsevn-savour/actions/workflows/build.yml) to succeed, then check the [website](https://savour.fivsevn.com/), the individual post, and its large image.

Each image becomes a separate post. Images uploaded in the same commit share the caption from its extended description. Publishing uses a photo and optional caption.

### Use Working Copy or a phone shortcut

Configure the shortcut to use **fivsevn-savour**, save images into `trigger_imgs/`, and commit and push to this repository's `main` branch. If the shortcut collects a caption, write it to the commit's extended description.

Before each upload, pull the latest `main`. The publishing bot creates commits containing new packages, publication state, and inbox cleanup; the next pull brings those changes back to the phone. Then save, commit, and push the new photos.

### Dates, names, and duplicate handling

- Publication time comes from the upload commit's **committer timestamp**, converted to `Asia/Shanghai` and saved with its UTC offset.
- A package ID combines that timestamp with a digest of the upload commit and path. Its directory is `savour/YYYY/MM/{id}/`.
- Archived media is named `assets/YYYYMMDD-HHMMSS-NN.webp`. Uploaded paths are sorted to assign stable batch numbers.
- Each commit and path is processed once; retries preserve the saved post and any later caption edits.
- Uploading the same filename or identical image bytes in a **new commit** creates a new post. Revise an existing post through its saved package.
- A saved package keeps its ID, publication date, and permalink through image conversion.

## Image conversion and storage

Supported inputs are JPG/JPEG, PNG, WebP, GIF, HEIC, and HEIF, with case-insensitive extensions. Unicode filenames and nested inbox folders are supported.

| Input | Archived WebP behavior |
| --- | --- |
| JPEG and HEIC/HEIF photos | Quality 85, original display dimensions, corrected orientation, retained ICC color profile and applicable EXIF metadata |
| PNG graphics | Lossless WebP with transparency; animated PNG frames and timing are retained |
| GIF animations | Lossless animated WebP retaining frames, timing, transparency, and loop behavior |
| Existing WebP | Validated and retained byte-for-byte |

MPO and HEIF uploads use the primary display photo; auxiliary images such as phone HDR gain maps stay outside the animation frames. Each saved package keeps its archived WebP. Uploaded originals remain recoverable from Git history.

For static images larger than 1400 pixels on their longest edge, the website build creates a smaller `display.webp` thumbnail in `_site/`. The individual post links to the full-resolution archived WebP. Smaller WebP images and animations are served directly. Display thumbnails live in the generated deployment artifact.

`normalize_images.py` also handles saved packages added manually, including hidden and draft posts. It validates the whole batch, stages converted files, updates image references and retained-asset checksums, and replaces old-format files as one transaction. Existing WebP files and the conversion receipt stay unchanged when the archive is already normalized.

## Captions and saved posts

A package contains one `index.md` and its own `assets/` directory:

```yaml
---
id: 2026-10-29-120000-example
title: 29 Oct, 2026 12:00
module: savour
submodule: '2026'
topic: null
type: log
status: published
canonical: true
summary: null
parents: []
related: []
tags: []
audience: [public]
languages: [zh]
maturity: evolving
confidence: null
visibility: public
source_of_truth: site
filename_policy: entrypoint
created: '2026-10-29'
updated: '2026-10-29'
metadata_updated: '2026-10-30'
extra:
  profile: site-post-v1
  published_at: '2026-10-29T12:00:00+08:00'
  author: 五月七日
  image: assets/20261029-120000-01.webp
  alt: A bowl of freshly cooked noodles
---

Write the caption here. **Markdown** and [named links](https://example.com/) are supported.
```

Saved posts use the same [content metadata contract](https://github.com/fivsevn-agy/fivsevn-spec/blob/main/content/content-metadata.schema.json) and [site-post profile](https://github.com/fivsevn-agy/fivsevn-spec/blob/main/content/site-post.schema.json) as Flux and Fieldlog. The shared normalizer and schemas are committed locally under `scripts/` and `schemas/`, so normal builds need no network connection. Update those copies together when adopting a new contract version.

Uploads need only a photo and optional caption. The importer fills the shared fields automatically, and the workflow completes missing fields in manually saved packages before validation. Explicit statuses and visibility settings are preserved. Unrecognized older metadata is retained under `legacy.metadata` rather than discarded.

| Field | Meaning |
| --- | --- |
| `id` | Stable identity; must match the package directory name |
| `title` | Displayed date label or heading |
| `module`, `submodule`, `type` | `savour`, publication year as a string, and `log` |
| `status`, `visibility` | A post is listed only when visibility is `public` and status is `active`, `publish`, or `published` |
| `created`, `updated` | Content dates; kept separate from publication time |
| `metadata_updated` | Date of a metadata change; an unchanged normalization does not refresh it |
| `extra.profile` | `site-post-v1` |
| `extra.published_at` | Fixed publication timestamp with a timezone offset; its year and month must match the package directories |
| `extra.author` | Author name; generated uploads use 五月七日 |
| `extra.image` | Package-relative photo path inside `assets/` |
| `extra.alt` | Alternative text for the photo |

The photo is stored in `extra.image`; put caption text after the closing `---`. On the individual page, the photo appears as one chat message and a caption as another. Image-only posts show the photo message. Additional Markdown images in the body fail validation.

To revise a caption, edit the saved `index.md`, commit, and push. Keep the ID and `extra.published_at` unchanged to preserve the permalink and chronological position. Set `status` to `hidden` or `draft`, or set `visibility` to `private` or `internal`, to exclude a post from the generated website. This metadata does not make files in the public repository private. Delete a post's entire package directory to remove it; earlier versions remain in Git history.

Each feed page contains up to **11 published posts**. The opening lock screen, closing chat, and final lock screen are decorative sections and do not count toward that limit. A partial final page contains the remaining posts.

## Publishing and inbox cleanup

The workflow runs on relevant pushes to `main` and supports manual runs. It serializes publication and checks out the latest branch with complete Git history.

1. Install pinned dependencies, normalize shared post metadata, and run the test suite.
2. Normalize saved photos, import unprocessed inbox changes from their immutable Git commit snapshots, and validate the shared core and site-post schemas.
3. Read the actual Pages base path, build into `_site/`, and validate source integrity and generated references.
4. Commit saved packages, updated checksums, conversion records, and the upload cursor together, then push to `main`.
5. Upload the artifact and deploy it through GitHub Pages.
6. Compare the public build receipt and required page/media bytes with the local artifact.
7. Confirm the remote branch still matches this run, clear matching verified inbox originals, and record the verified deployment.

One workflow run completes import, deployment, public verification, and inbox cleanup.

The inbox is temporary. An original is removed after its archived package has been saved and publicly verified. Cleanup checks the uploaded source digest and the saved WebP digest separately. Failed runs, newer uploads, and changed saved images retain their inbox files.

The source commit cursor and per-event records prevent retries from recreating posts. They also preserve manual caption edits. The newest event owns a reused inbox path, including when the new bytes happen to match an earlier upload.

## Recover from a failed run

Open the failed step in [Actions](https://github.com/fivsevn/fivsevn-savour/actions/workflows/build.yml), resolve its cause, and rerun the latest relevant workflow. Rerunning uses the saved upload event; uploading again creates a new post.

| Failure | What to do |
| --- | --- |
| Invalid or unsupported input | Replace or remove the bad inbox file and push. A superseded invalid historical upload can then be skipped; a current invalid upload still blocks its batch. |
| A newer commit arrived or a push was rejected | Let the latest queued run continue, or rerun against the latest `main`. Pull bot commits before the next phone upload. |
| Public deployment or media verification failed | Check Pages and rerun the latest workflow. Matching inbox originals remain until verification succeeds. |
| A retained image checksum changed | Restore an accidental change. For a deliberate replacement of an image tracked by `site-data/originals.json`, review and update that entry's path, byte count, and SHA-256. |
| The upload cursor is missing or outside main's first-parent history | Review or restore Git history before repairing publication state. Resetting the cursor can replay processed uploads. |

## Local development and maintenance

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/site_post_metadata.py normalize --site savour --root savour --schema-dir schemas
python -m unittest discover -s scripts -p 'test_*.py'
python scripts/normalize_images.py
python scripts/site_post_metadata.py check --site savour --root savour --schema-dir schemas
python scripts/build.py
python scripts/check.py
python -m http.server 8000 --directory _site
```

The default build uses the domain root. Use `--base-path /fivsevn-savour` for a GitHub project-path preview and pass the same value to `scripts/check.py`. Production Actions reads the configured Pages path automatically. Build output is generated under the Git-ignored `_site/` directory.

For optional local package creation:

```sh
python scripts/add_post.py meal.jpg dessert.heic \
  --date '2026-10-29T12:00:00+08:00' --text-file caption.md
```

The helper converts each input to WebP and creates a separate package. GitHub and phone uploads use the automatic workflow above.

### Settings and state

- `site.json` controls the site title, the 11-post feed page size, and random battery/progress ranges.
- `scripts/site_post_metadata.py` and `schemas/` keep the shared metadata contract local. `normalize` fills missing metadata without changing captions; `check` validates without rewriting files.
- `site-data/history.json` retains the established order for equal-time historic posts and same-origin path aliases.
- `site-data/originals.json` verifies archived WebP photos, the avatar, and fonts.
- `unpublished/IMG_7310.webp` retains a photo pending a reliable publication date.
- `.publishing/state.json` records the Git cursor, event identities, source digests, saved WebP digests, and package paths. Preserve it during routine maintenance.
- `.publishing/webp-conversion.json` records the last saved-image conversion batch and stays unchanged between conversions.
- `.publishing/deployed.json` records the last verified public file hashes. `_site/build-receipt.json` describes the current artifact, and `_site/.verified.json` is a local verification marker used before cleanup.

### Phone interface

Feed phones have uniform frames and the page scrolls as a whole. The individual page keeps one frame within the visible viewport and scrolls its chat area when needed; its header arrow returns to the source feed and post position.

Decorative time, battery, and eating progress are randomized independently for each phone once per document load. Progress has three decimal places, such as `704.739%`. These values stay fixed while the page is open, including during scrolling and resizing. Publication dates and URLs come from saved post metadata.

GitHub Pages manages the custom domain and HTTPS. Site settings and DNS are managed separately from the build. Savour uses the shared publishing conventions of the fivsevn site family and its own phone-chat interface.
