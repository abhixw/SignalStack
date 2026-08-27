"""One-time migration: import an existing SQLite dev/demo database into MongoDB.

This script is NOT part of the running application — SQLite/SQLAlchemy are not
runtime dependencies of SignaXAI after this migration. It exists purely so any
demo/dev data that predates the MongoDB migration isn't lost.

Usage (run from backend/):
    venv/bin/python scripts/migrate_sqlite_to_mongodb.py [path/to/sql_app.db]

The path defaults to $SQLITE_DB_PATH, then ./data/sql_app.db.

Idempotent: safe to re-run.
  - users:      matched by unique `email` — existing users are left untouched.
  - outcomes:   matched by preserved string `_id` — existing outcomes are skipped,
                never overwritten (so a rerun can't clobber newer app writes).
  - proofs / evaluations / feedback / audit_logs: matched by a synthetic
    `_migrated_from_sqlite_id` field (`"<table>:<sqlite row id>"`) — rerunning
    skips rows already imported.
  - signal_weights: upserted by (signal_name, task_id), same key the app itself
    uses — reruns just re-set the same weight.

Cross-table references are remapped: SQLite used integer/UUID ids that don't
carry over to Mongo's ObjectIds, so this script builds old-id -> new-id maps
for users and evaluations and rewrites `candidate_user_id` / `evaluation_id`
accordingly. `outcome_id` / `job_id` references need no remapping because
Outcome._id is preserved as the same string in both databases.
"""
import asyncio
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import AsyncMongoClient  # noqa: E402

from app.config.config import config  # noqa: E402


def _parse_dt(value) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return datetime.now(timezone.utc)


def _rows(conn: sqlite3.Connection, table: str):
    try:
        conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
    except sqlite3.OperationalError:
        return []  # table doesn't exist in this (possibly older) SQLite schema
    cur = conn.execute(f"SELECT * FROM {table}")
    return [dict(row) for row in cur.fetchall()]


class Report:
    def __init__(self):
        self.counts = {}

    def add(self, table: str, outcome: str):
        key = (table, outcome)
        self.counts[key] = self.counts.get(key, 0) + 1

    def print(self):
        tables = sorted({t for t, _ in self.counts})
        print("\n=== Migration report ===")
        for t in tables:
            inserted = self.counts.get((t, "inserted"), 0)
            skipped = self.counts.get((t, "skipped"), 0)
            failed = self.counts.get((t, "failed"), 0)
            print(f"{t:16s} inserted={inserted:<5d} skipped={skipped:<5d} failed={failed:<5d}")


async def migrate(sqlite_path: str):
    if not os.path.exists(sqlite_path):
        print(f"No SQLite database found at {sqlite_path} — nothing to migrate.")
        return

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row

    client = AsyncMongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client[config.MONGODB_ACTIVE_DATABASE]
    await client.admin.command("ping")

    report = Report()
    user_id_map: dict = {}       # old SQLite users.id (uuid str) -> new Mongo ObjectId
    evaluation_id_map: dict = {} # old SQLite evaluations.id (int) -> new Mongo ObjectId

    # --- users ---
    for row in _rows(conn, "users"):
        try:
            existing = await db.users.find_one({"email": row["email"]})
            if existing:
                user_id_map[row["id"]] = existing["_id"]
                report.add("users", "skipped")
                continue
            doc = {
                "email": row["email"],
                "hashed_password": row["hashed_password"],
                "role": row["role"],
                "full_name": row.get("full_name"),
                "created_at": _parse_dt(row.get("created_at")),
            }
            result = await db.users.insert_one(doc)
            user_id_map[row["id"]] = result.inserted_id
            report.add("users", "inserted")
        except Exception as e:
            print(f"  [users] failed to migrate row {row.get('id')}: {e}")
            report.add("users", "failed")

    # --- outcomes (id preserved verbatim as the Mongo _id) ---
    for row in _rows(conn, "outcomes"):
        try:
            existing = await db.outcomes.find_one({"_id": row["id"]})
            if existing:
                report.add("outcomes", "skipped")
                continue
            doc = {
                "_id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "tasks": json.loads(row["tasks_json"]) if row.get("tasks_json") else [],
                "rubric": json.loads(row["rubric_json"]) if row.get("rubric_json") else {},
                "owner_id": str(user_id_map.get(row.get("owner_id"), row.get("owner_id"))) if row.get("owner_id") else None,
                "is_public": bool(row.get("is_public", True)),
                "created_at": _parse_dt(row.get("created_at")),
            }
            await db.outcomes.insert_one(doc)
            report.add("outcomes", "inserted")
        except Exception as e:
            print(f"  [outcomes] failed to migrate row {row.get('id')}: {e}")
            report.add("outcomes", "failed")

    # --- evaluations (needs outcome title for the denormalized outcome_title field) ---
    for row in _rows(conn, "evaluations"):
        migration_key = f"evaluations:{row['id']}"
        try:
            existing = await db.evaluations.find_one({"_migrated_from_sqlite_id": migration_key})
            if existing:
                evaluation_id_map[row["id"]] = existing["_id"]
                report.add("evaluations", "skipped")
                continue
            outcome_doc = await db.outcomes.find_one({"_id": row["outcome_id"]}, {"title": 1})
            doc = {
                "job_id": row["job_id"],
                "outcome_id": row["outcome_id"],
                "outcome_title": outcome_doc["title"] if outcome_doc else "",
                "evaluation": json.loads(row["evaluation_json"]) if row.get("evaluation_json") else {},
                "fit_score": row.get("fit_score"),
                "created_at": _parse_dt(row.get("created_at")),
                "_migrated_from_sqlite_id": migration_key,
            }
            result = await db.evaluations.insert_one(doc)
            evaluation_id_map[row["id"]] = result.inserted_id
            report.add("evaluations", "inserted")
        except Exception as e:
            print(f"  [evaluations] failed to migrate row {row.get('id')}: {e}")
            report.add("evaluations", "failed")

    # --- proofs (candidate_user_id remapped through user_id_map) ---
    for row in _rows(conn, "proofs"):
        migration_key = f"proofs:{row['id']}"
        try:
            existing = await db.proofs.find_one({"_migrated_from_sqlite_id": migration_key})
            if existing:
                report.add("proofs", "skipped")
                continue
            old_candidate_user_id = row.get("candidate_user_id")
            new_candidate_user_id = str(user_id_map[old_candidate_user_id]) if old_candidate_user_id in user_id_map else old_candidate_user_id
            doc = {
                "outcome_id": row["outcome_id"],
                "candidate_id": row["candidate_id"],
                "candidate_user_id": new_candidate_user_id,
                "type": row["type"],
                "payload": json.loads(row["payload_json"]) if row.get("payload_json") else {},
                "created_at": _parse_dt(row.get("created_at")),
                "_migrated_from_sqlite_id": migration_key,
            }
            await db.proofs.insert_one(doc)
            report.add("proofs", "inserted")
        except Exception as e:
            print(f"  [proofs] failed to migrate row {row.get('id')}: {e}")
            report.add("proofs", "failed")

    # --- feedback (evaluation_id remapped through evaluation_id_map) ---
    for row in _rows(conn, "feedback"):
        migration_key = f"feedback:{row['id']}"
        try:
            existing = await db.feedback.find_one({"_migrated_from_sqlite_id": migration_key})
            if existing:
                report.add("feedback", "skipped")
                continue
            old_eval_id = row.get("evaluation_id")
            doc = {
                "evaluation_id": evaluation_id_map.get(old_eval_id),
                "job_id": row["job_id"],
                "result": row["result"],
                "metrics": json.loads(row["metrics_json"]) if row.get("metrics_json") else {},
                "created_at": _parse_dt(row.get("created_at")),
                "_migrated_from_sqlite_id": migration_key,
            }
            await db.feedback.insert_one(doc)
            report.add("feedback", "inserted")
        except Exception as e:
            print(f"  [feedback] failed to migrate row {row.get('id')}: {e}")
            report.add("feedback", "failed")

    # --- audit_logs ---
    for row in _rows(conn, "audit_logs"):
        migration_key = f"audit_logs:{row['id']}"
        try:
            existing = await db.audit_logs.find_one({"_migrated_from_sqlite_id": migration_key})
            if existing:
                report.add("audit_logs", "skipped")
                continue
            doc = {
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "action": row["action"],
                "details": json.loads(row["details_json"]) if row.get("details_json") else {},
                "created_at": _parse_dt(row.get("created_at")),
                "_migrated_from_sqlite_id": migration_key,
            }
            await db.audit_logs.insert_one(doc)
            report.add("audit_logs", "inserted")
        except Exception as e:
            print(f"  [audit_logs] failed to migrate row {row.get('id')}: {e}")
            report.add("audit_logs", "failed")

    # --- signal_weights (natural upsert key: signal_name + task_id, same as the app uses) ---
    for row in _rows(conn, "signal_weights"):
        try:
            await db.signal_weights.update_one(
                {"signal_name": row["signal_name"], "task_id": row.get("task_id")},
                {"$setOnInsert": {
                    "signal_name": row["signal_name"],
                    "task_id": row.get("task_id"),
                    "weight": row["weight"],
                    "updated_at": _parse_dt(row.get("updated_at")),
                }},
                upsert=True,
            )
            report.add("signal_weights", "inserted")
        except Exception as e:
            print(f"  [signal_weights] failed to migrate row {row.get('id')}: {e}")
            report.add("signal_weights", "failed")

    conn.close()
    await client.close()
    report.print()


if __name__ == "__main__":
    default_path = os.environ.get("SQLITE_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "sql_app.db"))
    path = sys.argv[1] if len(sys.argv) > 1 else default_path
    print(f"Migrating {os.path.abspath(path)} -> MongoDB database '{config.MONGODB_ACTIVE_DATABASE}' at {config.MONGODB_URI.split('@')[-1]}")
    asyncio.run(migrate(path))
