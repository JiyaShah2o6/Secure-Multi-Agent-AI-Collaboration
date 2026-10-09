#!/usr/bin/env python3
"""
Seed script for Secure Multi-Agent AI Collaboration customer database.
Usage:
    python scripts/seed_database.py
    python scripts/seed_database.py --reset
    python scripts/seed_database.py --db path/to/custom.db
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is in python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.data.customer_repository import CustomerRepository
from app.data.seed import seed_customer_database


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministic synthetic customer database seeder."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset and reseed customer database (clears existing data).",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path to target SQLite database (defaults to .runtime/customers.db).",
    )
    args = parser.parse_args()

    repo = CustomerRepository(db_path=args.db)
    try:
        custs, comps, fins = seed_customer_database(repo, reset=args.reset)
        print("Deterministic database seeding completed.")
        print(f"Target database:   {repo.db_path}")
        print(f"Total customers:   {custs}")
        print(f"Total complaints:  {comps}")
        print(f"Financial records: {fins}")
        print("Status: OK (All records validated)")
    finally:
        repo.close()


if __name__ == "__main__":
    main()
