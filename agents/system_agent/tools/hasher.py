import hashlib
import os


def hash_file(file_path: str, algorithm: str = "sha256") -> dict:
    """
    Computes cryptographic checksum hash (SHA256, MD5, SHA1) of any local file.
    Streams in 64KB chunks to efficiently handle large files without memory spikes.
    """
    if not file_path or not isinstance(file_path, str):
        return {"success": False, "message": "File path is required."}

    norm_path = os.path.abspath(os.path.expanduser(file_path.strip()))
    if not os.path.exists(norm_path) or not os.path.isfile(norm_path):
        return {"success": False, "message": f"File does not exist: '{norm_path}'"}

    algo_name = algorithm.strip().lower()
    if algo_name in ("md5",):
        hasher = hashlib.md5()
    elif algo_name in ("sha1",):
        hasher = hashlib.sha1()
    elif algo_name in ("sha512",):
        hasher = hashlib.sha512()
    else:
        hasher = hashlib.sha256()
        algo_name = "sha256"

    try:
        size_bytes = os.path.getsize(norm_path)
        with open(norm_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)

        digest = hasher.hexdigest()
        return {
            "success": True,
            "file": norm_path,
            "algorithm": algo_name.upper(),
            "hash": digest,
            "size_bytes": size_bytes,
            "message": f"{algo_name.upper()} ({os.path.basename(norm_path)}): {digest}"
        }
    except Exception as err:
        return {
            "success": False,
            "file": norm_path,
            "message": f"Failed to compute hash: {err}"
        }


def verify_checksum(file_path: str, expected_hash: str, algorithm: str = None) -> dict:
    """
    Verifies if a file matches an expected checksum. Auto-detects algorithm by length if not specified.
    """
    if not expected_hash or not isinstance(expected_hash, str):
        return {"success": False, "message": "Expected hash string is required."}

    clean_hash = expected_hash.strip().lower()
    if not algorithm:
        length = len(clean_hash)
        if length == 32:
            algorithm = "md5"
        elif length == 40:
            algorithm = "sha1"
        elif length == 128:
            algorithm = "sha512"
        else:
            algorithm = "sha256"

    calc_res = hash_file(file_path, algorithm=algorithm)
    if not calc_res.get("success"):
        return calc_res

    actual = calc_res.get("hash", "").lower()
    matches = (actual == clean_hash)

    status_str = "MATCHES" if matches else "MISMATCH"
    return {
        "success": True,
        "matches": matches,
        "algorithm": calc_res.get("algorithm"),
        "expected": clean_hash,
        "actual": actual,
        "message": f"Checksum {status_str}! ({calc_res.get('algorithm')})"
    }
