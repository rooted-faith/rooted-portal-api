"""
Import Bible data from bible_data directory to database
"""
import asyncio
import json
import sqlite3
import time
from pathlib import Path
from uuid import UUID

import click

from portal.container import Container
from portal.libs.logger import logger
from portal.models import BibleBook, BibleVerse, BibleVersion


async def import_bible_data(bible_id: str, data_dir: str = "bible_data"):
    """
    Import Bible data from bible_data directory to database

    :param bible_id: Bible ID (e.g., '1392')
    :param data_dir: Directory containing bible data (default: 'bible_data')
    """
    container = Container()
    session = container.db_session()

    bible_dir = Path(data_dir) / bible_id
    meta_dir = bible_dir / "meta"
    bible_json_path = meta_dir / "bible.json"
    index_json_path = meta_dir / "index.json"
    passages_db_path = bible_dir / "passages.db"

    # Check if files exist
    if not bible_json_path.exists():
        raise FileNotFoundError(f"Bible metadata not found: {bible_json_path}")
    if not index_json_path.exists():
        raise FileNotFoundError(f"Bible index not found: {index_json_path}")
    if not passages_db_path.exists():
        raise FileNotFoundError(f"Passages database not found: {passages_db_path}")

    try:
        # 1. Load and import Bible Version
        click.echo(f"Loading Bible version data from {bible_json_path}...")
        with open(bible_json_path, encoding="utf-8") as f:
            bible_meta = json.load(f)

        # Convert organization_id to UUID if present
        organization_id = None
        if bible_meta.get("organization_id"):
            try:
                organization_id = UUID(bible_meta["organization_id"])
            except (ValueError, TypeError):
                logger.warning(f"Invalid organization_id: {bible_meta.get('organization_id')}")

        click.echo(f"Importing Bible version: {bible_meta.get('localized_title', bible_meta.get('title'))}...")
        await (
            session.insert(BibleVersion)
            .values(
                youversion_bible_id=str(bible_meta["id"]),
                abbreviation=bible_meta["abbreviation"],
                title=bible_meta["title"],
                localized_title=bible_meta["localized_title"],
                localized_abbreviation=bible_meta.get("localized_abbreviation"),
                language_tag=bible_meta["language_tag"],
                copyright=bible_meta.get("copyright"),
                promotional_content=bible_meta.get("promotional_content"),
                publisher_url=bible_meta.get("publisher_url"),
                youversion_deep_link=bible_meta.get("youversion_deep_link"),
                organization_id=organization_id,
                is_active=True,
            )
            .on_conflict_do_update(
                index_elements=[BibleVersion.youversion_bible_id],
                set_={
                    "abbreviation": bible_meta["abbreviation"],
                    "title": bible_meta["title"],
                    "localized_title": bible_meta["localized_title"],
                    "localized_abbreviation": bible_meta.get("localized_abbreviation"),
                    "language_tag": bible_meta["language_tag"],
                    "copyright": bible_meta.get("copyright"),
                    "promotional_content": bible_meta.get("promotional_content"),
                    "publisher_url": bible_meta.get("publisher_url"),
                    "youversion_deep_link": bible_meta.get("youversion_deep_link"),
                    "organization_id": organization_id,
                    "is_active": True,
                },
            )
            .execute()
        )
        await session.commit()

        # Get the version ID
        version = await (
            session.select(BibleVersion.id)
            .where(BibleVersion.youversion_bible_id == str(bible_meta["id"]))
            .fetchval()
        )
        if not version:
            raise ValueError(f"Failed to get Bible version ID for {bible_meta['id']}")

        click.echo(f"Bible version imported: {version}")

        # 2. Load and import Bible Books
        click.echo(f"Loading Bible books data from {index_json_path}...")
        with open(index_json_path, encoding="utf-8") as f:
            index_data = json.load(f)

        books_data = index_data.get("books", [])
        click.echo(f"Importing {len(books_data)} books...")

        book_id_map = {}  # Map book_code to book_id (UUID)
        base_timestamp = time.time()  # Base timestamp for sequence calculation
        sort_order = 1  # Sort order (1-66 for standard Bible book order)

        for book_data in books_data:
            book_code = book_data["id"]
            book_title = book_data.get("title", "")
            full_title = book_data.get("full_title")
            abbreviation = book_data.get("abbreviation")
            canon = book_data.get("canon", "old_testament")

            # Calculate chapter count from chapters array
            chapters = book_data.get("chapters", [])
            chapter_count = len(chapters) if isinstance(chapters, list) else 0

            # Calculate sequence using base timestamp + small increment to maintain order
            # Use sort_order * 0.001 to preserve relative order while using timestamp format
            sequence = base_timestamp + (sort_order * 0.001)

            # Insert or update book
            await (
                session.insert(BibleBook)
                .values(
                    bible_version_id=version,
                    book_code=book_code,
                    title=book_title,
                    full_title=full_title,
                    abbreviation=abbreviation,
                    canon=canon,
                    sequence=sequence,
                    chapter_count=chapter_count,
                )
                .on_conflict_do_update(
                    index_elements=[BibleBook.bible_version_id, BibleBook.book_code],
                    set_={
                        "title": book_title,
                        "full_title": full_title,
                        "abbreviation": abbreviation,
                        "canon": canon,
                        "sequence": sequence,
                        "chapter_count": chapter_count,
                    },
                )
                .execute()
            )

            # Get the book ID
            book = await (
                session.select(BibleBook.id)
                .where(BibleBook.bible_version_id == version)
                .where(BibleBook.book_code == book_code)
                .fetchval()
            )
            if book:
                book_id_map[book_code] = book

            sort_order += 1

        await session.commit()
        click.echo(f"Imported {len(book_id_map)} books")

        # 3. Load and import Bible Verses
        click.echo(f"Loading verses from {passages_db_path}...")
        conn = sqlite3.connect(passages_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Count total verses
        cursor.execute("SELECT COUNT(*) FROM verses")
        total_verses = cursor.fetchone()[0]
        click.echo(f"Found {total_verses} verses to import...")

        # Fetch verses in batches
        batch_size = 1000
        cursor.execute("SELECT bible_id, book_id, chapter, verse, passage_id, data FROM verses ORDER BY book_id, chapter, verse")

        imported_count = 0
        batch = []

        for row in cursor:
            book_code = row["book_id"]
            book_id = book_id_map.get(book_code)
            if not book_id:
                logger.warning(f"Book not found for book_code: {book_code}, skipping verse {row['passage_id']}")
                continue

            # Parse verse content from JSON data
            try:
                verse_data = json.loads(row["data"])
                content = verse_data.get("content", "")
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse verse data for {row['passage_id']}")
                continue

            chapter = int(row["chapter"]) if row["chapter"] else None
            verse = int(row["verse"]) if row["verse"] else None

            if chapter is None or verse is None:
                logger.warning(f"Invalid chapter/verse for {row['passage_id']}")
                continue

            batch.append({
                "book_id": book_id,
                "chapter": chapter,
                "verse": verse,
                "passage_id": row["passage_id"],
                "content": content,
            })

            if len(batch) >= batch_size:
                # Insert batch
                for verse_data in batch:
                    await (
                        session.insert(BibleVerse)
                        .values(**verse_data)
                        .on_conflict_do_update(
                            index_elements=["book_id", "passage_id"],
                            set_={
                                "chapter": verse_data["chapter"],
                                "verse": verse_data["verse"],
                                "content": verse_data["content"],
                            },
                        )
                        .execute()
                    )

                await session.commit()
                imported_count += len(batch)
                click.echo(f"Imported {imported_count}/{total_verses} verses...")
                batch = []

        # Insert remaining batch
        if batch:
            for verse_data in batch:
                await (
                    session.insert(BibleVerse)
                    .values(**verse_data)
                    .on_conflict_do_update(
                        index_elements=["book_id", "passage_id"],
                        set_={
                            "chapter": verse_data["chapter"],
                            "verse": verse_data["verse"],
                            "content": verse_data["content"],
                        },
                    )
                    .execute()
                )
            await session.commit()
            imported_count += len(batch)

        conn.close()
        click.echo(f"Successfully imported {imported_count} verses")
        click.echo(f"Bible data import completed for {bible_id}")

    except Exception as e:
        click.echo(f"Error importing Bible data: {e}", err=True)
        logger.exception(e)
        await session.rollback()
        raise
    finally:
        await session.close()


def import_bible_data_process(bible_id: str, data_dir: str = "bible_data"):
    """Synchronous entry point for importing Bible data"""
    asyncio.run(import_bible_data(bible_id=bible_id, data_dir=data_dir))

