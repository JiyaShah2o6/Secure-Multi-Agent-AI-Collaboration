from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.schemas import Finding, GovernanceResult, Request
from app.authorization.data_minimization import PURPOSE_FIELDS


@dataclass
class AuditRecord:
    request_id: str
    timestamp: str
    sender: str
    receiver: str
    findings: list[dict[str, Any]]
    risk_level: str
    decision: str
    human_action: Optional[str] = None
    reanalysis_info: Optional[dict[str, Any]] = None
    record_id: Optional[int] = None
    details: dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    def __init__(self, db_path: str = "governance_audit.db") -> None:
        self.db_path = db_path
        self._memory_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:")
        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        if self._initialized:
            return
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        request_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        sender TEXT NOT NULL,
                        receiver TEXT NOT NULL,
                        findings_json TEXT NOT NULL,
                        risk_level TEXT NOT NULL,
                        decision TEXT NOT NULL,
                        human_action TEXT,
                        reanalysis_json TEXT,
                        details_json TEXT
                    )
                    """
                )
                columns = {row[1] for row in conn.execute("PRAGMA table_info(audit_logs)")}
                if "details_json" not in columns:
                    conn.execute("ALTER TABLE audit_logs ADD COLUMN details_json TEXT")
            self._initialized = True
        finally:
            if self._memory_conn is None:
                conn.close()

    def record_audit(
        self,
        request: Request,
        result: GovernanceResult,
        human_action: Optional[str] = None,
        reanalysis_info: Optional[dict[str, Any]] = None,
    ) -> AuditRecord:
        self._init_db()
        timestamp = datetime.now(timezone.utc).isoformat()
        findings_serialized = [asdict(f) for f in result.findings]
        # Keep labels/explanations, but never persist matched PII or raw payloads.
        for finding in findings_serialized:
            finding["evidence"] = "[redacted]" if finding["evidence"] else ""
        details = {
            # Retain the structured demo request, never arbitrary purpose text or IDs.
            "original_request": {
                "sender": request.sender,
                "receiver": request.receiver,
                "customer_id": request.customer_id if re.fullmatch(r"C[0-9]{3}", request.customer_id) else "[redacted]",
                "requested_fields": request.requested_fields,
                "purpose": request.purpose if request.purpose in PURPOSE_FIELDS else "[custom purpose redacted]",
            },
            "authorization": result.authorization,
            "requested_fields": request.requested_fields,
            "effective_fields": (result.modified_request or request).requested_fields,
            "reason": result.reason,
            "mitigation": result.suggested_action,
            "trajectory": result.trajectory,
        }
        findings_json = json.dumps(findings_serialized)
        reanalysis_json = (
            json.dumps(reanalysis_info) if reanalysis_info is not None else None
        )

        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO audit_logs (
                        request_id, timestamp, sender, receiver,
                        findings_json, risk_level, decision,
                        human_action, reanalysis_json, details_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request.request_id,
                        timestamp,
                        request.sender,
                        request.receiver,
                        findings_json,
                        result.risk_level,
                        result.decision,
                        human_action,
                        reanalysis_json,
                        json.dumps(details),
                    ),
                )
                record_id = cursor.lastrowid
        finally:
            if self._memory_conn is None:
                conn.close()

        return AuditRecord(
            record_id=record_id,
            request_id=request.request_id,
            timestamp=timestamp,
            sender=request.sender,
            receiver=request.receiver,
            findings=findings_serialized,
            risk_level=result.risk_level,
            decision=result.decision,
            human_action=human_action,
            reanalysis_info=reanalysis_info,
            details=details,
        )

    def get_records_by_request_id(self, request_id: str) -> list[AuditRecord]:
        self._init_db()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT record_id, request_id, timestamp, sender, receiver,
                       findings_json, risk_level, decision, human_action, reanalysis_json, details_json
                FROM audit_logs
                WHERE request_id = ?
                ORDER BY record_id ASC
                """,
                (request_id,),
            )
            rows = cursor.fetchall()
        finally:
            if self._memory_conn is None:
                conn.close()

        return [
            AuditRecord(
                record_id=row[0],
                request_id=row[1],
                timestamp=row[2],
                sender=row[3],
                receiver=row[4],
                findings=json.loads(row[5]),
                risk_level=row[6],
                decision=row[7],
                human_action=row[8],
                reanalysis_info=json.loads(row[9]) if row[9] else None,
                details=json.loads(row[10]) if row[10] else {},
            )
            for row in rows
        ]

    def get_all_records(self) -> list[AuditRecord]:
        self._init_db()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT record_id, request_id, timestamp, sender, receiver,
                       findings_json, risk_level, decision, human_action, reanalysis_json, details_json
                FROM audit_logs
                ORDER BY record_id ASC
                """
            )
            rows = cursor.fetchall()
        finally:
            if self._memory_conn is None:
                conn.close()

        return [
            AuditRecord(
                record_id=row[0],
                request_id=row[1],
                timestamp=row[2],
                sender=row[3],
                receiver=row[4],
                findings=json.loads(row[5]),
                risk_level=row[6],
                decision=row[7],
                human_action=row[8],
                reanalysis_info=json.loads(row[9]) if row[9] else None,
                details=json.loads(row[10]) if row[10] else {},
            )
            for row in rows
        ]


    def record_execution(self, request_id: str, status: str, returned_fields: list[str]) -> None:
        """Attach retrieval outcome to the latest policy event, without storing values."""
        self._init_db()
        conn = self._get_connection()
        try:
            with conn:
                row = conn.execute(
                    "SELECT record_id, details_json FROM audit_logs WHERE request_id = ? "
                    "ORDER BY record_id DESC LIMIT 1", (request_id,),
                ).fetchone()
                if row is None:
                    raise ValueError("No policy event for execution")
                details = json.loads(row[1]) if row[1] else {}
                details["execution"] = {"status": status, "returned_fields": returned_fields}
                conn.execute("UPDATE audit_logs SET details_json = ? WHERE record_id = ?",
                             (json.dumps(details), row[0]))
        finally:
            if self._memory_conn is None:
                conn.close()

    def close(self) -> None:
        if self._memory_conn is not None:
            self._memory_conn.close()


default_audit_logger = AuditLogger()
