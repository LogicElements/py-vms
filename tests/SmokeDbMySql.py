"""
Smoke test of DbMysql against a real BVMS database.

This is deliberately not a unittest: it needs a reachable MySQL server and is meant to be
run once by hand after switching the driver to mysql-connector-python, to confirm that the
new driver returns the same value types as the old one.

    python tests/SmokeDbMySql.py --host 10.0.0.1 --user VMS --password *** --system-id 101
"""
import argparse
import datetime
import sys

import mysql.connector

from pyvms.DbMySql import DbMysql


def main():
    parser = argparse.ArgumentParser(description="Read back a BVMS database with DbMysql")
    parser.add_argument("--host", default="localhost", help="MySQL server, default localhost")
    parser.add_argument("--database", default="BVMS", help="Database name, default BVMS")
    parser.add_argument("--user", default="VMS", help="MySQL user, default VMS")
    parser.add_argument("--password", required=True, help="MySQL password")
    parser.add_argument("--info", default="info_le", help="Information table, default info_le")
    parser.add_argument("--system-id", type=int, default=101, help="System ID of a turbine")
    parser.add_argument("--missing-id", type=int, default=999999,
                        help="System ID that has no row, used to check the empty result")
    args = parser.parse_args()

    print(f"Driver: mysql.connector {mysql.connector.__version__}")
    print(f"Python: {sys.version.split()[0]}")

    db = DbMysql()
    db.connect(host=args.host, database=args.database, user=args.user, password=args.password)
    errors = 0

    # Table details: UPDATE_TIME must stay a datetime, the agent subtracts it from now()
    details = db.get_table_details(args.database)
    print(f"\nget_table_details: {len(details)} tables")
    for name, rows, updated in details[:5]:
        print(f"  {name}: rows={rows} updated={updated!r}")
    stamps = [d[2] for d in details if d[2] is not None]
    if stamps and not isinstance(stamps[0], datetime.datetime):
        print(f"  ERROR: UPDATE_TIME is {type(stamps[0]).__name__}, expected datetime")
        errors += 1

    # Information row as a tuple
    row = db.get_info(args.info, args.system_id)
    print(f"\nget_info(system {args.system_id}): {row!r}")
    if row is None:
        print(f"  ERROR: no row for system {args.system_id}, pick an existing --system-id")
        errors += 1

    # Information row keyed by column name
    named = db.get_info(args.info, args.system_id, as_dict=True)
    if named is not None:
        print(f"\nget_info(as_dict): {len(named)} columns")
        for key, value in named.items():
            print(f"  {key} = {value!r}")

    # Missing system must be reported as None, not as an exception
    missing = db.get_info(args.info, args.missing_id)
    print(f"\nget_info(missing system {args.missing_id}): {missing!r}")
    if missing is not None:
        print("  ERROR: expected None for a system with no row")
        errors += 1

    db.close()
    print(f"\n=== RESULT === {'SUCCESS' if errors == 0 else f'{errors} ERRORS'} ===")
    return errors


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
