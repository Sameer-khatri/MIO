import os
import tarfile
import zipfile


def create_zip(source_path: str, zip_path: str = None) -> dict:
    """
    Compresses a file or directory into a standard .zip archive.
    If zip_path is omitted, creates a .zip adjacent to source_path.
    """
    if not source_path or not isinstance(source_path, str):
        return {"success": False, "message": "Source path is required."}

    norm_source = os.path.abspath(os.path.expanduser(source_path.strip()))
    if not os.path.exists(norm_source):
        return {"success": False, "message": f"Source does not exist: '{norm_source}'"}

    if zip_path and zip_path.strip():
        norm_zip = os.path.abspath(os.path.expanduser(zip_path.strip()))
        if not norm_zip.lower().endswith(".zip"):
            norm_zip += ".zip"
    else:
        if os.path.isdir(norm_source):
            norm_zip = norm_source.rstrip("\\/") + ".zip"
        else:
            base, _ = os.path.splitext(norm_source)
            norm_zip = base + ".zip"

    target_dir = os.path.dirname(norm_zip)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    file_count = 0
    try:
        with zipfile.ZipFile(norm_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            if os.path.isdir(norm_source):
                for root, _, files in os.walk(norm_source):
                    for file in files:
                        full_path = os.path.join(root, file)
                        if os.path.abspath(full_path) == norm_zip:
                            continue
                        rel_path = os.path.relpath(full_path, start=norm_source)
                        zf.write(full_path, arcname=rel_path)
                        file_count += 1
            else:
                zf.write(norm_source, arcname=os.path.basename(norm_source))
                file_count = 1

        size_bytes = os.path.getsize(norm_zip)
        return {
            "success": True,
            "zip_path": norm_zip,
            "file_count": file_count,
            "size_bytes": size_bytes,
            "message": f"Successfully created zip archive '{norm_zip}' with {file_count} file(s) ({size_bytes} bytes)."
        }
    except Exception as err:
        return {
            "success": False,
            "zip_path": norm_zip if "norm_zip" in locals() else zip_path,
            "message": f"Failed to create zip: {err}"
        }


def extract_zip(zip_path: str, destination_folder: str = None) -> dict:
    """
    Safely extracts a .zip archive into the specified destination folder.
    Prevents Zip-Slip directory traversal vulnerabilities.
    """
    if not zip_path or not isinstance(zip_path, str):
        return {"success": False, "message": "Zip path is required."}

    norm_zip = os.path.abspath(os.path.expanduser(zip_path.strip()))
    if not os.path.exists(norm_zip) or not os.path.isfile(norm_zip):
        return {"success": False, "message": f"Zip file does not exist: '{norm_zip}'"}

    if destination_folder and destination_folder.strip():
        norm_dest = os.path.abspath(os.path.expanduser(destination_folder.strip()))
    else:
        base, _ = os.path.splitext(norm_zip)
        norm_dest = base

    os.makedirs(norm_dest, exist_ok=True)

    extracted_count = 0
    try:
        with zipfile.ZipFile(norm_zip, "r") as zf:
            dest_prefix = os.path.commonpath([norm_dest])

            for member in zf.infolist():
                target_path = os.path.abspath(os.path.join(norm_dest, member.filename))
                if os.path.commonpath([norm_dest, target_path]) != dest_prefix:
                    raise ValueError(f"Zip contains unsafe path attempting directory traversal: {member.filename}")

                zf.extract(member, norm_dest)
                extracted_count += 1

        return {
            "success": True,
            "destination": norm_dest,
            "extracted_count": extracted_count,
            "message": f"Successfully extracted {extracted_count} item(s) to '{norm_dest}'."
        }
    except Exception as err:
        return {
            "success": False,
            "destination": norm_dest if "norm_dest" in locals() else destination_folder,
            "message": f"Failed to extract zip: {err}"
        }


def list_zip_contents(zip_path: str) -> dict:
    """
    Lists all files and metadata stored inside a .zip archive without extracting.
    """
    if not zip_path or not isinstance(zip_path, str):
        return {"success": False, "message": "Zip path is required."}

    norm_zip = os.path.abspath(os.path.expanduser(zip_path.strip()))
    if not os.path.exists(norm_zip) or not os.path.isfile(norm_zip):
        return {"success": False, "message": f"Zip file does not exist: '{norm_zip}'"}

    try:
        with zipfile.ZipFile(norm_zip, "r") as zf:
            entries = []
            total_uncompressed = 0
            total_compressed = 0
            for info in zf.infolist():
                entries.append({
                    "filename": info.filename,
                    "file_size": info.file_size,
                    "compress_size": info.compress_size,
                    "is_dir": info.is_dir()
                })
                total_uncompressed += info.file_size
                total_compressed += info.compress_size

        return {
            "success": True,
            "zip_path": norm_zip,
            "total_items": len(entries),
            "uncompressed_bytes": total_uncompressed,
            "compressed_bytes": total_compressed,
            "files": entries,
            "message": f"Found {len(entries)} item(s) in '{norm_zip}'."
        }
    except Exception as err:
        return {
            "success": False,
            "zip_path": norm_zip,
            "message": f"Failed to inspect zip: {err}"
        }


def create_tar(source_path: str, tar_path: str = None, gzip_compress: bool = True, gzip: bool = None) -> dict:
    """
    Compresses files or directories into .tar.gz or .tar format using standard library tarfile.
    """
    if gzip is not None:
        gzip_compress = gzip

    if not source_path or not isinstance(source_path, str):
        return {"success": False, "message": "Source path is required."}

    norm_source = os.path.abspath(os.path.expanduser(source_path.strip()))
    if not os.path.exists(norm_source):
        return {"success": False, "message": f"Source does not exist: {norm_source}"}

    ext = ".tar.gz" if gzip_compress else ".tar"
    mode = "w:gz" if gzip_compress else "w"

    if tar_path and tar_path.strip():
        norm_tar = os.path.abspath(os.path.expanduser(tar_path.strip()))
    else:
        norm_tar = norm_source.rstrip("\\/") + ext

    os.makedirs(os.path.dirname(norm_tar), exist_ok=True)

    try:
        with tarfile.open(norm_tar, mode) as tar:
            arcname = os.path.basename(norm_source)
            tar.add(norm_source, arcname=arcname)

        size_bytes = os.path.getsize(norm_tar)
        return {
            "success": True,
            "tar_path": norm_tar,
            "size_bytes": size_bytes,
            "message": f"Created tar archive '{norm_tar}' ({size_bytes} bytes)."
        }
    except Exception as err:
        return {"success": False, "message": f"Failed to create tar: {err}"}


def test_archive(archive_path: str) -> dict:
    """
    Verifies the integrity of a .zip or .tar archive without extracting to disk.
    """
    norm_path = os.path.abspath(os.path.expanduser(archive_path.strip()))
    if not os.path.exists(norm_path):
        return {"success": False, "message": f"Archive not found: {norm_path}"}

    if zipfile.is_zipfile(norm_path):
        try:
            with zipfile.ZipFile(norm_path, "r") as zf:
                bad_file = zf.testzip()
                if bad_file:
                    return {"success": False, "valid": False, "corrupt_file": bad_file, "message": f"Corrupt file in zip: {bad_file}"}
                return {"success": True, "valid": True, "type": "ZIP", "message": f"Zip archive '{os.path.basename(norm_path)}' is healthy (integrity verified)."}
        except Exception as err:
            return {"success": False, "valid": False, "message": f"Zip verification error: {err}"}
    elif tarfile.is_tarfile(norm_path):
        try:
            with tarfile.open(norm_path, "r:*") as tar:
                members = tar.getmembers()
                return {"success": True, "valid": True, "type": "TAR", "items": len(members), "message": f"Tar archive '{os.path.basename(norm_path)}' is healthy ({len(members)} items)."}
        except Exception as err:
            return {"success": False, "valid": False, "message": f"Tar verification error: {err}"}

    return {"success": False, "message": "Unsupported archive format (must be .zip or .tar)."}
