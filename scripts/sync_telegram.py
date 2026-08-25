#!/usr/bin/env python3
"""Batch-sync pending Telegram PDF records to a Hugging Face Dataset."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


MAX_RETRIES = int(os.environ.get("SYNC_MAX_RETRIES", "5"))
BASE_DELAY = float(os.environ.get("SYNC_BASE_DELAY_SECONDS", "2"))
SYNC_API_URL = os.environ.get("SYNC_API_URL", "").rstrip("/")
SYNC_SECRET = os.environ.get("MY_COMPUTER_SYNC_SECRET", "")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
LOCAL_BOT_API = os.environ.get("LOCAL_BOT_API", "http://127.0.0.1:8081/bot").rstrip("/")
LOCAL_FILE_API = os.environ.get("LOCAL_FILE_API", "http://127.0.0.1:8081/file").rstrip("/")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_REPO_ID = os.environ.get("HF_REPO_ID", "")
HF_REPO_TYPE = os.environ.get("HF_REPO_TYPE", "dataset")
WORK_DIR = pathlib.Path(os.environ.get("SYNC_WORK_DIR", ".sync-work"))


def request_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"accept": "application/json", "user-agent": "my-computer-telegram-sync"}
    if SYNC_SECRET and url.startswith(SYNC_API_URL):
        headers["x-my-computer-sync-secret"] = SYNC_SECRET
    if body is not None:
        headers["content-type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def telegram_json(method: str, payload: dict[str, Any]) -> Any:
    return request_json(f"{LOCAL_BOT_API}/{BOT_TOKEN}/{method}", "POST", payload)


def telegram_status(chat_id: str, message_id: str, text: str) -> None:
    if not chat_id or not message_id:
        return
    try:
        request_json(f"{LOCAL_BOT_API}/{BOT_TOKEN}/editMessageText", "POST", {
            "chat_id": int(chat_id),
            "message_id": int(message_id),
            "text": text,
        })
    except Exception as exc:
        print(f"status update skipped: {exc}", file=sys.stderr)


def update_record(record_id: str, status: str, **fields: Any) -> None:
    request_json(f"{SYNC_API_URL}", "POST", {
        "id": record_id,
        "sync_status": status,
        "sync_job_id": os.environ.get("GITHUB_RUN_ID", "my-computer-manual"),
        **fields,
    })


def download_telegram_file(record: dict[str, Any], destination: pathlib.Path) -> None:
    file_id = record.get("source_file_id")
    if not file_id:
        raise RuntimeError("record has no source_file_id")
    info = telegram_json("getFile", {"file_id": file_id})
    file_path = (info.get("result") or {}).get("file_path")
    if not file_path:
        raise RuntimeError("Telegram did not return a file path")
    url = f"{LOCAL_FILE_API}/{BOT_TOKEN}/{urllib.parse.quote(file_path, safe='/')}"
    request = urllib.request.Request(url, headers={"user-agent": "my-computer-telegram-sync"})
    with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(8 * 1024 * 1024)
            if not chunk:
                break
            output.write(chunk)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def category_path(record: dict[str, Any]) -> str:
    category = str(record.get("category_id") or "unassigned").replace("/", "-").replace("..", "-")
    return category


def safe_name(name: str) -> str:
    cleaned = "".join(character if character.isalnum() or character in " ._-" else "_" for character in name).strip()
    return cleaned[:160] or "document.pdf"


def upload_file(local_path: pathlib.Path, repo_path: str, commit_message: str) -> None:
    from huggingface_hub import HfApi

    api = HfApi(token=HF_TOKEN)
    api.upload_file(
        path_or_fileobj=str(local_path),
        path_in_repo=repo_path,
        repo_id=HF_REPO_ID,
        repo_type=HF_REPO_TYPE,
        commit_message=commit_message,
    )


def upload_json(value: dict[str, Any], repo_path: str, commit_message: str) -> None:
    from huggingface_hub import HfApi

    api = HfApi(token=HF_TOKEN)
    api.upload_file(
        path_or_fileobj=io.BytesIO(json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")),
        path_in_repo=repo_path,
        repo_id=HF_REPO_ID,
        repo_type=HF_REPO_TYPE,
        commit_message=commit_message,
    )


def process_record(record: dict[str, Any]) -> None:
    record_id = str(record["id"])
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    local_path = WORK_DIR / f"{record_id}.pdf"
    update_record(record_id, "uploading")
    download_telegram_file(record, local_path)
    checksum = sha256_file(local_path)
    folder = category_path(record)
    pdf_path = f"pdfs/{folder}/{record_id}--{safe_name(str(record.get('title') or 'document.pdf'))}"
    metadata_path = f"metadata/{record_id}.json"
    text_path = f"text/{record_id}.txt"
    metadata = {**record, "sha256": checksum, "hf_path": pdf_path, "sync_job_id": os.environ.get("GITHUB_RUN_ID", "my-computer-manual")}
    upload_file(local_path, pdf_path, f"Sync PDF {record_id}")
    text_local_path = WORK_DIR / f"{record_id}.txt"
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(local_path), strict=False)
        with text_local_path.open("w", encoding="utf-8") as text_output:
            for page in reader.pages:
                text_output.write(page.extract_text() or "")
                text_output.write("\\n\\n")
        upload_file(text_local_path, text_path, f"Sync extracted text {record_id}")
    except Exception as exc:
        metadata["text_extraction_error"] = str(exc)[:300]
    upload_json(metadata, metadata_path, f"Sync metadata {record_id}")
    update_record(record_id, "synced", hf_path=pdf_path, hf_url=f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/{urllib.parse.quote(pdf_path, safe='/')}", sha256=checksum, sync_error="")
    local_path.unlink(missing_ok=True)
    text_local_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--chat-id", default=os.environ.get("SYNC_CHAT_ID", ""))
    parser.add_argument("--status-message-id", default=os.environ.get("SYNC_STATUS_MESSAGE_ID", ""))
    args = parser.parse_args()
    if not all([SYNC_API_URL, SYNC_SECRET, BOT_TOKEN, HF_TOKEN, HF_REPO_ID]):
        raise SystemExit("SYNC_API_URL, MY_COMPUTER_SYNC_SECRET, TELEGRAM_BOT_TOKEN, HF_TOKEN, and HF_REPO_ID are required")
    if args.shard_index >= args.shard_count:
        return 0
    records = request_json(f"{SYNC_API_URL}?limit=500").get("records", [])
    selected = [record for index, record in enumerate(records) if index % args.shard_count == args.shard_index]
    telegram_status(args.chat_id, args.status_message_id, f"🔄 My-Computer sync running: batch {args.shard_index + 1}/{args.shard_count}, {len(selected)} PDF(s) assigned.")
    completed = 0
    for record in selected:
        record_id = str(record["id"])
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                process_record(record)
                completed += 1
                break
            except Exception as exc:
                update_record(record_id, "retry_wait" if attempt < MAX_RETRIES else "failed", sync_error=str(exc)[:500])
                if attempt == MAX_RETRIES:
                    print(f"{record_id}: failed after {attempt} attempts: {exc}", file=sys.stderr)
                else:
                    time.sleep(BASE_DELAY * (2 ** (attempt - 1)))
    telegram_status(args.chat_id, args.status_message_id, f"✅ My-Computer sync batch {args.shard_index + 1}/{args.shard_count} complete: {completed}/{len(selected)} uploaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
