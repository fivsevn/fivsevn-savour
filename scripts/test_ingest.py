"""Exercise the publishing queue against real, isolated Git repositories."""
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml
from PIL import Image

from ingest_github import ingest, read_state, register_heif_opener


def image_bytes(color="red", format="PNG"):
    data = BytesIO()
    Image.new("RGB", (4, 3), color).save(data, format=format)
    return data.getvalue()


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.command("init", "--quiet", "-b", "main")
        self.command("config", "user.name", "Publisher test")
        self.command("config", "user.email", "publisher@example.invalid")
        self.write("README.md", b"test repository\n")
        baseline = self.commit("Initial repository", "2026-10-28T00:00:00+00:00")
        self.state_path = self.root / ".publishing/state.json"
        self.state_path.parent.mkdir()
        self.state_path.write_text(json.dumps({"version": 1, "cursor": baseline, "events": {}}))
        self.baseline = baseline

    def tearDown(self):
        self.temporary.cleanup()

    def command(self, *arguments, environment=None):
        result = subprocess.run(["git", "-C", str(self.root), *arguments], check=True,
                                capture_output=True, env=environment)
        return result.stdout.decode("utf-8").strip()

    def write(self, path, data):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return destination

    def commit(self, message, date="2026-10-29T04:30:12+00:00"):
        self.command("add", "--all")
        environment = {**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
        self.command("commit", "--quiet", "-m", message, environment=environment)
        return self.command("rev-parse", "HEAD")

    def packages(self):
        result = []
        for path in sorted((self.root / "savour").glob("*/*/*/index.md")):
            _, head, body = path.read_text().split("---", 2)
            result.append((path, yaml.safe_load(head), body.strip()))
        return result

    def test_batch_names_date_caption_and_original_bytes(self):
        payloads = {"trigger_imgs/说明/IMG_0001.PNG": image_bytes("red"),
                    "trigger_imgs/相片/IMG_0001.PNG": image_bytes("blue")}
        for path, data in payloads.items():
            self.write(path, data)
        sha = self.commit("Upload photos\n\n配文 [主页](https://example.com/)\n第二段")
        self.assertEqual(ingest(self.root), 2)
        state = read_state(self.root)
        self.assertEqual(state["cursor"], sha)
        paths = sorted(payloads)
        self.assertEqual(list(state["events"]), [sha + ":" + path for path in paths])
        for number, upload in enumerate(paths, start=1):
            event = state["events"][sha + ":" + upload]
            original = self.root / event["image_path"]
            self.assertEqual(original.name, f"20261029-123012-{number:02d}.png")
            self.assertEqual(original.read_bytes(), payloads[upload])
            self.assertEqual(event["sha256"], hashlib.sha256(payloads[upload]).hexdigest())
            self.assertEqual(event["blob_sha"], self.command("rev-parse", sha + ":" + upload))
            _, meta, body = next(package for package in self.packages() if package[1]["id"] == event["id"])
            self.assertEqual(set(meta), {"id", "date", "title", "author", "status", "image", "alt"})
            self.assertEqual(meta["date"], "2026-10-29T12:30:12+08:00")
            self.assertEqual(meta["title"], "29 Oct, 2026 12:30")
            self.assertEqual(meta["image"], "assets/" + original.name)
            self.assertEqual(body, "配文 [主页](https://example.com/)\n第二段")
            self.assertNotIn("![]", body)
            self.assertTrue((self.root / upload).exists(), "Ingestion must retain the inbox original")

    def test_each_immutable_commit_imports_its_own_bytes_oldest_first(self):
        upload = "trigger_imgs/photo.png"
        first = image_bytes("red")
        second = image_bytes("blue")
        self.write(upload, first)
        one = self.commit("First upload", "2026-10-29T00:00:00+00:00")
        self.write(upload, second)
        two = self.commit("Second upload", "2026-10-29T00:00:01+00:00")
        self.assertEqual(ingest(self.root), 2)
        events = read_state(self.root)["events"]
        self.assertEqual(list(events), [one + ":" + upload, two + ":" + upload])
        self.assertEqual((self.root / events[one + ":" + upload]["image_path"]).read_bytes(), first)
        self.assertEqual((self.root / events[two + ":" + upload]["image_path"]).read_bytes(), second)

    def test_retry_and_rewound_cursor_never_overwrite_manual_edits(self):
        self.write("trigger_imgs/a.jpg", image_bytes(format="JPEG"))
        self.commit("Upload")
        self.assertEqual(ingest(self.root), 1)
        path, _, _ = self.packages()[0]
        edited = path.read_text() + "\n后来单独编辑的正文\n"
        path.write_text(edited)
        self.assertEqual(ingest(self.root), 0)
        self.assertEqual(path.read_text(), edited)
        # A retry can encounter an older cursor with already-saved event keys.
        state = read_state(self.root)
        state["cursor"] = self.baseline
        self.state_path.write_text(json.dumps(state))
        self.assertEqual(ingest(self.root), 0)
        self.assertEqual(path.read_text(), edited)

    def test_new_upload_after_cleanup_can_reuse_identical_name_and_bytes(self):
        upload = "trigger_imgs/IMG_0001.PNG"
        payload = image_bytes()
        self.write(upload, payload)
        one = self.commit("Upload first")
        self.assertEqual(ingest(self.root), 1)
        (self.root / upload).unlink()
        self.commit("Record saved package and clear verified inbox")
        self.write(upload, payload)
        two = self.commit("Upload again in a new commit")
        self.assertEqual(ingest(self.root), 1)
        events = read_state(self.root)["events"]
        self.assertEqual(len(events), 2)
        self.assertNotEqual(events[one + ":" + upload]["id"], events[two + ":" + upload]["id"])
        self.assertEqual(len(self.packages()), 2)

    def test_deletions_and_guides_are_not_new_posts_but_cursor_advances(self):
        self.write("trigger_imgs/README.md", b"Upload images here")
        self.write("trigger_imgs/.gitkeep", b"")
        self.write("trigger_imgs/.keep", b"")
        one = self.commit("Add inbox guide")
        self.assertEqual(ingest(self.root), 0)
        self.assertEqual(read_state(self.root)["cursor"], one)
        (self.root / "trigger_imgs/.keep").unlink()
        two = self.commit("Remove inbox placeholder")
        self.assertEqual(ingest(self.root), 0)
        self.assertEqual(read_state(self.root)["cursor"], two)
        self.assertFalse(self.packages())

    def test_deleted_later_upload_is_still_read_from_its_original_commit(self):
        payload = image_bytes()
        upload = self.write("trigger_imgs/a.png", payload)
        self.commit("Upload")
        upload.unlink()
        latest = self.commit("Remove inbox original")
        self.assertEqual(ingest(self.root), 1)
        event = next(iter(read_state(self.root)["events"].values()))
        self.assertEqual((self.root / event["image_path"]).read_bytes(), payload)
        self.assertEqual(read_state(self.root)["cursor"], latest)

    def test_bad_batch_leaves_all_content_state_and_inbox_intact(self):
        self.write("trigger_imgs/a.png", image_bytes())
        self.write("trigger_imgs/z.png", b"damaged")
        self.commit("Upload valid and damaged photos together")
        before = self.state_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "damaged"):
            ingest(self.root)
        self.assertEqual(self.state_path.read_bytes(), before)
        self.assertFalse((self.root / "savour").exists())
        self.assertTrue((self.root / "trigger_imgs/a.png").exists())
        self.assertTrue((self.root / "trigger_imgs/z.png").exists())
        self.assertFalse(list(self.root.glob(".savour-ingest-*")))

    def test_unsupported_upload_fails_without_creating_packages(self):
        self.write("trigger_imgs/movie.mov", b"video")
        self.commit("Upload unsupported file")
        before = self.state_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Unsupported upload"):
            ingest(self.root)
        self.assertEqual(self.state_path.read_bytes(), before)
        self.assertFalse(self.packages())

    def test_later_repair_unblocks_a_previously_damaged_batch(self):
        self.write("trigger_imgs/a.png", image_bytes("red"))
        self.write("trigger_imgs/z.png", b"damaged")
        broken = self.commit("Upload batch with one damaged photo")
        with self.assertRaisesRegex(ValueError, "damaged"):
            ingest(self.root)
        self.write("trigger_imgs/z.png", image_bytes("blue"))
        repaired = self.commit("Replace damaged upload with a valid photo")
        self.assertEqual(ingest(self.root), 2)
        events = read_state(self.root)["events"]
        self.assertEqual(set(events), {broken + ":trigger_imgs/a.png", repaired + ":trigger_imgs/z.png"})
        self.assertEqual(read_state(self.root)["cursor"], repaired)

    def test_later_deletion_unblocks_a_previously_unsupported_batch(self):
        self.write("trigger_imgs/a.png", image_bytes())
        self.write("trigger_imgs/video.mov", b"unsupported")
        broken = self.commit("Upload photo and an unsupported video")
        with self.assertRaisesRegex(ValueError, "Unsupported upload"):
            ingest(self.root)
        (self.root / "trigger_imgs/video.mov").unlink()
        repaired = self.commit("Remove unsupported video from inbox")
        self.assertEqual(ingest(self.root), 1)
        self.assertEqual(set(read_state(self.root)["events"]), {broken + ":trigger_imgs/a.png"})
        self.assertEqual(read_state(self.root)["cursor"], repaired)

    def test_empty_upload_fails_without_advancing_cursor(self):
        self.write("trigger_imgs/empty.jpg", b"")
        self.commit("Upload empty file")
        before = self.state_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Empty image"):
            ingest(self.root)
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_symlink_upload_and_symlink_destination_are_rejected(self):
        outside = self.write("outside.png", image_bytes())
        (self.root / "trigger_imgs").mkdir()
        (self.root / "trigger_imgs/link.png").symlink_to(outside)
        self.commit("Upload symlink")
        with self.assertRaisesRegex(ValueError, "regular image"):
            ingest(self.root)
        (self.root / "trigger_imgs/link.png").unlink()
        self.write("trigger_imgs/a.png", image_bytes())
        self.commit("Use real image")
        state = read_state(self.root)
        state["cursor"] = self.command("rev-parse", "HEAD^1")
        self.state_path.write_text(json.dumps(state))
        (self.root / "savour").symlink_to(self.root / "somewhere-else")
        with self.assertRaisesRegex(ValueError, "symlink"):
            ingest(self.root)

    def test_type_changes_cannot_hide_symlinks_and_a_later_regular_file_repairs_them(self):
        upload = self.write("trigger_imgs/a.png", image_bytes())
        self.commit("Upload regular image")
        self.assertEqual(ingest(self.root), 1)
        outside = self.write("outside.png", image_bytes("blue"))
        upload.unlink()
        upload.symlink_to(outside)
        self.commit("Replace image with symlink")
        with self.assertRaisesRegex(ValueError, "regular image"):
            ingest(self.root)
        upload.unlink()
        upload.write_bytes(image_bytes("green"))
        self.commit("Restore a regular image file")
        self.assertEqual(ingest(self.root), 1)
        self.assertEqual(len(self.packages()), 2)

    def test_missing_and_nonancestor_cursors_fail_instead_of_replaying(self):
        self.write("trigger_imgs/a.png", image_bytes())
        self.commit("Upload")
        state = read_state(self.root)
        state["cursor"] = "0" * 40
        self.state_path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, "missing"):
            ingest(self.root)
        self.command("checkout", "--", ".publishing/state.json")
        self.command("checkout", "--quiet", "-b", "unrelated", self.baseline)
        self.write("other.txt", b"another branch")
        unrelated = self.commit("Other branch")
        self.command("checkout", "--quiet", "main")
        state["cursor"] = unrelated
        self.state_path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, "first-parent"):
            ingest(self.root)
        self.assertFalse(self.packages())

    def test_animated_original_is_preserved_without_reencoding(self):
        data = BytesIO()
        Image.new("RGB", (3, 2), "red").save(data, format="GIF", save_all=True,
                                                append_images=[Image.new("RGB", (3, 2), "blue")], duration=[100, 200], loop=0)
        original = data.getvalue()
        self.write("trigger_imgs/动画.GIF", original)
        self.commit("Upload animation")
        self.assertEqual(ingest(self.root), 1)
        event = next(iter(read_state(self.root)["events"].values()))
        self.assertEqual((self.root / event["image_path"]).read_bytes(), original)
        with Image.open(self.root / event["image_path"]) as saved:
            self.assertEqual(saved.n_frames, 2)

    @unittest.skipUnless(register_heif_opener is not None, "HEIC support requires pillow-heif")
    def test_heic_original_bytes_and_extension_are_retained(self):
        data = BytesIO()
        Image.new("RGB", (4, 4), "green").save(data, format="HEIF")
        original = data.getvalue()
        self.write("trigger_imgs/IMG_0001.HEIC", original)
        self.commit("Upload phone HEIC")
        self.assertEqual(ingest(self.root), 1)
        event = next(iter(read_state(self.root)["events"].values()))
        saved = self.root / event["image_path"]
        self.assertEqual(saved.suffix, ".heic")
        self.assertEqual(saved.read_bytes(), original)

    def test_state_write_failure_rolls_back_installed_packages(self):
        self.write("trigger_imgs/a.png", image_bytes())
        self.commit("Upload")
        before = self.state_path.read_bytes()
        with patch("ingest_github.os.replace", side_effect=OSError("read-only state file")):
            with self.assertRaisesRegex(OSError, "read-only"):
                ingest(self.root)
        self.assertEqual(self.state_path.read_bytes(), before)
        self.assertFalse((self.root / "savour").exists())
        self.assertFalse(list(self.state_path.parent.glob(".state-*")))


if __name__ == "__main__":
    unittest.main()
