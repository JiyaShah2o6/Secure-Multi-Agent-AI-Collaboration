from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Final, Optional

CUSTOMER_COLUMN_MAP: Final[dict[str, str]] = {
    "customer_id": "customer_id",
    "name": "name",
    "email": "email",
    "phone": "phone",
    "address": "address",
}

COMPLAINT_COLUMN_MAP: Final[dict[str, str]] = {
    "complaint_id": "complaint_id",
    "complaint_status": "complaint_status",
    "complaint_description": "complaint_description",
}

FINANCIAL_COLUMN_MAP: Final[dict[str, str]] = {
    "bank_account": "masked_bank_account",
    "card_details": "masked_card_details",
}

# Reverse mapping for projection
_FINANCIAL_REVERSE_MAP: Final[dict[str, str]] = {
    v: k for k, v in FINANCIAL_COLUMN_MAP.items()
}

ALL_SUPPORTED_FIELDS: Final[frozenset[str]] = (
    frozenset(CUSTOMER_COLUMN_MAP.keys())
    | frozenset(COMPLAINT_COLUMN_MAP.keys())
    | frozenset(FINANCIAL_COLUMN_MAP.keys())
)


class CustomerRepository:
    """
    Repository abstraction for persistent synthetic customer data.
    Provides parameterized SQL queries, explicit column allowlists,
    and minimal field projections.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is not None:
            self.db_path = db_path
        else:
            env_path = os.environ.get("CUSTOMER_DB_PATH")
            if env_path:
                self.db_path = env_path
            else:
                default_dir = Path(__file__).resolve().parents[2] / ".runtime"
                default_dir.mkdir(parents=True, exist_ok=True)
                self.db_path = str(default_dir / "customers.db")

        self._memory_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:")
            self._memory_conn.execute("PRAGMA foreign_keys = ON;")

        self._initialized = False
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        if self._initialized:
            return
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS customers (
                        customer_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        address TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS complaints (
                        complaint_id TEXT PRIMARY KEY,
                        customer_id TEXT NOT NULL,
                        complaint_status TEXT NOT NULL,
                        complaint_description TEXT NOT NULL,
                        FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_complaints_customer_id
                    ON complaints(customer_id)
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS financial_records (
                        financial_record_id TEXT PRIMARY KEY,
                        customer_id TEXT NOT NULL,
                        masked_bank_account TEXT NOT NULL,
                        masked_card_details TEXT NOT NULL,
                        FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_financial_customer_id
                    ON financial_records(customer_id)
                    """
                )
            self._initialized = True
        finally:
            if self._memory_conn is None:
                conn.close()

    def customer_exists(self, customer_id: str) -> bool:
        """Validate if a customer exists using parameterized SQL."""
        if not isinstance(customer_id, str) or not customer_id.strip():
            return False
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM customers WHERE customer_id = ? LIMIT 1",
                (customer_id.strip(),),
            )
            return cursor.fetchone() is not None
        finally:
            if self._memory_conn is None:
                conn.close()

    def get_customer_fields(
        self, customer_id: str, fields: list[str]
    ) -> dict[str, Any]:
        """Retrieve permitted customer table fields using strict column allowlist."""
        valid_cols = [
            CUSTOMER_COLUMN_MAP[f]
            for f in fields
            if f in CUSTOMER_COLUMN_MAP
        ]
        if not valid_cols:
            return {}

        # Allowlist ensures no arbitrary SQL identifier interpolation
        col_sql = ", ".join(valid_cols)
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {col_sql} FROM customers WHERE customer_id = ? LIMIT 1",
                (customer_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return {}
            return {valid_cols[i]: row[i] for i in range(len(valid_cols))}
        finally:
            if self._memory_conn is None:
                conn.close()

    def get_complaint_fields(
        self, customer_id: str, fields: list[str]
    ) -> dict[str, Any]:
        """Retrieve permitted complaint table fields using strict column allowlist."""
        valid_cols = [
            COMPLAINT_COLUMN_MAP[f]
            for f in fields
            if f in COMPLAINT_COLUMN_MAP
        ]
        if not valid_cols:
            return {}

        col_sql = ", ".join(valid_cols)
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {col_sql} FROM complaints WHERE customer_id = ? LIMIT 1",
                (customer_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return {}
            return {valid_cols[i]: row[i] for i in range(len(valid_cols))}
        finally:
            if self._memory_conn is None:
                conn.close()

    def get_financial_fields(
        self, customer_id: str, fields: list[str]
    ) -> dict[str, Any]:
        """Retrieve financial fixtures using strict column allowlist."""
        valid_cols = [
            FINANCIAL_COLUMN_MAP[f]
            for f in fields
            if f in FINANCIAL_COLUMN_MAP
        ]
        if not valid_cols:
            return {}

        col_sql = ", ".join(valid_cols)
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {col_sql} FROM financial_records WHERE customer_id = ? LIMIT 1",
                (customer_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return {}
            result = {}
            for i, col in enumerate(valid_cols):
                field_name = _FINANCIAL_REVERSE_MAP.get(col, col)
                result[field_name] = row[i]
            return result
        finally:
            if self._memory_conn is None:
                conn.close()

    def get_record(
        self, customer_id: str, requested_fields: list[str]
    ) -> Optional[dict[str, Any]]:
        """
        Query and return a minimal structured result containing only the requested fields.
        Applies a double projection check.
        """
        if not self.customer_exists(customer_id):
            return None

        combined: dict[str, Any] = {}

        # 1. Customer table fields (only if requested)
        cust_needed = [f for f in requested_fields if f in CUSTOMER_COLUMN_MAP]
        if cust_needed:
            combined.update(self.get_customer_fields(customer_id, cust_needed))

        # 2. Complaint table fields (only if requested)
        comp_needed = [f for f in requested_fields if f in COMPLAINT_COLUMN_MAP]
        if comp_needed:
            combined.update(self.get_complaint_fields(customer_id, comp_needed))

        # 3. Financial records (only if explicitly requested)
        fin_needed = [f for f in requested_fields if f in FINANCIAL_COLUMN_MAP]
        if fin_needed:
            combined.update(self.get_financial_fields(customer_id, fin_needed))

        # Always include customer_id if specifically requested
        if "customer_id" in requested_fields:
            combined["customer_id"] = customer_id

        # Enforce strict secondary projection: never return fields outside requested_fields
        return {k: v for k, v in combined.items() if k in requested_fields}

    def insert_customer(
        self,
        customer_id: str,
        name: str,
        email: str,
        phone: str,
        address: str,
    ) -> None:
        """Insert or replace a customer record using parameterized SQL."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO customers (
                        customer_id, name, email, phone, address
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (customer_id, name, email, phone, address),
                )
        finally:
            if self._memory_conn is None:
                conn.close()

    def insert_complaint(
        self,
        complaint_id: str,
        customer_id: str,
        status: str,
        description: str,
    ) -> None:
        """Insert or replace a complaint record with foreign-key constraint."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO complaints (
                        complaint_id, customer_id, complaint_status, complaint_description
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (complaint_id, customer_id, status, description),
                )
        finally:
            if self._memory_conn is None:
                conn.close()

    def insert_financial_record(
        self,
        financial_record_id: str,
        customer_id: str,
        masked_bank: str,
        masked_card: str,
    ) -> None:
        """Insert or replace a masked financial fixture with foreign-key constraint."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO financial_records (
                        financial_record_id, customer_id, masked_bank_account, masked_card_details
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (financial_record_id, customer_id, masked_bank, masked_card),
                )
        finally:
            if self._memory_conn is None:
                conn.close()

    def get_customer_count(self) -> int:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM customers")
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            if self._memory_conn is None:
                conn.close()

    def get_complaint_count(self) -> int:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM complaints")
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            if self._memory_conn is None:
                conn.close()

    def get_financial_count(self) -> int:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM financial_records")
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            if self._memory_conn is None:
                conn.close()

    def get_all_customer_ids(self) -> list[str]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT customer_id FROM customers ORDER BY customer_id ASC")
            return [row[0] for row in cursor.fetchall()]
        finally:
            if self._memory_conn is None:
                conn.close()

    def clear_all(self) -> None:
        """Clear all records within a transaction (cascading deletes)."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute("DELETE FROM customers")
        finally:
            if self._memory_conn is None:
                conn.close()

    def close(self) -> None:
        if self._memory_conn is not None:
            try:
                self._memory_conn.close()
            except Exception:
                pass
            self._memory_conn = None

    def __enter__(self) -> CustomerRepository:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


_default_repo: Optional[CustomerRepository] = None


def get_default_customer_repository() -> CustomerRepository:
    """Singleton getter for customer repository, ensuring auto-initialization."""
    global _default_repo
    if _default_repo is None:
        _default_repo = CustomerRepository()
        # If fresh database with 0 customers, automatically seed it
        if _default_repo.get_customer_count() == 0:
            from app.data.seed import seed_customer_database
            seed_customer_database(_default_repo)
    return _default_repo
