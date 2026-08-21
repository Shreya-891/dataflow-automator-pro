"""
Unit tests for File Manager Automation Module.
"""

import os
import shutil
import tempfile
import unittest
from core.file_manager import (
    organize_directory, find_duplicates, batch_rename, clean_stale_files, create_archive, scan_directory
)


class TestFileManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

        # Create dummy sample files
        self.doc_file = os.path.join(self.test_dir, "notes.txt")
        with open(self.doc_file, "w") as f:
            f.write("Meeting notes sample text.")

        self.pdf_file = os.path.join(self.test_dir, "report.pdf")
        with open(self.pdf_file, "w") as f:
            f.write("Sample PDF content placeholder.")

        # Create duplicate file
        self.dup_file = os.path.join(self.test_dir, "notes_copy.txt")
        with open(self.dup_file, "w") as f:
            f.write("Meeting notes sample text.")

        self.img_file = os.path.join(self.test_dir, "photo.png")
        with open(self.img_file, "w") as f:
            f.write("Fake image data bytes.")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_scan_directory(self):
        items = scan_directory(self.test_dir)
        self.assertEqual(len(items), 4)

    def test_find_duplicates(self):
        dups = find_duplicates(self.test_dir, algo="sha256", delete_duplicates=False)
        self.assertEqual(dups["duplicate_groups_count"], 1)
        self.assertEqual(dups["total_duplicates_found"], 1)

    def test_batch_rename(self):
        res = batch_rename(self.test_dir, prefix="test_", numbering=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["renamed_count"], 4)

        # Check new files exist with test_ prefix
        renamed_files = os.listdir(self.test_dir)
        for f in renamed_files:
            self.assertTrue(f.startswith("test_"))

    def test_organize_directory(self):
        res = organize_directory(self.test_dir, rule_type="category", dry_run=False)
        self.assertTrue(res["success"])
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Documents")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Images")))

    def test_create_archive(self):
        zip_out = os.path.join(self.test_dir, "test_archive.zip")
        create_archive([self.doc_file, self.pdf_file], zip_out, format_type="zip")
        self.assertTrue(os.path.exists(zip_out))
        self.assertGreater(os.path.getsize(zip_out), 0)


if __name__ == "__main__":
    unittest.main()
