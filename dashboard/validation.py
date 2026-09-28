"""Client-side validation for log files uploaded to the pipeline."""
import gzip
import json

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit
REQUIRED_LOG_FIELDS = ("timestamp", "level", "service", "message")
VALID_SEVERITY_LEVELS = {"INFO", "WARN", "WARNING", "ERROR", "CRITICAL"}
SUPPORTED_EXTENSIONS = (".json", ".jsonl", ".gz")


def validate_log_file(file) -> tuple[bool, str | None]:
    """Validate log file size, format, decompression, and required JSONL fields.

    Returns:
        tuple[bool, str | None]: (is_valid, error_message)
    """
    if file is None:
        return False, "Please choose a file to upload."

    # Validate file size
    if file.size > MAX_FILE_SIZE_BYTES:
        size_mb = file.size / (1024 * 1024)
        return (
            False,
            f"File exceeds the 10 MB limit (current size: {size_mb:.2f} MB). "
            "Please split or compress the log batch before uploading.",
        )

    filename = file.name.lower()
    if not any(filename.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
        return (
            False,
            f"Unsupported file format '{file.name}'. "
            "Accepted formats are .json, .jsonl, or .json.gz.",
        )

    raw_bytes = file.getvalue()
    if not raw_bytes or len(raw_bytes.strip()) == 0:
        return False, "The uploaded file is empty. Please provide a valid log file."

    # Handle gzip decompress if .gz
    if filename.endswith(".gz"):
        try:
            decompressed = gzip.decompress(raw_bytes)
        except Exception as e:
            return (
                False,
                f"Failed to decompress gzip archive: {e}. "
                "Ensure the archive is not corrupted and was compressed with gzip.",
            )
        try:
            text = decompressed.decode("utf-8")
        except UnicodeDecodeError:
            return (
                False,
                "Decompressed archive content is not valid UTF-8 text.",
            )
    else:
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return (
                False,
                "File encoding error: expected UTF-8 text. "
                "Please verify file encoding and upload again.",
            )

    # Check non-empty lines
    lines = text.splitlines()
    checked_count = 0

    for line_idx, line in enumerate(lines, start=1):
        line_clean = line.strip()
        if not line_clean:
            continue

        # Parse JSON
        try:
            record = json.loads(line_clean)
        except Exception as err:
            return (
                False,
                f"Line {line_idx} is not valid JSON: {err}. "
                "Each line in the file must be a standalone JSON object.",
            )

        if not isinstance(record, dict):
            return (
                False,
                f"Line {line_idx} is a JSON array or scalar instead of a JSON object. "
                "Ensure each line represents an individual log entry object.",
            )

        # Verify required fields
        for field in REQUIRED_LOG_FIELDS:
            if field not in record:
                return (
                    False,
                    f"Line {line_idx} is missing required field '{field}'. "
                    f"Required fields: {', '.join(REQUIRED_LOG_FIELDS)}.",
                )

        # Verify severity level
        level_str = str(record.get("level", "")).upper()
        if level_str not in VALID_SEVERITY_LEVELS:
            return (
                False,
                f"Line {line_idx} contains invalid level '{record.get('level')}'. "
                f"Expected one of: INFO, WARN, ERROR, CRITICAL.",
            )

        checked_count += 1
        if checked_count >= 25:
            break

    if checked_count == 0:
        return False, "File does not contain any valid log records."

    return True, None
