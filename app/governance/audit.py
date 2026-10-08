from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.schemas import Finding, GovernanceResult, Request


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


class AuditLogger:
    def __init__(self, db_path: str = "governance_audit.db") -> None:
        self.db_path = db_path
        self._memory_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
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
                        reanalysis_json TEXT
                    )
                    """
                )
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
        timestamp = datetime.now(timezone.utc).isoformat()
        findings_serialized = [asdict(f) for f in result.findings]
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
                        human_action, reanalysis_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        )

    def get_records_by_request_id(self, request_id: str) -> list[AuditRecord]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT record_id, request_id, timestamp, sender, receiver,
                       findings_json, risk_level, decision, human_action, reanalysis_json
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
            )
            for row in rows
        ]

    def get_all_records(self) -> list[AuditRecord]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT record_id, request_id, timestamp, sender, receiver,
                       findings_json, risk_level, decision, human_action, reanalysis_json
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
            )
            for row in rows
        ]


default_audit_logger = AuditLogger()
