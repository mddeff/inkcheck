import os
import sqlite3

DATABASE_PATH = os.environ.get(
    "DATABASE_PATH", os.path.join(os.path.dirname(__file__), "instance", "checkprint.db")
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('check','deposit')),
    date TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    description TEXT NOT NULL,
    check_number TEXT,
    memo TEXT,
    voided INTEGER NOT NULL DEFAULT 0,
    printed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

UNIQUE_CHECK_NUMBER_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_check_number
    ON transactions(check_number) WHERE type = 'check' AND check_number IS NOT NULL;
"""


class DuplicateCheckNumberError(Exception):
    pass

BALANCE_SUBQUERY = """
SELECT t.*,
    SUM(CASE WHEN t.voided = 0 THEN
        (CASE WHEN t.type = 'deposit' THEN t.amount_cents ELSE -t.amount_cents END)
    ELSE 0 END) OVER (ORDER BY t.date, t.id ROWS UNBOUNDED PRECEDING) AS running_balance_cents
FROM transactions t
"""


def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    try:
        conn.executescript(UNIQUE_CHECK_NUMBER_INDEX)
    except sqlite3.IntegrityError:
        conn.close()
        raise RuntimeError(
            "Cannot start: duplicate check_number values already exist in "
            f"{DATABASE_PATH}, so check-number uniqueness can't be enforced. Find "
            "them with `SELECT check_number, COUNT(*) FROM transactions WHERE "
            "type='check' GROUP BY check_number HAVING COUNT(*) > 1;` and fix or "
            "remove the duplicates, then restart."
        )
    conn.commit()
    conn.close()


def _escape_like(value):
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_transactions(filters=None):
    """Transactions (including voided) matching filters, with a running balance
    computed over the full unfiltered history so filtering never distorts it."""
    filters = filters or {}
    clauses = []
    params = []

    if filters.get("date_from"):
        clauses.append("date >= ?")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("date <= ?")
        params.append(filters["date_to"])
    if filters.get("type") in ("check", "deposit"):
        clauses.append("type = ?")
        params.append(filters["type"])
    if filters.get("check_from"):
        try:
            clauses.append("CAST(check_number AS INTEGER) >= ?")
            params.append(int(filters["check_from"]))
        except ValueError:
            pass
    if filters.get("check_to"):
        try:
            clauses.append("CAST(check_number AS INTEGER) <= ?")
            params.append(int(filters["check_to"]))
        except ValueError:
            pass
    if filters.get("q"):
        clauses.append("(description LIKE ? ESCAPE '\\' OR memo LIKE ? ESCAPE '\\')")
        like = f"%{_escape_like(filters['q'])}%"
        params.extend([like, like])

    query = f"SELECT * FROM ({BALANCE_SUBQUERY})"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY date, id"

    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_current_balance_cents():
    """The true current balance, as of the latest transaction, independent of any filter."""
    conn = get_connection()
    row = conn.execute(
        f"SELECT running_balance_cents FROM ({BALANCE_SUBQUERY}) ORDER BY date DESC, id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row["running_balance_cents"] if row else 0


def get_transaction(txn_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    conn.close()
    return row


def insert_check(date, amount_cents, description, check_number, memo):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO transactions (type, date, amount_cents, description, check_number, memo)
               VALUES ('check', ?, ?, ?, ?, ?)""",
            (date, amount_cents, description, check_number, memo),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise DuplicateCheckNumberError(f"Check number {check_number} is already in use")
    finally:
        conn.close()


def insert_deposit(date, amount_cents, description):
    conn = get_connection()
    conn.execute(
        """INSERT INTO transactions (type, date, amount_cents, description)
           VALUES ('deposit', ?, ?, ?)""",
        (date, amount_cents, description),
    )
    conn.commit()
    conn.close()


def toggle_void(txn_id):
    conn = get_connection()
    conn.execute("UPDATE transactions SET voided = 1 - voided WHERE id = ?", (txn_id,))
    conn.commit()
    conn.close()


def mark_printed(txn_id):
    conn = get_connection()
    conn.execute(
        "UPDATE transactions SET printed_at = datetime('now') WHERE id = ?", (txn_id,)
    )
    conn.commit()
    conn.close()


def get_next_check_number():
    conn = get_connection()
    row = conn.execute(
        """SELECT MAX(CAST(check_number AS INTEGER)) AS max_num
           FROM transactions WHERE type = 'check' AND check_number IS NOT NULL"""
    ).fetchone()
    conn.close()
    max_num = row["max_num"]
    return str(max_num + 1) if max_num is not None else "1"
