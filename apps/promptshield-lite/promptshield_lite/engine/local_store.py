"""
SQLite-backed local history store for PromptShield Lite.

Stores precheck decisions for offline analytics and history browsing.
Database is located at ~/.promptshield/history.db by default.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DB_DIR = Path.home() / ".promptshield"
_DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "history.db"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS precheck_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    model           TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    cost_usd        REAL NOT NULL DEFAULT 0.0,
    decision        TEXT NOT NULL,
    classifications TEXT NOT NULL DEFAULT '[]',
    misuse_score    REAL NOT NULL DEFAULT 0.0,
    source          TEXT,
    prompt_hash     TEXT
)
"""

_INSERT_SQL = """
INSERT INTO precheck_history
    (request_id, timestamp, model, user_id, input_tokens, output_tokens,
     cost_usd, decision, classifications, misuse_score, source, prompt_hash)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class LocalStore:
    """
    SQLite-backed persistence layer for PromptShield Lite history.

    Thread-safe for single-process use (SQLite WAL mode).
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """
        Initialise the store.

        Args:
            db_path: Path to the SQLite database file. Defaults to
                     ~/.promptshield/history.db.
        """
        self._db_path = db_path or _DEFAULT_DB_PATH
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create the database directory and schema if they don't exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE_SQL)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path), detect_types=sqlite3.PARSE_DECLTYPES)

    def save(self, response: Any, user_id: str, model: str, source: str = "cli", prompt_hash: str | None = None) -> None:
        """
        Persist a PromptDecisionResponse to the local store.

        Args:
            response:    The PromptDecisionResponse from the precheck engine.
            user_id:     The user identifier for this request.
            model:       The target model identifier.
            source:      Request source tag (e.g. 'cli').
            prompt_hash: Optional SHA-256 hash of the prompt text.
        """
        classifications_json = json.dumps([c.value if hasattr(c, "value") else str(c) for c in response.classifications])
        ts = response.timestamp.isoformat() if hasattr(response.timestamp, "isoformat") else str(response.timestamp)
        decision_val = response.decision.value if hasattr(response.decision, "value") else str(response.decision)

        try:
            with self._connect() as conn:
                conn.execute(
                    _INSERT_SQL,
                    (
                        str(response.request_id),
                        ts,
                        model,
                        user_id,
                        response.estimated_input_tokens,
                        response.estimated_output_tokens,
                        response.estimated_cost_usd,
                        decision_val,
                        classifications_json,
                        response.misuse_score,
                        source,
                        prompt_hash,
                    ),
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.warning("Failed to save history record: %s", e)

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Retrieve recent precheck history records.

        Args:
            limit: Maximum number of records to return (default: 50).

        Returns:
            List of dicts representing history records, newest first.
        """
        try:
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM precheck_history ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    record = dict(row)
                    record["classifications"] = json.loads(record.get("classifications", "[]"))
                    result.append(record)
                return result
        except sqlite3.Error as e:
            logger.warning("Failed to list history: %s", e)
            return []

    def stats(self) -> dict[str, Any]:
        """
        Compute aggregate statistics from the local history.

        Returns:
            Dict with keys: total_requests, total_tokens, total_cost_usd,
            decision_counts (dict), model_counts (dict).
        """
        try:
            with self._connect() as conn:
                total_row = conn.execute(
                    "SELECT COUNT(*), SUM(input_tokens + output_tokens), SUM(cost_usd) FROM precheck_history"
                ).fetchone()
                total_requests = total_row[0] or 0
                total_tokens = total_row[1] or 0
                total_cost = total_row[2] or 0.0

                decision_rows = conn.execute(
                    "SELECT decision, COUNT(*) FROM precheck_history GROUP BY decision"
                ).fetchall()
                decision_counts = {row[0]: row[1] for row in decision_rows}

                model_rows = conn.execute(
                    "SELECT model, COUNT(*) FROM precheck_history GROUP BY model"
                ).fetchall()
                model_counts = {row[0]: row[1] for row in model_rows}

            return {
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 6),
                "decision_counts": decision_counts,
                "model_counts": model_counts,
            }
        except sqlite3.Error as e:
            logger.warning("Failed to compute stats: %s", e)
            return {"total_requests": 0, "total_tokens": 0, "total_cost_usd": 0.0, "decision_counts": {}, "model_counts": {}}

    def clear(self) -> int:
        """
        Delete all history records.

        Returns:
            Number of records deleted.
        """
        try:
            with self._connect() as conn:
                cursor = conn.execute("DELETE FROM precheck_history")
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            logger.warning("Failed to clear history: %s", e)
            return 0
