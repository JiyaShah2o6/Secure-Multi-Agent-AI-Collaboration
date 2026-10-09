from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.agents.communication import AgentCommunication
from app.agents.data_agent import DataAgent
from app.agents.support_agent import SupportAgent
from app.data.customer_repository import (
    CustomerRepository,
    get_default_customer_repository,
)
from app.data.seed import generate_synthetic_customers, seed_customer_database
from app.governance.audit import AuditLogger
from app.models.schemas import AgentRequest, Request


class TestPhase2Database(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for disposable test database
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        self.repo = CustomerRepository(db_path=self.temp_db_path)
        seed_customer_database(self.repo, reset=True)

        self.temp_audit_fd, self.temp_audit_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_audit_fd)
        self.audit_logger = AuditLogger(db_path=self.temp_audit_path)

        self.transport = AgentCommunication(
            audit_logger=self.audit_logger,
            customer_repository=self.repo,
        )
        self.agent = SupportAgent(self.transport)

    def tearDown(self):
        self.repo.close()
        self.audit_logger.close()
        for path in (self.temp_db_path, self.temp_audit_path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass

    # 1. Deterministic seed creation
    def test_deterministic_seed_creation(self):
        records1 = generate_synthetic_customers(100)
        records2 = generate_synthetic_customers(100)
        self.assertEqual(len(records1), 100)
        self.assertEqual(len(records2), 100)
        # Verify strict reproducibility across invocations
        self.assertEqual(records1, records2)
        # Verify baseline customers exist and are unmodified
        self.assertEqual(records1[0]["customer_id"], "C101")
        self.assertEqual(records1[0]["name"], "Rahul Sharma")
        self.assertEqual(records1[1]["customer_id"], "C102")
        self.assertEqual(records1[2]["customer_id"], "C103")
        # Verify generated counts in database
        self.assertEqual(self.repo.get_customer_count(), 100)
        self.assertEqual(self.repo.get_complaint_count(), 100)
        self.assertEqual(self.repo.get_financial_count(), 100)

    # 2. Repeat-safe seeding
    def test_repeat_safe_seeding(self):
        # Seeding second time without reset must not duplicate rows
        custs, comps, fins = seed_customer_database(self.repo, reset=False)
        self.assertEqual(custs, 100)
        self.assertEqual(comps, 100)
        self.assertEqual(fins, 100)
        self.assertEqual(self.repo.get_customer_count(), 100)
        self.assertEqual(self.repo.get_complaint_count(), 100)
        self.assertEqual(self.repo.get_financial_count(), 100)

        # Seeding with reset must clear and recreate cleanly
        custs, comps, fins = seed_customer_database(self.repo, reset=True)
        self.assertEqual(custs, 100)
        self.assertEqual(self.repo.get_customer_count(), 100)

    # 3. Correct relationships between customer and complaint records
    def test_correct_relationships_and_foreign_keys(self):
        conn = self.repo._get_connection()
        try:
            # Foreign-key enforcement must reject inserting a complaint for a non-existent customer
            with self.assertRaises(sqlite3.IntegrityError):
                with conn:
                    conn.execute("PRAGMA foreign_keys = ON;")
                    conn.execute(
                        "INSERT INTO complaints (complaint_id, customer_id, complaint_status, complaint_description) "
                        "VALUES (?, ?, ?, ?)",
                        ("CMP9999", "C9999_NONEXISTENT", "Pending", "Invalid customer"),
                    )

            # Cascade delete verification
            with conn:
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute("DELETE FROM customers WHERE customer_id = ?", ("C101",))
            # Complaints and financial records for C101 must be cascaded
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM complaints WHERE customer_id = 'C101'")
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute("SELECT COUNT(*) FROM financial_records WHERE customer_id = 'C101'")
            self.assertEqual(cursor.fetchone()[0], 0)
        finally:
            if self.repo._memory_conn is None:
                conn.close()

    # 4. Permitted field projection
    def test_permitted_field_projection(self):
        # Retrieve only complaint_status
        record = self.repo.get_record("C102", ["complaint_status"])
        self.assertIsNotNone(record)
        self.assertEqual(record, {"complaint_status": "Resolved"})
        # Name and address must NOT be fetched or included
        self.assertNotIn("name", record)
        self.assertNotIn("address", record)

        # Retrieve specific multi-table fields
        record = self.repo.get_record("C102", ["name", "email", "complaint_status"])
        self.assertEqual(
            record,
            {
                "name": "Priya Patel",
                "email": "priya@example.com",
                "complaint_status": "Resolved",
            },
        )
        self.assertNotIn("phone", record)
        self.assertNotIn("address", record)

    # 5. Restricted field retrieval denial
    def test_restricted_field_retrieval_denial(self):
        # Normal complaint request through AgentCommunication must block financial fields
        response = self.agent.request_customer_data(
            "C101", ["bank_account", "card_details"], "Resolve customer complaint"
        )
        self.assertEqual(response.status, "unauthorized")
        self.assertEqual(response.data, {})
        gov = response.metadata["governance"]
        self.assertEqual(gov["decision"], "BLOCK")

    # 6. SQL injection-like input
    def test_sql_injection_input(self):
        # SQL injection in customer_id
        sqli_customer = "C101' OR '1'='1"
        self.assertFalse(self.repo.customer_exists(sqli_customer))
        self.assertIsNone(self.repo.get_record(sqli_customer, ["complaint_status"]))

        # SQL injection attempt in field list
        malicious_fields = [
            "name",
            "complaint_status; DROP TABLE customers; --",
            "' UNION SELECT * FROM financial_records --",
        ]
        # Allowlist must filter out any non-allowlisted column expressions
        record = self.repo.get_record("C101", malicious_fields)
        self.assertIsNotNone(record)
        self.assertEqual(list(record.keys()), ["name"])
        # Verify customers table was not dropped
        self.assertTrue(self.repo.customer_exists("C101"))
        self.assertEqual(self.repo.get_customer_count(), 100)

    # 7. Invalid/unknown field names
    def test_invalid_unknown_field_names(self):
        unknown_fields = ["ssn", "non_existent_column", "secret_pass"]
        record = self.repo.get_record("C101", unknown_fields)
        self.assertIsNotNone(record)
        self.assertEqual(record, {})

    # 8. Missing customers
    def test_missing_customers(self):
        self.assertFalse(self.repo.customer_exists("C999"))
        self.assertIsNone(self.repo.get_record("C999", ["name"]))

        response = self.agent.request_customer_data(
            "C999", ["complaint_status"], "Resolve customer complaint"
        )
        self.assertEqual(response.status, "error")
        self.assertEqual(response.data, {})

    # 9. Transaction rollback
    def test_transaction_rollback(self):
        conn = self.repo._get_connection()
        try:
            initial_count = self.repo.get_customer_count()
            # Deliberately fail inside a transaction block
            with self.assertRaises(sqlite3.IntegrityError):
                with conn:
                    conn.execute("PRAGMA foreign_keys = ON;")
                    # Insert valid customer
                    conn.execute(
                        "INSERT INTO customers (customer_id, name, email, phone, address) "
                        "VALUES ('C999', 'Temp Test', 't@e.com', '123', 'City')"
                    )
                    # Trigger foreign key failure
                    conn.execute(
                        "INSERT INTO complaints (complaint_id, customer_id, complaint_status, complaint_description) "
                        "VALUES ('CMP_FAIL', 'NON_EXISTENT_FK', 'Open', 'Desc')"
                    )

            # Customer insert must be rolled back
            self.assertEqual(self.repo.get_customer_count(), initial_count)
            self.assertFalse(self.repo.customer_exists("C999"))
        finally:
            if self.repo._memory_conn is None:
                conn.close()

    # 10. Audit persistence across reconnect/restart
    def test_audit_persistence_across_reconnect(self):
        req_id = "req-persist-test-1"
        req = Request(req_id, "AgentA", "AgentB", "C101", ["complaint_status"], "Resolve customer complaint")
        from app.governance.reanalysis import govern_request
        gov_res = govern_request(req, enforce_policy=True, audit_logger=self.audit_logger)

        self.audit_logger.record_execution(req_id, "success", ["complaint_status"])
        self.audit_logger.record_failure(req_id, "test_error", "Simulated failure for persistence check")
        self.audit_logger.close()

        # Reopen audit logger with the same database file
        reopened = AuditLogger(db_path=self.temp_audit_path)
        try:
            records = reopened.get_records_by_request_id(req_id)
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record.request_id, req_id)
            self.assertEqual(record.decision, "ALLOW")
            self.assertEqual(record.details["execution"]["status"], "success")

            exec_logs = reopened.get_execution_logs(req_id)
            self.assertEqual(len(exec_logs), 1)
            self.assertEqual(exec_logs[0]["status"], "success")
            self.assertEqual(exec_logs[0]["returned_fields"], ["complaint_status"])

            fail_logs = reopened.get_failure_logs(req_id)
            self.assertEqual(len(fail_logs), 1)
            self.assertEqual(fail_logs[0]["error_type"], "test_error")
        finally:
            reopened.close()

    # 11. Audit record redaction
    def test_audit_record_redaction(self):
        response = self.agent.request_customer_data(
            "C101", ["complaint_status"], "Arbitrary unapproved custom purpose statement"
        )
        gov = response.metadata["governance"]
        req_id = response.metadata["request_id"]
        records = self.audit_logger.get_records_by_request_id(req_id)
        self.assertTrue(len(records) > 0)
        rec = records[0]
        # Custom purpose must be redacted in audit storage
        self.assertEqual(rec.details["original_request"]["purpose"], "[custom purpose redacted]")

    # 12. Failed audit operation behaviour
    def test_failed_audit_operation_behaviour(self):
        # If record_execution fails, AgentCommunication must fail closed
        with patch.object(self.audit_logger, "record_execution", side_effect=sqlite3.OperationalError("disk I/O error")):
            response = self.agent.request_customer_data(
                "C101", ["complaint_status"], "Resolve customer complaint"
            )
            self.assertEqual(response.status, "error")
            self.assertEqual(response.data, {})
            self.assertIn("Execution audit failed", response.message)

    # 13. Approval enforcement continues to function with database repository
    def test_approval_enforcement_with_database(self):
        # Legitimate request succeeds through database repository
        response = self.agent.request_customer_data(
            "C101", ["complaint_status"], "Resolve customer complaint"
        )
        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, {"complaint_status": "In Progress"})

        # Tampered ticket or direct data agent call without ticket is blocked
        data_agent = self.transport.data_agent
        direct_resp = data_agent.handle_request("forged_ticket", customer_id="C101", requested_fields=["complaint_status"])
        self.assertEqual(direct_resp.status, "blocked")
        self.assertEqual(direct_resp.data, {})


if __name__ == "__main__":
    unittest.main()
