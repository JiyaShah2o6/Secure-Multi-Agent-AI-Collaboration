from __future__ import annotations

import argparse
import random
import sys
from typing import Any, Final

from app.data.customer_repository import CustomerRepository

# Baseline fixtures preserved for exact compatibility
BASELINE_CUSTOMERS: Final[list[dict[str, Any]]] = [
    {
        "customer_id": "C101",
        "name": "Rahul Sharma",
        "email": "rahul@example.com",
        "phone": "9876543210",
        "complaint_id": "CMP101",
        "complaint_status": "In Progress",
        "complaint_description": "Product replacement requested",
        "address": "Vadodara",
        "bank_account": "XXXX-XXXX-1234",
        "card_details": "XXXX-XXXX-5678",
    },
    {
        "customer_id": "C102",
        "name": "Priya Patel",
        "email": "priya@example.com",
        "phone": "9123456780",
        "complaint_id": "CMP102",
        "complaint_status": "Resolved",
        "complaint_description": "Refund requested",
        "address": "Ahmedabad",
        "bank_account": "XXXX-XXXX-5678",
        "card_details": "XXXX-XXXX-1234",
    },
    {
        "customer_id": "C103",
        "name": "Aman Mehta",
        "email": "aman@example.com",
        "phone": "9988776655",
        "complaint_id": "CMP103",
        "complaint_status": "Pending",
        "complaint_description": "Delivery issue reported",
        "address": "Surat",
        "bank_account": "XXXX-XXXX-9012",
        "card_details": "XXXX-XXXX-7890",
    },
]

_FIRST_NAMES: Final[list[str]] = [
    "Aarav", "Aditi", "Ananya", "Arjun", "Deepak", "Divya", "Ishaan",
    "Kavita", "Manish", "Neha", "Pooja", "Rajesh", "Ritu", "Rohan",
    "Sanjay", "Sneha", "Suresh", "Tanvi", "Varun", "Vikram",
]

_LAST_NAMES: Final[list[str]] = [
    "Deshmukh", "Gupta", "Iyer", "Joshi", "Kapoor", "Kulkarni",
    "Malhotra", "Nair", "Pandey", "Rao", "Reddy", "Shah", "Singh",
    "Verma", "Yadav",
]

_CITIES: Final[list[str]] = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Kolkata",
    "Pune", "Ahmedabad", "Jaipur", "Surat", "Lucknow", "Chandigarh",
    "Indore", "Bhopal", "Vadodara", "Nagpur", "Coimbatore", "Visakhapatnam",
]

_COMPLAINT_STATUSES: Final[list[str]] = [
    "Pending", "In Progress", "Resolved", "Escalated",
]

_COMPLAINT_DESCRIPTIONS: Final[list[str]] = [
    "Product replacement requested",
    "Refund requested",
    "Delivery issue reported",
    "Billing discrepancy observed",
    "Account access issue",
    "Service delay complaint",
    "Warranty claim filed",
    "Damaged packaging received",
]


def generate_synthetic_customers(total: int = 100) -> list[dict[str, Any]]:
    """
    Deterministically generate exactly `total` synthetic customer records.
    The first 3 records are the baseline fixtures (C101, C102, C103).
    Remaining records (C104-C200) are generated reproducibly with fixed random seed.
    """
    records = list(BASELINE_CUSTOMERS)
    if total <= len(records):
        return records[:total]

    rng = random.Random(42)

    for i in range(104, 101 + total):
        first = rng.choice(_FIRST_NAMES)
        last = rng.choice(_LAST_NAMES)
        city = rng.choice(_CITIES)
        status = rng.choice(_COMPLAINT_STATUSES)
        desc = rng.choice(_COMPLAINT_DESCRIPTIONS)
        phone = f"98{rng.randint(10000000, 99999999)}"
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        bank = f"XXXX-XXXX-{rng.randint(1000, 9999)}"
        card = f"XXXX-XXXX-{rng.randint(1000, 9999)}"

        records.append({
            "customer_id": f"C{i}",
            "name": f"{first} {last}",
            "email": email,
            "phone": phone,
            "complaint_id": f"CMP{i}",
            "complaint_status": status,
            "complaint_description": desc,
            "address": city,
            "bank_account": bank,
            "card_details": card,
        })

    return records


def seed_customer_database(
    repo: CustomerRepository, reset: bool = False
) -> tuple[int, int, int]:
    """
    Seed customer database with deterministic synthetic data.
    Repeat-safe (idempotent): will not create duplicate rows on subsequent runs.
    Returns (customer_count, complaint_count, financial_count).
    """
    if reset:
        repo.clear_all()

    synthetic_records = generate_synthetic_customers(100)

    for record in synthetic_records:
        cid = record["customer_id"]
        cmp_id = record["complaint_id"]
        fin_id = f"FIN{cid[1:]}"

        # 1. Customer table
        repo.insert_customer(
            customer_id=cid,
            name=record["name"],
            email=record["email"],
            phone=record["phone"],
            address=record["address"],
        )

        # 2. Complaint table
        repo.insert_complaint(
            complaint_id=cmp_id,
            customer_id=cid,
            status=record["complaint_status"],
            description=record["complaint_description"],
        )

        # 3. Financial records table
        repo.insert_financial_record(
            financial_record_id=fin_id,
            customer_id=cid,
            masked_bank=record["bank_account"],
            masked_card=record["card_details"],
        )

    cust_count = repo.get_customer_count()
    comp_count = repo.get_complaint_count()
    fin_count = repo.get_financial_count()

    if cust_count != len(synthetic_records):
        raise RuntimeError(
            f"Seeding verification failed: expected {len(synthetic_records)} customers, found {cust_count}"
        )
    if comp_count != len(synthetic_records):
        raise RuntimeError(
            f"Seeding verification failed: expected {len(synthetic_records)} complaints, found {comp_count}"
        )
    if fin_count != len(synthetic_records):
        raise RuntimeError(
            f"Seeding verification failed: expected {len(synthetic_records)} financial records, found {fin_count}"
        )

    return cust_count, comp_count, fin_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministic synthetic customer database seeder."
    )
    parser.add_argument(
        "--reset", action="store_true", help="Reset/clear tables before seeding."
    )
    parser.add_argument(
        "--db", type=str, default=None, help="Custom SQLite database path."
    )
    args = parser.parse_args()

    repo = CustomerRepository(db_path=args.db)
    try:
        custs, comps, fins = seed_customer_database(repo, reset=args.reset)
        print(f"Database seeded successfully: {repo.db_path}")
        print(f"  Customers:         {custs}")
        print(f"  Complaints:        {comps}")
        print(f"  Financial records: {fins}")
    finally:
        repo.close()


if __name__ == "__main__":
    main()
