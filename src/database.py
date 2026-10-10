import psycopg2
from psycopg2.extras import Json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import os
from datetime import datetime

class DatabaseManager:
    """Manages connections and operations for the Supabase PostgreSQL database."""

    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()

        self.connection_params = {
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT", "5432"),
            "dbname": os.getenv("DB_NAME")
        }

        self.connection = None
        self.cursor = None

    def connect(self):
        """Establish database connection."""
        self.connection = psycopg2.connect(**self.connection_params)
        self.cursor = self.connection.cursor()
        self.cursor.execute("SET TIME ZONE 'UTC'")
        print(f"✅ Database connected: {self.connection_params['host']}")

    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("✅ Database connection closed.")

    def create_tables(self):
        """Creates the tables needed to store results.json data."""

        # Create gambling_urls table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS gambling_urls (
            id SERIAL PRIMARY KEY,
            url TEXT NOT NULL,
            keyword_used TEXT NOT NULL,
            collected_at TIMESTAMP WITH TIME ZONE NOT NULL,
            is_illegal BOOLEAN NOT NULL,
            gemini_confidence NUMERIC(3, 2),
            gemini_reason TEXT,
            gemini_error TEXT,
            detected_keywords JSONB,
            category TEXT,
            screenshot_url TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """

        # screenshot_url is written by the report worker; add it to tables created before it existed
        add_screenshot_column = """
        ALTER TABLE gambling_urls ADD COLUMN IF NOT EXISTS screenshot_url TEXT;
        """

        # category (operator / promotion) was added later; add it to existing tables
        add_category_column = """
        ALTER TABLE gambling_urls ADD COLUMN IF NOT EXISTS category TEXT;
        """

        # Index on url for fast lookups
        create_index_url = """
        CREATE INDEX IF NOT EXISTS idx_gambling_urls_url
        ON gambling_urls(url);
        """

        # Index on is_illegal for filtering
        create_index_illegal = """
        CREATE INDEX IF NOT EXISTS idx_gambling_urls_is_illegal
        ON gambling_urls(is_illegal);
        """

        # Index on collected_at for time-based sorting
        create_index_collected = """
        CREATE INDEX IF NOT EXISTS idx_gambling_urls_collected_at
        ON gambling_urls(collected_at DESC);
        """

        # GIN index on detected_keywords JSONB for keyword search
        create_index_keywords = """
        CREATE INDEX IF NOT EXISTS idx_gambling_urls_detected_keywords
        ON gambling_urls USING GIN(detected_keywords);
        """

        # Trigger function to auto-update updated_at
        create_trigger_function = """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """

        # Trigger to call the function on update
        create_trigger = """
        DROP TRIGGER IF EXISTS update_gambling_urls_updated_at ON gambling_urls;
        CREATE TRIGGER update_gambling_urls_updated_at
            BEFORE UPDATE ON gambling_urls
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """

        self.cursor.execute(create_table_query)
        self.cursor.execute(add_screenshot_column)
        self.cursor.execute(add_category_column)
        self.cursor.execute(create_index_url)
        self.cursor.execute(create_index_illegal)
        self.cursor.execute(create_index_collected)
        self.cursor.execute(create_index_keywords)
        self.cursor.execute(create_trigger_function)
        self.cursor.execute(create_trigger)
        self.connection.commit()

        print("✅ Table and indexes created: gambling_urls")

    def insert_url_data(self, url_data: Dict[str, Any]) -> bool:
        """
        Inserts or updates a URL record.
        - New URL: INSERT
        - Existing URL with keyword_used != 'manual report': UPDATE
        - Existing URL with keyword_used == 'manual report': INSERT new row
        """
        url = url_data.get("url")

        # Find an existing row that is eligible for update (not a manual report)
        find_query = """
        SELECT id FROM gambling_urls
        WHERE url = %s AND keyword_used != 'manual report'
        LIMIT 1;
        """
        self.cursor.execute(find_query, (url,))
        result = self.cursor.fetchone()

        collected_at = url_data.get("collected_at")
        if isinstance(collected_at, str):
            collected_at = datetime.fromisoformat(collected_at)

        if result:
            entry_id_to_update = result[0]
            update_query = """
            UPDATE gambling_urls SET
                keyword_used = %s,
                collected_at = %s,
                is_illegal = %s,
                gemini_confidence = %s,
                gemini_reason = %s,
                gemini_error = %s,
                detected_keywords = %s,
                category = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
            """
            self.cursor.execute(update_query, (
                url_data.get("keyword_used"),
                collected_at,
                url_data.get("is_illegal"),
                url_data.get("gemini_confidence"),
                url_data.get("gemini_reason"),
                url_data.get("gemini_error"),
                Json(url_data.get("detected_keywords", [])),
                url_data.get("category"),
                entry_id_to_update
            ))
        else:
            insert_query = """
            INSERT INTO gambling_urls (
                url, keyword_used, collected_at, is_illegal,
                gemini_confidence, gemini_reason, gemini_error, detected_keywords, category
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            self.cursor.execute(insert_query, (
                url_data.get("url"),
                url_data.get("keyword_used"),
                collected_at,
                url_data.get("is_illegal"),
                url_data.get("gemini_confidence"),
                url_data.get("gemini_reason"),
                url_data.get("gemini_error"),
                Json(url_data.get("detected_keywords", [])),
                url_data.get("category")
            ))

        self.connection.commit()
        return True

    def insert_bulk_url_data(self, url_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Bulk-inserts multiple URL records. Returns the records that failed to insert."""
        failed = []

        for url_data in url_data_list:
            try:
                self.insert_url_data(url_data)
            except Exception as e:
                print(f"❌ Failed to insert URL ({url_data.get('url')}): {e}")
                self.connection.rollback()
                failed.append(url_data)

        return failed

    def get_illegal_urls(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieves illegal gambling site URLs from the database."""
        query = """
        SELECT url, keyword_used, collected_at, is_illegal,
               gemini_confidence, gemini_reason, detected_keywords
        FROM gambling_urls
        WHERE is_illegal = TRUE
        ORDER BY collected_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        self.cursor.execute(query)

        results = []
        for row in self.cursor.fetchall():
            results.append({
                "url": row[0],
                "keyword_used": row[1],
                "collected_at": row[2],
                "is_illegal": row[3],
                "gemini_confidence": row[4],
                "gemini_reason": row[5],
                "detected_keywords": row[6]
            })

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Retrieves database statistics."""
        stats_query = """
        SELECT
            COUNT(*) as total_urls,
            SUM(CASE WHEN is_illegal = TRUE THEN 1 ELSE 0 END) as illegal_count,
            SUM(CASE WHEN is_illegal = FALSE THEN 1 ELSE 0 END) as legal_count,
            AVG(CASE WHEN is_illegal = TRUE THEN gemini_confidence END) as avg_illegal_confidence,
            MIN(collected_at) as first_collected,
            MAX(collected_at) as last_collected
        FROM gambling_urls;
        """

        self.cursor.execute(stats_query)
        row = self.cursor.fetchone()

        return {
            "total_urls": row[0],
            "illegal_count": row[1],
            "legal_count": row[2],
            "avg_illegal_confidence": float(row[3]) if row[3] else 0.0,
            "first_collected": row[4],
            "last_collected": row[5]
        }


def import_from_json(json_file_path: str, delete_after_import: bool = True):
    """
    Imports data from a results.json file into the database.

    Args:
        json_file_path: Path to the JSON file.
        delete_after_import: Whether to delete the JSON file after a successful import (default: True).
    """
    import json

    if not os.path.exists(json_file_path):
        print(f"⚠️ File not found: {json_file_path}")
        return

    with open(json_file_path, 'r', encoding='utf-8') as f:
        url_data_list = json.load(f)

    if not url_data_list:
        print(f"⚠️ File is empty: {json_file_path}")
        return

    print(f"📄 Read {len(url_data_list)} URL records.")

    # Records crawled without Gemini have no verdict and can't satisfy is_illegal NOT NULL
    unclassified = [d for d in url_data_list if d.get("is_illegal") is None]
    classified = [d for d in url_data_list if d.get("is_illegal") is not None]
    if unclassified:
        print(f"⚠️ Skipping {len(unclassified)} unclassified records (no Gemini verdict); they stay in the JSON file.")

    db = DatabaseManager()
    db.connect()

    db.create_tables()

    failed = db.insert_bulk_url_data(classified)
    inserted_count = len(classified) - len(failed)
    print(f"✅ Saved {inserted_count} URL records to the database.")

    stats = db.get_statistics()
    print("\n📊 Database statistics:")
    print(f"  - Total URLs: {stats['total_urls']}")
    print(f"  - Illegal sites: {stats['illegal_count']}")
    print(f"  - Legal sites: {stats['legal_count']}")
    print(f"  - Avg confidence (illegal): {stats['avg_illegal_confidence']:.2f}")

    db.disconnect()

    if not delete_after_import:
        return

    remaining = unclassified + failed
    if remaining:
        # Keep only the records that were not imported so nothing is lost
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(remaining, f, indent=2, ensure_ascii=False)
        print(f"\n📝 Kept {len(remaining)} records that were not imported in {json_file_path}")
    else:
        os.remove(json_file_path)
        print(f"\n🗑️ Deleted JSON file: {json_file_path}")
        print("   (A new results.json will be created on the next crawl)")


if __name__ == "__main__":
    import_from_json("results.json")
