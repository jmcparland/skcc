import sqlite3
import requests
import threading
import queue
import time

exitFlag = 0


class worker(threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q

    def run(self):
        print("Starting " + self.name)
        process_data(self.name, self.q)
        print("Exiting " + self.name)


FCCURL = 'https://data.fcc.gov/api/license-view/basicSearch/getLicenses'


def process_data(threadName, q):

    db = sqlite3.connect('membership.db')
    csr = db.cursor()

    while not exitFlag:

        queueLock.acquire()
        if not workQueue.empty():
            callsign = q.get()
            queueLock.release()

            print("%s processing %s" % (threadName, callsign))

            inserted = False
            params = {
                "searchValue": callsign,
                "format": "json"
            }
            rr = requests.get(url=FCCURL, params=params)

            # network or service error? resubmit.
            if rr.status_code != 200:
                print("REST status_code %d for callsign=%s. resubmitting to queue." % (
                    rr.status_code, callsign,))
                queueLock.acquire()
                q.put(callsign)
                queueLock.release()
                continue

            data = rr.json()
            status = data.get("status")  # returns None if not set
            if status == "OK":
                licenses = data["Licenses"]["License"]
                exact_match = False
                for license in licenses:
                    # {'licName': 'McParland, Joseph E', 'frn': '0003435047', 'callsign': 'AB3WW', 'categoryDesc': 'Personal Use', 'serviceDesc': 'Amateur', 'statusDesc': 'Active', 'expiredDate': '06/25/2024', 'licenseID': '3679808', 'licDetailURL': 'http://wireless2.fcc.gov/UlsApp/UlsSearch/license.jsp?__newWindow=false&licKey=3679808'}
                    # want: licName, frn, statusDesc, expiredDate, licenseID
                    # the fcc search returns callsign stem matches with no provision for exact match. lesson learned.
                    if callsign == license.get("callsign"):
                        exact_match = True
                        licName = license.get("licName")
                        frn = license.get("frn")
                        statusDesc = license.get("statusDesc")
                        expiredDate = license.get("expiredDate")
                        licenseID = license.get("licenseID")
                        csr.execute("insert into fcc values (?,?,?,?,?,?)",
                                    (callsign, licName, frn, statusDesc, expiredDate, licenseID))
                        inserted = True
                if not exact_match:
                    cmd = 'insert into errors(callsign) values ("%s")' % callsign
                    csr.execute(cmd)
                    inserted = True
                if inserted:
                    db.commit()
            else:
                print("FCC error for callsign %s" % callsign)
                cmd = 'insert into errors(callsign) values ("%s")' % callsign
                csr.execute(cmd)
                db.commit()
        else:
            queueLock.release()
            time.sleep(1)

    db.commit()
    db.close()


# sqlite> .sch
# CREATE TABLE members(
#   "skccnr" TEXT,
#   "call" TEXT,
#   "name" TEXT,
#   "city" TEXT,
#   "state" TEXT,
#   "ccnr" TEXT,
#   "mbrdate" TEXT
# );

# '{"status": "OK", "Licenses": {"page": "1", "rowPerPage": "100", "totalRows": "1", "lastUpdate": "Jun 29, 2019", "License": [{"licName": "McParland, Joseph E", "frn": "0003435047", "callsign": "AB3WW", "categoryDesc": "Personal Use", "serviceDesc": "Amateur", "statusDesc": "Active", "expiredDate": "06/25/2024", "licenseID": "3679808", "licDetailURL": "http://wireless2.fcc.gov/UlsApp/UlsSearch/license.jsp?__newWindow=false&licKey=3679808"}]}}'

db = sqlite3.connect('membership.db')
csr = db.cursor()

users = csr.execute("select call from members").fetchall()
callsigns = [item[0].upper() for item in users]

# Fill the queue
queueLock = threading.Lock()
workQueue = queue.Queue(30000)
queueLock.acquire()
for callsign in callsigns:
    workQueue.put(callsign)
queueLock.release()

csr.execute("drop table if exists fcc")
csr.execute("create table fcc(call text, licName text, frn text, statusDesc text, expiredDate text, licenseID text)")
csr.execute("drop table if exists errors")
csr.execute("create table errors(callsign text)")
db.commit()
db.close()

# Create new threads
# threadList = ["T-1", "T-2", "T-3", "T-4"]
threadList = ["T-%02d" % xx for xx in range(8)]
threads = []
threadID = 1
for tName in threadList:
    thread = worker(threadID, tName, workQueue)
    thread.start()
    threads.append(thread)
    threadID += 1

# Wait for queue to empty
while not workQueue.empty():
    pass

# Notify threads it's time to exit
exitFlag = 1

# Wait for all threads to complete
for t in threads:
    t.join()

print("Exiting Main Thread")
