import json
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
DATABASE_PATH = Path(os.getenv('DATABASE_PATH', 'data/refund_cases.db'))


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DATABASE_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    with get_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS refund_cases (
            thread_id TEXT PRIMARY KEY,
            image_path TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            approval_status TEXT NOT NULL DEFAULT 'not_requested',
            escalation_tier INTEGER,
            escalation_reason TEXT,
            state_json TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        existing = {row['name'] for row in conn.execute('PRAGMA table_info(refund_cases)').fetchall()}
        migrations = {
            'state_json': "ALTER TABLE refund_cases ADD COLUMN state_json TEXT NOT NULL DEFAULT '{}'",
            'updated_at': 'ALTER TABLE refund_cases ADD COLUMN updated_at TIMESTAMP',
        }
        for name, sql in migrations.items():
            if name not in existing:
                conn.execute(sql)


def create_case(case: dict):
    with get_connection() as conn:
        conn.execute('''INSERT INTO refund_cases (thread_id,image_path,category,status,approval_status,state_json)
                        VALUES (?,?,?,?,?,?)''', (
            case['thread_id'], case['image_path'], case['category'], case.get('status', 'pending'),
            case.get('approval_status', 'not_requested'), json.dumps(case.get('state', {}), ensure_ascii=False, default=str)))


def get_case(thread_id: str):
    with get_connection() as conn:
        row = conn.execute('SELECT * FROM refund_cases WHERE thread_id=?', (thread_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        try:
            result['state'] = json.loads(result.pop('state_json', '{}') or '{}')
        except json.JSONDecodeError:
            result['state'] = {}
        return result


def update_case(thread_id: str, updates: dict):
    allowed = {'status', 'approval_status', 'escalation_tier', 'escalation_reason', 'state'}
    updates = {k: v for k, v in updates.items() if k in allowed}
    if not updates:
        return False
    if 'state' in updates:
        updates['state_json'] = json.dumps(updates.pop('state'), ensure_ascii=False, default=str)
    fields = ', '.join(f'{key}=?' for key in updates)
    with get_connection() as conn:
        cur = conn.execute(f'UPDATE refund_cases SET {fields}, updated_at=CURRENT_TIMESTAMP WHERE thread_id=?', (*updates.values(), thread_id))
        return cur.rowcount > 0


def get_escalated_cases():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM refund_cases WHERE status='escalated' ORDER BY created_at DESC").fetchall()
        return [_row_to_dict(row) for row in rows]


def _row_to_dict(row):
    result = dict(row)
    try:
        result['state'] = json.loads(result.pop('state_json', '{}') or '{}')
    except json.JSONDecodeError:
        result['state'] = {}
    return result


def get_all_cases():
    with get_connection() as conn:
        return [_row_to_dict(row) for row in conn.execute('SELECT * FROM refund_cases ORDER BY created_at DESC').fetchall()]
