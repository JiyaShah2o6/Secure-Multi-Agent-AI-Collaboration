from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.schemas import Finding, GovernanceResult, Request
from app.authorization.data_minimization import PURPOSE_FIELDS
from app.governance.confidentiality import classify_field


def safe_fields(fields):
    """Retain schema names, never arbitrary input masquerading as a field name."""
    if not isinstance(fields, (list, tuple)):
        return ["[invalid fields]"]
    return [f.strip().lower() if isinstance(f, str) and classify_field(f) != "UNKNOWN"
            else "[unknown field]" for f in fields]


def safe_findings(findings):
    sanitized = []
    for finding in findings:
        item = dict(finding)
        item["evidence"] = "[redacted]" if item.get("evidence") else ""
        if "UNKNOWN_FIELD" in item.get("labels", []):
            item["labels"] = ["UNKNOWN_FIELD"]
            item["explanation"] = "Requested field is not in the recognized customer schema."
        sanitized.append(item)
    return sanitized


def safe_trajectory(trajectory):
    return [{**step, "findings": safe_findings(step.get("findings", [])),
             "modified_fields": safe_fields(step["modified_fields"])
             if step.get("modified_fields") is not None else None} for step in trajectory]


def safe_agent(value):
    known = {"AgentA", "AgentB", "agent_a", "agent_b", "support_agent", "data_agent"}
    return value if isinstance(value, str) and value in known else "[unrecognized agent]"


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
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS execution_logs (
                        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        request_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        status TEXT NOT NULL,
                        returned_fields_json TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_execution_request_id
                    ON execution_logs(request_id)
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS failure_logs (
                        failure_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        request_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        error_type TEXT NOT NULL,
                        description TEXT NOT NULL,
                        details_json TEXT
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_failures_request_id
                    ON failure_logs(request_id)
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
        findings_serialized = safe_findings([asdict(f) for f in result.findings])
        details = {
            # Retain the structured demo request, never arbitrary purpose text or IDs.
            "original_request": {
                "sender": safe_agent(request.sender),
                "receiver": safe_agent(request.receiver),
                "customer_id": request.customer_id if isinstance(request.customer_id, str) and re.fullmatch(r"C[0-9]{3}", request.customer_id) else "[redacted]",
                "requested_fields": safe_fields(request.requested_fields),
                "purpose": request.purpose if isinstance(request.purpose, str) and request.purpose in PURPOSE_FIELDS else "[custom purpose redacted]",
            },
            "authorization": result.authorization,
            "requested_fields": safe_fields(request.requested_fields),
            "effective_fields": safe_fields((result.modified_request or request).requested_fields),
            "reason": result.reason,
            "mitigation": result.suggested_action,
            "trajectory": safe_trajectory(result.trajectory),
        }
        if human_action:
            details["human_action"] = human_action
        if reanalysis_info is not None:
            reanalysis_info = dict(reanalysis_info)
            if reanalysis_info.get("modified_fields") is not None:
                reanalysis_info["modified_fields"] = safe_fields(reanalysis_info["modified_fields"])
            if "trajectory" in reanalysis_info:
                reanalysis_info["trajectory"] = safe_trajectory(reanalysis_info["trajectory"])
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
                        safe_agent(request.sender),
                        safe_agent(request.receiver),
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
            sender=safe_agent(request.sender),
            receiver=safe_agent(request.receiver),
            findings=findings_serialized,
            risk_level=result.risk_level,
            decision=result.decision,
            human_action=human_action,
            reanalysis_info=reanalysis_info,
            details=details,
        )

    def record_rejection(self, request_id, *, sender=None, receiver=None,
                         customer_id=None, requested_fields=None, purpose=None):
        """Record validation denial without serializing the malformed payload or exception."""
        request = Request(request_id, sender, receiver, customer_id, requested_fields, purpose)
        result = GovernanceResult(request_id, "HIGH", [Finding(
            "validation", "HIGH", ["MALFORMED_REQUEST"], "",
            "Request failed input validation; no data access attempted.", "BLOCK")],
            "BLOCK", "Malformed request rejected before data access.", "BLOCK",
            authorization=False)
        return self.record_audit(request, result)

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
        """Attach retrieval outcome to policy event and append to execution event log."""
        self._init_db()
        timestamp = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            with conn:
                # 1. Append to execution event log
                conn.execute(
                    """
                    INSERT INTO execution_logs (
                        request_id, timestamp, status, returned_fields_json
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (request_id, timestamp, status, json.dumps(safe_fields(returned_fields))),
                )
                # 2. Update latest policy event for backwards compatibility
                row = conn.execute(
                    "SELECT record_id, details_json FROM audit_logs WHERE request_id = ? "
                    "ORDER BY record_id DESC LIMIT 1", (request_id,),
                ).fetchone()
                if row is None:
                    raise ValueError("No policy event for execution")
                details = json.loads(row[1]) if row[1] else {}
                details["execution"] = {"status": status, "returned_fields": safe_fields(returned_fields)}
                conn.execute("UPDATE audit_logs SET details_json = ? WHERE record_id = ?",
                             (json.dumps(details), row[0]))
        finally:
            if self._memory_conn is None:
                conn.close()

    def record_failure(
        self,
        request_id: str,
        error_type: str,
        description: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Append an explicit failure event to failure_logs table."""
        self._init_db()
        timestamp = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO failure_logs (
                        request_id, timestamp, error_type, description, details_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        request_id,
                        timestamp,
                        error_type,
                        description,
                        json.dumps(details or {}),
                    ),
                )
        finally:
            if self._memory_conn is None:
                conn.close()

    def get_execution_logs(self, request_id: str) -> list[dict[str, Any]]:
        self._init_db()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT event_id, request_id, timestamp, status, returned_fields_json
                FROM execution_logs
                WHERE request_id = ?
                ORDER BY event_id ASC
                """,
                (request_id,),
            )
            return [
                {
                    "event_id": row[0],
                    "request_id": row[1],
                    "timestamp": row[2],
                    "status": row[3],
                    "returned_fields": json.loads(row[4]),
                }
                for row in cursor.fetchall()
            ]
        finally:
            if self._memory_conn is None:
                conn.close()

    def get_failure_logs(self, request_id: str) -> list[dict[str, Any]]:
        self._init_db()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT failure_id, request_id, timestamp, error_type, description, details_json
                FROM failure_logs
                WHERE request_id = ?
                ORDER BY failure_id ASC
                """,
                (request_id,),
            )
            return [
                {
                    "failure_id": row[0],
                    "request_id": row[1],
                    "timestamp": row[2],
                    "error_type": row[3],
                    "description": row[4],
                    "details": json.loads(row[5]) if row[5] else {},
                }
                for row in cursor.fetchall()
            ]
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

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


default_audit_logger = AuditLogger()
