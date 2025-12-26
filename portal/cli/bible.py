"""
Bible crawler CLI commands.
"""

import json
import os
import sqlite3
import time
from typing import Any, Dict, Optional, List

import click
import httpx
from dotenv import load_dotenv

from portal.libs.http_client import http_client
from portal.libs.logger import logger

# Load environment variables from .env file
load_dotenv()

BASE_URL = "https://api.youversion.com"
YVP_APP_KEY_ENV = "YVP_APP_KEY"
YVP_AUTH_HEADER = "X-YVP-App-Key"


def load_json(path: str, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def atomic_write_json(path: str, obj: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def safe_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in str(s))


class YouVersionDumper:
    def __init__(
        self,
        bible_id: str,
        out_dir: str,
        daily_limit: int,
        sleep_sec: float,
        timeout_sec: float,
        include_headings: bool,
        include_notes: bool,
        format_: str,
    ):
        self.bible_id = str(bible_id)
        self.out_dir = out_dir
        self.daily_limit = daily_limit
        self.sleep_sec = sleep_sec
        self.timeout_sec = timeout_sec
        self.include_headings = include_headings
        self.include_notes = include_notes
        self.format_ = format_
        self.max_retries = 3  # Maximum retries for timeout/connection errors
        self.retry_interval = 5  # Seconds between retries

        # Prepare headers for HTTP requests
        self.headers = {"Accept": "application/json"}

        # Get YVP_APP_KEY from environment variable
        yvp_app_key = os.environ.get(YVP_APP_KEY_ENV)
        if yvp_app_key:
            self.headers[YVP_AUTH_HEADER] = yvp_app_key

        self.root_dir = os.path.join(out_dir, self.bible_id)
        self.state_path = os.path.join(self.root_dir, "state.json")
        self.meta_dir = os.path.join(self.root_dir, "meta")
        self.db_path = os.path.join(self.root_dir, "passages.db")

        self.state = load_json(
            self.state_path,
            {
                "bible_id": self.bible_id,
                "requests_today": 0,
                "last_book_index": 0,
                "last_chapter_index": 0,
                "last_verse_index": 0,
                "done": False,
                "updated_at": None,
                "rate_limit_info": None,
            },
        )

        if str(self.state.get("bible_id")) != self.bible_id:
            self.state = {
                "bible_id": self.bible_id,
                "requests_today": 0,
                "last_book_index": 0,
                "last_chapter_index": 0,
                "last_verse_index": 0,
                "done": False,
                "updated_at": None,
                "rate_limit_info": None,
            }

        # Initialize SQLite database
        self._init_database()

    def _save_state(self):
        self.state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        atomic_write_json(self.state_path, self.state)

    def _init_database(self):
        """Initialize SQLite database with verses table."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bible_id TEXT NOT NULL,
                book_id TEXT NOT NULL,
                chapter INTEGER NOT NULL,
                verse INTEGER NOT NULL,
                passage_id TEXT NOT NULL UNIQUE,
                format TEXT,
                include_headings INTEGER,
                include_notes INTEGER,
                data TEXT NOT NULL,
                created_at TEXT,
                UNIQUE(bible_id, book_id, chapter, verse)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_passage_id ON verses(passage_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_book_chapter_verse 
            ON verses(bible_id, book_id, chapter, verse)
        """)

        conn.commit()
        conn.close()

    def _insert_verse(
        self,
        book_id: str,
        chapter: Any,
        verse: Any,
        passage_id: str,
        params: Dict[str, Any],
        data: Any,
    ):
        """Insert or replace a verse in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Convert chapter and verse to integers if possible
        try:
            chapter_int = int(chapter) if str(chapter).isdigit() else None
        except (ValueError, TypeError):
            chapter_int = None

        try:
            verse_int = int(verse) if str(verse).isdigit() else None
        except (ValueError, TypeError):
            verse_int = None

        # Use integer if available, otherwise use string representation
        chapter_value = chapter_int if chapter_int is not None else str(chapter)
        verse_value = verse_int if verse_int is not None else str(verse)

        cursor.execute("""
            INSERT OR REPLACE INTO verses (
                bible_id, book_id, chapter, verse, passage_id,
                format, include_headings, include_notes, data, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.bible_id,
            book_id,
            chapter_value,
            verse_value,
            passage_id,
            params.get("format"),
            1 if params.get("include_headings") == "true" else 0,
            1 if params.get("include_notes") == "true" else 0,
            json.dumps(data, ensure_ascii=False),
            time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        ))

        conn.commit()
        conn.close()

    def _count_request(self):
        """Count request without stopping."""
        self.state["requests_today"] += 1
        self._save_state()

    def _parse_rate_limit_headers(self, response) -> Dict[str, Any]:
        """Parse rate limit headers from response."""
        rate_limit_info = {}
        if not hasattr(response, "headers"):
            return rate_limit_info

        headers = response.headers

        # X-RateLimit-Limit: Maximum requests per time window
        limit_header = headers.get("X-RateLimit-Limit")
        if limit_header:
            try:
                rate_limit_info["limit"] = int(limit_header)
            except (ValueError, TypeError):
                pass

        # X-RateLimit-Remaining: Remaining requests in current window
        remaining_header = headers.get("X-RateLimit-Remaining")
        if remaining_header:
            try:
                rate_limit_info["remaining"] = int(remaining_header)
            except (ValueError, TypeError):
                pass

        # X-RateLimit-Reset: Time when the rate limit resets
        reset_header = headers.get("X-RateLimit-Reset")
        if reset_header:
            rate_limit_info["reset"] = reset_header

        return rate_limit_info

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        self._count_request()
        url = f"{BASE_URL}{path}"

        try:
            session = (
                http_client.create(url)
                .add_headers(self.headers)
                .timeout(int(self.timeout_sec))
                .retry(self.max_retries, self.retry_interval)
            )

            if params:
                for key, value in params.items():
                    session.add_query(key, value)

            response = session.get()

        except (
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.TimeoutException,
            TimeoutError,
        ) as timeout_exc:
            # http_client retry 後仍然失敗，保存狀態並停止
            error_msg = (
                f"請求超時 (Read operation timed out): {url} "
                f"(已重試 {self.max_retries} 次)"
            )
            logger.error(
                error_msg,
                extra={
                    "url": url,
                    "retry_count": self.max_retries,
                    "timeout_sec": self.timeout_sec,
                    "exception": str(timeout_exc),
                },
            )
            self._save_state()
            raise SystemExit(
                f"{error_msg}。已保存 state，請下次再跑。"
            ) from timeout_exc

        except Exception as exc:
            # 其他異常，記錄並重新拋出
            logger.error(
                "請求發生未預期的錯誤: %s",
                str(exc),
                extra={"url": url, "exception_type": type(exc).__name__},
            )
            raise

        # Handle 429 (Too Many Requests) - parse headers and stop
        if response.status_code == 429:
            # Parse rate limit headers
            rate_limit_info = self._parse_rate_limit_headers(response)
            self.state["rate_limit_info"] = rate_limit_info

            # Log error details (status code and error message)
            error_message = "收到 429 (Too Many Requests) 狀態碼"
            if rate_limit_info:
                details = []
                if "limit" in rate_limit_info:
                    details.append(f"限制: {rate_limit_info['limit']}")
                if "remaining" in rate_limit_info:
                    details.append(f"剩餘: {rate_limit_info['remaining']}")
                if "reset" in rate_limit_info:
                    details.append(f"重置時間: {rate_limit_info['reset']}")
                if details:
                    error_message += f" ({', '.join(details)})"

            # Try to parse error response body
            try:
                error_body = response.json() if hasattr(response, "json") else None
                if error_body:
                    logger.error(
                        "Rate limit error response: %s",
                        error_body,
                        extra={"status_code": 429, "url": url},
                    )
            except (ValueError, TypeError, AttributeError):
                error_text = response.text[:500] if hasattr(response, "text") else ""
                if error_text:
                    logger.error(
                        "Rate limit error: %s",
                        error_text,
                        extra={"status_code": 429, "url": url},
                    )

            logger.warning(
                error_message,
                extra={
                    "status_code": 429,
                    "url": url,
                    "rate_limit_info": rate_limit_info,
                },
            )

            self._save_state()
            raise SystemExit(f"{error_message}。已保存 state，請下次再跑。")

        # Handle other errors (4xx, 5xx)
        if response.status_code >= 400:
            error_text = response.text[:5000] if hasattr(response, "text") else ""
            error_details = f"HTTP {response.status_code} GET {url}"

            # Log error details
            logger.error(
                error_details,
                extra={"status_code": response.status_code, "url": url},
            )

            # Try to parse error response body for better error message
            try:
                error_body = response.json() if hasattr(response, "json") else None
                if error_body and isinstance(error_body, dict):
                    error_msg = error_body.get("message") or error_body.get("error")
                    if error_msg:
                        error_details += f": {error_msg}"
            except (ValueError, TypeError, AttributeError):
                if error_text:
                    error_details += f": {error_text[:500]}"

            raise RuntimeError(error_details)

        if self.sleep_sec:
            time.sleep(self.sleep_sec)

        return response.json()

    def dump_meta(self) -> Dict[str, Any]:
        bible = self._get(f"/v1/bibles/{self.bible_id}")
        atomic_write_json(os.path.join(self.meta_dir, "bible.json"), bible)

        index = self._get(f"/v1/bibles/{self.bible_id}/index")
        atomic_write_json(os.path.join(self.meta_dir, "index.json"), index)
        return index

    def _books(self, index_obj: Any) -> List[Dict[str, Any]]:
        if isinstance(index_obj, dict) and isinstance(index_obj.get("books"), list):
            return index_obj["books"]
        # 容錯：若包在 data
        if isinstance(index_obj, dict) and isinstance(index_obj.get("data"), dict):
            v = index_obj["data"].get("books")
            if isinstance(v, list):
                return v
        raise ValueError("index 回傳格式找不到 books[]。")

    def dump_passages_by_chapter_from_index(self, index_obj: Dict[str, Any]):
        books = self._books(index_obj)

        start_bi = int(self.state.get("last_book_index", 0))
        start_ci = int(self.state.get("last_chapter_index", 0))
        start_vi = int(self.state.get("last_verse_index", 0))

        params = {
            "format": self.format_,
            "include_headings": str(self.include_headings).lower(),
            "include_notes": str(self.include_notes).lower(),
        }

        for bi in range(start_bi, len(books)):
            book = books[bi]
            book_id = book.get("id")  # 例如 GEN
            if not book_id:
                raise ValueError(f"book 缺少 id：{book}")

            chapters = book.get("chapters")
            if not isinstance(chapters, list):
                raise ValueError(f"book.chapters 不是 list：book_id={book_id}")

            ci0 = start_ci if bi == start_bi else 0

            for ci in range(ci0, len(chapters)):
                ch = chapters[ci]
                ch_num = ch.get("title") or ch.get("id") or (ci + 1)

                verses = ch.get("verses")
                if not isinstance(verses, list):
                    raise ValueError(
                        f"chapter.verses 不是 list：book_id={book_id}, chapter={ch_num}"
                    )

                vi0 = start_vi if (bi == start_bi and ci == start_ci) else 0

                for vi in range(vi0, len(verses)):
                    verse = verses[vi]
                    verse_num = verse.get("title") or verse.get("id") or (vi + 1)
                    passage_id = verse.get("passage_id")  # 例如 GEN.1.1
                    if not passage_id:
                        raise ValueError(
                            f"verse 缺少 passage_id：book_id={book_id}, chapter={ch_num}, verse={verse}"
                        )

                    data = self._get(
                        f"/v1/bibles/{self.bible_id}/passages/{passage_id}",
                        params=params,
                    )

                    self._insert_verse(
                        book_id=book_id,
                        chapter=ch_num,
                        verse=verse_num,
                        passage_id=passage_id,
                        params=params,
                        data=data,
                    )

                    # 更新斷點：下一節
                    self.state["last_book_index"] = bi
                    self.state["last_chapter_index"] = ci
                    self.state["last_verse_index"] = vi + 1
                    self.state["done"] = False
                    self._save_state()

                # 章節完成
                self.state["last_book_index"] = bi
                self.state["last_chapter_index"] = ci + 1
                self.state["last_verse_index"] = 0
                self._save_state()

            # 書卷完成
            self.state["last_book_index"] = bi + 1
            self.state["last_chapter_index"] = 0
            self.state["last_verse_index"] = 0
            self._save_state()

        self.state["done"] = True
        self._save_state()


def dump_bible(
    bible_id: str,
    out_dir: str,
    daily_limit: int,
    sleep_sec: float,
    timeout_sec: float,
    include_headings: bool,
    include_notes: bool,
    format_: str,
    meta_only: bool,
):
    """
    Dump YouVersion Bible metadata and passages.
    """
    dumper = YouVersionDumper(
        bible_id=bible_id,
        out_dir=out_dir,
        daily_limit=daily_limit,
        sleep_sec=sleep_sec,
        timeout_sec=timeout_sec,
        include_headings=include_headings,
        include_notes=include_notes,
        format_=format_,
    )

    try:
        click.echo(click.style(f"Dumping Bible ID: {bible_id}", fg="cyan"))
        index_obj = dumper.dump_meta()
        click.echo(click.style("Metadata dumped successfully.", fg="green"))

        if not meta_only:
            click.echo(click.style("Dumping passages...", fg="cyan"))
            dumper.dump_passages_by_chapter_from_index(index_obj)
            click.echo(click.style("All passages dumped successfully.", fg="green"))
        else:
            click.echo(click.style("Meta-only mode: skipping passages.", fg="yellow"))
    except SystemExit as e:
        click.echo(click.style(str(e), fg="yellow"))
        logger.info(str(e))
        raise
    except Exception as e:
        click.echo(click.style(f"Error dumping Bible: {e}", fg="red"))
        logger.exception(e)
        raise


def dump_bible_process(
    bible_id: str,
    out_dir: str,
    daily_limit: int,
    sleep_sec: float,
    timeout_sec: float,
    include_headings: bool,
    include_notes: bool,
    format_: str,
    meta_only: bool,
):
    """Synchronous entry to run Bible dumping."""
    dump_bible(
        bible_id=bible_id,
        out_dir=out_dir,
        daily_limit=daily_limit,
        sleep_sec=sleep_sec,
        timeout_sec=timeout_sec,
        include_headings=include_headings,
        include_notes=include_notes,
        format_=format_,
        meta_only=meta_only,
    )
