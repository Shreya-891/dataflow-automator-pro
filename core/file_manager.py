"""
DataFlow Automator Pro - File Automation Module
Provides smart directory organization, duplicate file detection (hashing),
batch renaming, stale file cleanup, and archive packaging.
"""

import os
import shutil
import hashlib
import re
import zipfile
import tarfile
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from core.logger import logger
from core.exceptions import FileOperationError

CATEGORY_MAPPING = {
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".rtf", ".odt", ".epub", ".md", ".pptx", ".ppt"],
    "Spreadsheets": [".xlsx", ".xls", ".csv", ".tsv", ".ods"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".ico"],
    "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"],
    "Video": [".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm"],
    "Archives": [".zip", ".rar", ".tar", ".gz", ".7z", ".bz2"],
    "Code & Data": [".py", ".js", ".html", ".css", ".json", ".xml", ".sql", ".yaml", ".yml", ".sh", ".bat"],
    "Executables": [".exe", ".msi", ".dmg", ".apk", ".bin"]
}


def get_file_category(ext: str) -> str:
    ext_lower = ext.lower()
    for cat, exts in CATEGORY_MAPPING.items():
        if ext_lower in exts:
            return cat
    return "Others"


def compute_file_hash(filepath: str, algo: str = "sha256", chunk_size: int = 65536) -> str:
    """Compute cryptographic hash of a file efficiently."""
    hasher = hashlib.sha256() if algo == "sha256" else hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Failed to compute hash for {filepath}: {e}")
        raise FileOperationError(f"Could not hash file {filepath}", {"error": str(e)})


def scan_directory(directory: str) -> List[Dict[str, Any]]:
    """Scan directory and return rich metadata for each item."""
    if not os.path.exists(directory):
        raise FileOperationError(f"Directory not found: {directory}")

    items = []
    try:
        for entry in os.scandir(directory):
            stat = entry.stat()
            mod_time = datetime.fromtimestamp(stat.st_mtime)
            is_file = entry.is_file()
            ext = os.path.splitext(entry.name)[1] if is_file else ""
            category = get_file_category(ext) if is_file else "Folder"

            items.append({
                "name": entry.name,
                "path": entry.path,
                "is_file": is_file,
                "size_bytes": stat.st_size if is_file else 0,
                "size_formatted": format_size(stat.st_size) if is_file else "-",
                "modified": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                "extension": ext,
                "category": category
            })
        return items
    except Exception as e:
        logger.error(f"Error scanning directory {directory}: {e}")
        raise FileOperationError(f"Directory scan error: {directory}", {"error": str(e)})


def format_size(bytes_num: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PB"


def get_directory_stats(directory: str) -> Dict[str, Any]:
    """Calculate aggregate statistics of a directory."""
    if not os.path.exists(directory):
        raise FileOperationError(f"Directory not found: {directory}")

    total_files = 0
    total_size = 0
    category_counts: Dict[str, int] = {}
    extension_counts: Dict[str, int] = {}

    for root, _, files in os.walk(directory):
        for f in files:
            filepath = os.path.join(root, f)
            try:
                size = os.path.getsize(filepath)
                ext = os.path.splitext(f)[1].lower() or "no_ext"
                cat = get_file_category(ext)

                total_files += 1
                total_size += size
                category_counts[cat] = category_counts.get(cat, 0) + 1
                extension_counts[ext] = extension_counts.get(ext, 0) + 1
            except (OSError, PermissionError):
                continue

    return {
        "directory": directory,
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_formatted": format_size(total_size),
        "categories": category_counts,
        "top_extensions": dict(sorted(extension_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    }


def organize_directory(
    source_dir: str,
    target_dir: Optional[str] = None,
    rule_type: str = "category",
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Organize files in source_dir into subfolders based on rule_type:
    - 'category': Documents, Images, Spreadsheets, etc.
    - 'extension': .pdf, .docx, .png, etc.
    - 'date': YYYY-MM subfolders based on last modified date.
    - 'size': Small (<1MB), Medium (1-50MB), Large (50-500MB), Huge (>500MB)
    """
    if not os.path.exists(source_dir):
        raise FileOperationError(f"Source directory does not exist: {source_dir}")

    target_dir = target_dir or source_dir
    actions = []
    moved_count = 0
    errors = []

    logger.info(f"Starting organization for '{source_dir}' using rule '{rule_type}' (dry_run={dry_run})")

    for entry in os.scandir(source_dir):
        if not entry.is_file():
            continue

        filename = entry.name
        filepath = entry.path
        ext = os.path.splitext(filename)[1]
        stat = entry.stat()

        dest_subfolder = "Others"
        if rule_type == "category":
            dest_subfolder = get_file_category(ext)
        elif rule_type == "extension":
            dest_subfolder = ext.lstrip(".").upper() if ext else "NO_EXT"
        elif rule_type == "date":
            mod_date = datetime.fromtimestamp(stat.st_mtime)
            dest_subfolder = mod_date.strftime("%Y-%m")
        elif rule_type == "size":
            size_mb = stat.st_size / (1024 * 1024)
            if size_mb < 1:
                dest_subfolder = "Small (<1MB)"
            elif size_mb < 50:
                dest_subfolder = "Medium (1-50MB)"
            elif size_mb < 500:
                dest_subfolder = "Large (50-500MB)"
            else:
                dest_subfolder = "Huge (>500MB)"

        dest_folder_path = os.path.join(target_dir, dest_subfolder)
        dest_file_path = os.path.join(dest_folder_path, filename)

        # Handle duplicate naming in target folder
        if os.path.exists(dest_file_path) and os.path.abspath(filepath) != os.path.abspath(dest_file_path):
            base, ext_part = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_file_path = os.path.join(dest_folder_path, f"{base}_{timestamp}{ext_part}")

        action_record = {
            "file": filename,
            "source": filepath,
            "destination_folder": dest_subfolder,
            "destination_path": dest_file_path,
            "status": "planned" if dry_run else "success"
        }

        if not dry_run:
            try:
                os.makedirs(dest_folder_path, exist_ok=True)
                shutil.move(filepath, dest_file_path)
                moved_count += 1
                action_record["status"] = "moved"
            except Exception as e:
                err_msg = f"Failed moving {filename}: {str(e)}"
                logger.error(err_msg)
                action_record["status"] = "failed"
                action_record["error"] = str(e)
                errors.append(err_msg)
        else:
            moved_count += 1

        actions.append(action_record)

    logger.info(f"Completed organization: {moved_count} files processed with {len(errors)} errors.")
    return {
        "success": len(errors) == 0,
        "moved_count": moved_count,
        "rule_type": rule_type,
        "dry_run": dry_run,
        "actions": actions,
        "errors": errors
    }


def find_duplicates(directory: str, algo: str = "sha256", delete_duplicates: bool = False) -> Dict[str, Any]:
    """
    Scans directory recursively to find duplicate files based on content hash.
    Optionally deletes duplicate copies, retaining one original file per unique hash.
    """
    if not os.path.exists(directory):
        raise FileOperationError(f"Directory not found: {directory}")

    logger.info(f"Scanning for duplicates in '{directory}' using {algo.upper()}")
    size_map: Dict[int, List[str]] = {}

    # Quick pre-filter by size
    for root, _, files in os.walk(directory):
        for f in files:
            path = os.path.join(root, f)
            try:
                size = os.path.getsize(path)
                if size > 0:  # ignore empty files or group separately
                    size_map.setdefault(size, []).append(path)
            except (OSError, PermissionError):
                continue

    # Hash files that have identical sizes
    hash_map: Dict[str, List[str]] = {}
    for size, paths in size_map.items():
        if len(paths) > 1:
            for p in paths:
                try:
                    file_hash = compute_file_hash(p, algo=algo)
                    hash_map.setdefault(file_hash, []).append(p)
                except Exception:
                    continue

    duplicate_groups = []
    total_wasted_bytes = 0
    deleted_files = []

    for file_hash, paths in hash_map.items():
        if len(paths) > 1:
            size = os.path.getsize(paths[0])
            wasted = size * (len(paths) - 1)
            total_wasted_bytes += wasted

            group_info = {
                "hash": file_hash,
                "original": paths[0],
                "duplicates": paths[1:],
                "file_size": format_size(size),
                "wasted_space": format_size(wasted)
            }
            duplicate_groups.append(group_info)

            if delete_duplicates:
                for dup_path in paths[1:]:
                    try:
                        os.remove(dup_path)
                        deleted_files.append(dup_path)
                        logger.info(f"Removed duplicate file: {dup_path}")
                    except Exception as e:
                        logger.error(f"Error removing duplicate {dup_path}: {e}")

    return {
        "directory": directory,
        "duplicate_groups_count": len(duplicate_groups),
        "total_duplicates_found": sum(len(g["duplicates"]) for g in duplicate_groups),
        "total_wasted_space": format_size(total_wasted_bytes),
        "groups": duplicate_groups,
        "deleted_count": len(deleted_files),
        "deleted_files": deleted_files
    }


def batch_rename(
    directory: str,
    pattern: str = "",
    replacement: str = "",
    prefix: str = "",
    suffix: str = "",
    numbering: bool = False,
    start_index: int = 1,
    case_style: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Batch rename files in a directory using pattern replacement, prefixes/suffixes,
    sequential numbering, and casing styles ('lower', 'upper', 'title', 'slug').
    """
    if not os.path.exists(directory):
        raise FileOperationError(f"Directory not found: {directory}")

    renamed_items = []
    errors = []
    counter = start_index

    entries = sorted([e for e in os.scandir(directory) if e.is_file()], key=lambda e: e.name)

    for entry in entries:
        old_name = entry.name
        base_name, ext = os.path.splitext(old_name)
        new_base = base_name

        # 1. Pattern / Regex Replacement
        if pattern:
            try:
                new_base = re.sub(pattern, replacement, new_base)
            except re.error as e:
                raise FileOperationError(f"Invalid regex pattern: {pattern}", {"error": str(e)})

        # 2. Case Style
        if case_style == "lower":
            new_base = new_base.lower()
        elif case_style == "upper":
            new_base = new_base.upper()
        elif case_style == "title":
            new_base = new_base.title()
        elif case_style == "slug":
            new_base = re.sub(r'[\s_]+', '-', new_base.strip()).lower()
            new_base = re.sub(r'[^a-zA-Z0-9-]', '', new_base)

        # 3. Prefix and Suffix
        if prefix:
            new_base = f"{prefix}{new_base}"
        if suffix:
            new_base = f"{new_base}{suffix}"

        # 4. Numbering
        if numbering:
            new_base = f"{new_base}_{counter:03d}"
            counter += 1

        new_name = f"{new_base}{ext}"
        old_path = entry.path
        new_path = os.path.join(directory, new_name)

        item_record = {
            "old_name": old_name,
            "new_name": new_name,
            "old_path": old_path,
            "new_path": new_path,
            "status": "planned" if dry_run else "success"
        }

        if old_name != new_name and not dry_run:
            try:
                os.rename(old_path, new_path)
                item_record["status"] = "renamed"
            except Exception as e:
                item_record["status"] = "failed"
                item_record["error"] = str(e)
                errors.append(f"Failed renaming {old_name} -> {new_name}: {e}")

        renamed_items.append(item_record)

    return {
        "success": len(errors) == 0,
        "total_files": len(entries),
        "renamed_count": len([i for i in renamed_items if i["status"] in ("renamed", "planned") and i["old_name"] != i["new_name"]]),
        "dry_run": dry_run,
        "items": renamed_items,
        "errors": errors
    }


def clean_stale_files(
    directory: str,
    days_old: int = 30,
    extensions: Optional[List[str]] = None,
    action: str = "archive",
    archive_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Identify and either delete or archive files older than days_old.
    """
    if not os.path.exists(directory):
        raise FileOperationError(f"Directory not found: {directory}")

    cutoff_date = datetime.now() - timedelta(days=days_old)
    matched_files = []
    processed_count = 0

    if action == "archive":
        archive_dir = archive_dir or os.path.join(directory, "Archive_Stale")
        os.makedirs(archive_dir, exist_ok=True)

    for entry in os.scandir(directory):
        if not entry.is_file():
            continue

        ext = os.path.splitext(entry.name)[1].lower()
        if extensions and ext not in [e.lower() for e in extensions]:
            continue

        mod_time = datetime.fromtimestamp(entry.stat().st_mtime)
        if mod_time < cutoff_date:
            file_record = {
                "name": entry.name,
                "path": entry.path,
                "modified": mod_time.strftime("%Y-%m-%d"),
                "size": format_size(entry.stat().st_size)
            }

            if action == "delete":
                try:
                    os.remove(entry.path)
                    file_record["status"] = "deleted"
                    processed_count += 1
                except Exception as e:
                    file_record["status"] = f"failed: {e}"
            elif action == "archive":
                try:
                    dest = os.path.join(archive_dir, entry.name)
                    shutil.move(entry.path, dest)
                    file_record["status"] = "archived"
                    file_record["archive_path"] = dest
                    processed_count += 1
                except Exception as e:
                    file_record["status"] = f"failed: {e}"

            matched_files.append(file_record)

    return {
        "directory": directory,
        "days_threshold": days_old,
        "action": action,
        "processed_count": processed_count,
        "files": matched_files
    }


def create_archive(source_paths: List[str], output_zip_path: str, format_type: str = "zip") -> str:
    """Create a compressed ZIP or TAR archive containing specified files or directories."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_zip_path)), exist_ok=True)
        if format_type == "zip":
            with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for path in source_paths:
                    if os.path.isfile(path):
                        zf.write(path, os.path.basename(path))
                    elif os.path.isdir(path):
                        for root, _, files in os.walk(path):
                            for f in files:
                                full_p = os.path.join(root, f)
                                arcname = os.path.relpath(full_p, os.path.dirname(path))
                                zf.write(full_p, arcname)
        elif format_type in ("tar", "tar.gz"):
            mode = "w:gz" if format_type == "tar.gz" else "w"
            with tarfile.open(output_zip_path, mode) as tf:
                for path in source_paths:
                    arcname = os.path.basename(path)
                    tf.add(path, arcname=arcname)

        logger.info(f"Successfully created {format_type.upper()} archive at {output_zip_path}")
        return output_zip_path
    except Exception as e:
        logger.error(f"Archive creation failed: {e}")
        raise FileOperationError(f"Failed to create archive {output_zip_path}", {"error": str(e)})
