import fcc
import sqlite3

DB="membership.3.db"

db=sqlite3.connect(DB)
cur=db.cursor()

cur.execute("drop table if exists sk")
cur.execute("create table sk(licenseID text, fcc_comment text)")
db.commit()

obs=cur.execute('select licenseID from fcc where statusDesc="Cancelled"')
cancelled_ids = [id[0] for id in obs]

for id in cancelled_ids:
	rr=fcc.licenseHasSkNotation(id)
	sk=rr.get("sk_comments")

	if sk:
		txt=sk[0].strip()
		print("%s\t%s" % (id, txt))

		cur.execute("insert into sk values (?,?)", (id,txt))
		db.commit()
