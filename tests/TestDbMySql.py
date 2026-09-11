"""
Unit tests of the DbMysql database layer.

Unlike tests/TestCommunication.py these need neither a VMS device nor a MySQL server:
the mysql.connector driver is replaced by a fake connection, so they run anywhere.

    python -m unittest tests.TestDbMySql
"""
import unittest
from unittest import mock

from pyvms.DbMySql import DbMysql


class FakeCursor:
    """
    Minimal stand-in for a mysql.connector cursor
    """

    def __init__(self, rows, column_names, dictionary=False):
        self.rows = rows
        self._column_names = column_names
        self.dictionary = dictionary
        self.executed = []
        self.closed = False

    @property
    def column_names(self):
        # The real driver loses the description once the cursor is closed
        if self.closed:
            raise RuntimeError("column_names read after the cursor was closed")
        return self._column_names

    def execute(self, sql):
        self.executed.append(sql)

    def fetchall(self):
        if self.dictionary:
            return [dict(zip(self._column_names, row)) for row in self.rows]
        return list(self.rows)

    def close(self):
        self.closed = True


class FakeConnection:
    """
    Minimal stand-in for a mysql.connector connection
    """

    def __init__(self, rows=(), column_names=()):
        self.rows = rows
        self.column_names = column_names
        self.cursors = []
        self.closed = False

    def cursor(self, dictionary=None, **kwargs):
        cur = FakeCursor(self.rows, self.column_names, dictionary=bool(dictionary))
        self.cursors.append(cur)
        return cur

    def close(self):
        self.closed = True


class TestDbMySql(unittest.TestCase):
    """
    Tests of DbMysql that do not touch a real database
    """

    COLUMNS = ("SystemId", "Name", "InfoTime", "PmCnt")
    ROW = (101, "turbine", "2026-09-11 12:00:00", 2000000)

    def _db(self, rows=(), column_names=COLUMNS):
        """
        Build a DbMysql backed by a fake connection
        :param rows: Rows the fake cursor returns
        :param column_names: Column names the fake cursor reports
        :return: Tuple of DbMysql instance and the fake connection
        """
        conn = FakeConnection(rows=rows, column_names=column_names)
        db = DbMysql()
        with mock.patch("mysql.connector.connect", return_value=conn) as connect:
            db.connect(host="h", database="BVMS", user="u", password="p")
        self.connect_kwargs = connect.call_args[1]
        return db, conn

    def test_connect_passes_password_keyword(self):
        """Driver is called with password=, not the deprecated passwd= alias"""
        self._db()
        self.assertEqual("p", self.connect_kwargs["password"])
        self.assertNotIn("passwd", self.connect_kwargs)

    def test_get_info_returns_row(self):
        """Existing system yields its row as a tuple"""
        db, _ = self._db(rows=[self.ROW])
        self.assertEqual(self.ROW, db.get_info("info_le", 101))

    def test_get_info_missing_system_returns_none(self):
        """System without a row is not an error, it yields None"""
        db, _ = self._db(rows=[])
        self.assertIsNone(db.get_info("info_le", 999))

    def test_get_info_return_columns_keeps_arity(self):
        """return_columns yields a pair both with and without a row"""
        db, _ = self._db(rows=[self.ROW])
        row, columns = db.get_info("info_le", 101, return_columns=True)
        self.assertEqual(self.ROW, row)
        self.assertEqual(self.COLUMNS, columns)

        db, _ = self._db(rows=[])
        row, columns = db.get_info("info_le", 999, return_columns=True)
        self.assertIsNone(row)
        self.assertEqual(self.COLUMNS, columns)

    def test_get_info_as_dict(self):
        """as_dict asks the driver for a dictionary cursor and yields a named row"""
        db, conn = self._db(rows=[self.ROW])
        row = db.get_info("info_le", 101, as_dict=True)
        self.assertTrue(conn.cursors[0].dictionary)
        self.assertEqual(2000000, row["PmCnt"])
        self.assertEqual(101, row["SystemId"])

    def test_get_info_as_dict_missing_system_returns_none(self):
        """Dictionary variant reports a missing row the same way"""
        db, _ = self._db(rows=[])
        self.assertIsNone(db.get_info("info_le", 999, as_dict=True))

    def test_get_info_selects_by_system_id(self):
        """Row is selected by the system id of the requested turbine"""
        db, conn = self._db(rows=[self.ROW])
        db.get_info("info_le", 101)
        self.assertIn("`info_le`", conn.cursors[0].executed[0])
        self.assertIn("101", conn.cursors[0].executed[0])

    def test_get_info_closes_cursor(self):
        """Cursor is closed even though column names are still returned"""
        db, conn = self._db(rows=[self.ROW])
        db.get_info("info_le", 101, return_columns=True)
        self.assertTrue(conn.cursors[0].closed)

    def test_get_table_details(self):
        """Table details are read for the requested schema"""
        rows = [("buffer_le", 1234, "2026-09-11 12:00:00")]
        db, conn = self._db(rows=rows, column_names=("TABLE_NAME", "TABLE_ROWS", "UPDATE_TIME"))
        self.assertEqual(rows, db.get_table_details("BVMS"))
        self.assertIn("BVMS", conn.cursors[0].executed[0])

    def test_close(self):
        """Closing releases the connection"""
        db, conn = self._db()
        db.close()
        self.assertTrue(conn.closed)
        self.assertIsNone(db.db)


if __name__ == "__main__":
    unittest.main()
