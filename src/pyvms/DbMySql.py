import datetime
import mysql.connector
from collections import Counter
from matplotlib import pyplot as plt
import matplotlib.dates as mdates


class DbMysql:
    """
    Class for closed-loop VMS testing via mysql database read back
    """
    def __init__(self):
        self.db = None

    def connect(self, host='localhost'):
        """
        Connect to mysql database containing instance of le_buffer table
        :param host: Server to connect, e.g., loacalhost, 192.168.1.7
        :return: None
        """
        self.db = mysql.connector.connect(
            host=host,
            user="VMS",
            passwd="Vms2015",
            database="BVMS"
        )

    def close(self):
        """
        Close connection to database
        :return: None
        """
        self.db.close()
        self.db = None

    def truncate_buffer(self, suffix=""):
        """
        Truncate buffer_le table
        :param suffix: Buffer_le suffix
        :return: None
        """
        cursor = self.db.cursor()
        sql = "TRUNCATE TABLE buffer_le" + suffix
        cursor.execute(sql)

    def iterate(self, sql, commit=0, suffix=""):
        """
        Perform one iteration of test.
        It consists of one Select SQL query followed by optional erase of selected rows.
        :param sql: SQL query to select rows of interest
        :param commit: Commit erase operation (none-zero for delete)
        :param suffix: Buffer_le suffix
        :return: Transposed tuple of selected rows
        """
        cursor = self.db.cursor()
        cursor.execute(sql + f" order by idbuffer limit 10000")
        result = cursor.fetchall()

        # Erase fetched data
        if len(result) > 0:
            start = result[0][0]
            end = result[-1][0]
            limit = len(result)
            sql = f"DELETE FROM buffer_le{suffix} where idbuffer >= {start} and idbuffer <= {end} limit {limit}"
            if commit != 0:
                cursor.execute(sql)
                self.db.commit()
                if cursor.rowcount != limit:
                    print(f"Wrong affected row count {cursor.rowcount}. Expected {limit} rows.")

        return result

    def plot_events(self, sys_id=101, last=0):
        """
        Plot graph representing occurrence of diagnostics events
        :param sys_id: ID of VMS system
        :param last: Number of the most recent events (0 means all)
        :return: Dictionary of events occurrence (histogram)
        """
        sql = f"SELECT * FROM diag_le where SystemId = {sys_id} order by iddiag"
        if last:
            sql += f" desc limit {last}"
        cursor = self.db.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        # result = sorted(result, key=lambda i: i[4])
        res = dict(Counter(res[4] for res in result))
        cnt = sorted(res)
        dates = []
        for event in cnt:
            evts = [a[3] for a in result if a[4] == event]
            dates.append(evts)

        x = []
        y = []
        for idx, lst in enumerate(dates):
            for time in lst:
                x.append(time)
                y.append(idx)
        plt.figure(f"Diagnostic events for system {sys_id}", figsize=(12, 6))
        plt.title(f"Diagnostic events for VMS system ID {sys_id}")
        plt.ylim((-1, len(cnt)))
        plt.yticks(range(len(cnt)), [a for a in cnt])
        plt.scatter(x, y, color='r', s=70)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        plt.gcf().autofmt_xdate()
        plt.show()
        return res

    def speed_check(self, rpm=3000, tol=1.05, suffix=""):
        """
        Perform simple check of measured speed.
        It selects only id and PM count and verifies measured speed within given tolerance
        :param rpm: Expected RPM
        :param tol: Nominal tolerance
        :param suffix: Buffer le suffix
        :return: 0 on success, 1 on fail
        """
        res = self.iterate("SELECT idbuffer, PmCnt FROM buffer_le" + suffix, commit=1)
        if len(res) == 0:
            print("No data from DB")
            return 1
        res = tuple(zip(*res))
        if len(res[0]) > 10:
            meas_speed = sum(res[1][-10:]) / 10
            return in_tolerance(rpm, 100000000 / meas_speed * 60, tol, "Wrong measured speed at buffer_le" + suffix)
        else:
            print("Not enough data from DB buffer_le" + suffix)
            return 1


def in_tolerance(val1, val2, tol, msg=""):
    ret = 0
    if abs(val1) * tol < abs(val2) or abs(val1) / tol > abs(val2):
        ret = 1
        print(f"Values of \"{msg}\" ouf of tolerance {tol}. Values {val1}, {val2}.")
    return ret


if __name__ == "__main__":
    print(f"=== START === " + datetime.datetime.now().strftime("%y/%m/%d %H:%M:%S ==="))
    err = 0

    mydb = DbMysql()
    mydb.connect()
    err += mydb.speed_check()
    mydb.close()

    print(f"=== END === " + datetime.datetime.now().strftime("%y/%m/%d %H:%M:%S ==="))
    print('=== RESULT === {} === '.format('SUCCESS' if err == 0 else '{} ERRORS'.format(err)))







