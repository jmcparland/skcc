# skcc
Scripts and such for SKCC processing

## skcc-augment.py

A quick hack to pull all FCC license records associated with all callsigns in the SKCC membership. The script is tested using python3 and the `requests` module.

The script operates on an sqlite3 database `membership.db` containing a table `members`--an import of `skcclist.txt` from the website.

The script makes extensive use of an FCC ULS API, which performs a partial-match search of an input value against callsigns, FRNs, and license holder names.  All but exact callsign matches are filtered in the script.

Non HTTP 200 responses are assumed to be a network timeout and are requeued for processing. (So far, this hasn't been observed.)

HTTP 200 repsponses indicate a successful inquiry. Either a page of partial-match records is returned, or the response will indicate no matches.

Callsigns searched that do not return a match are inserted into an `errors` table in the same database file. Similarly, if partial matches *are* found but no exact match is found, the callsign is placed in the `errors` table. Through observation, the most common non-matches are foreign member callsigns. Other non-matches include member callsigns containing the "/" character indicating foreign operation or an administrative annotation (e.g., "/SK").

Found license records--potentially several per callsign--are inserted into the `fcc` table in the same database file.

Each FCC license record returned has a field `statusDesc` indicating if the license cited is Active, Expired, Cancelled, or Terminated. This field is used in post-processing.

Since the script is heavily I/O bound with REST calls against the FCC API, the script in its current form is naively multithreaded, launching eight threads to handle an input queue of callsigns to make the execution CPU-bound instead. Each thread maintains its own connection to the database, and the script relies on the database to deconflict access. The script completes in approximately 2.5 hours on a single CPU AWS "micro" instance in Oregon.

N.B.: The script has a few hard-coded values (e.g., 30k queue slots for processing knowing there are currently ~20k members) that should be replaced. Data handling assumes the membership fits in memory for callsign extraction. Queue resubmissions are thrown to the back of the queue without checking if the queue is full. There is no exception handling. Etc. Etc. It's a hack :-)

## The SKCC Membership Schema (in sqlite3 notation)
```
CREATE TABLE members(
  "skccnr" TEXT,
  "call" TEXT,
  "name" TEXT,
  "city" TEXT,
  "state" TEXT,
  "ccnr" TEXT,
  "mbrdate" TEXT
);
```
## Sample FCC Response by Callsign (as in the script) (JSON format)
```
https://data.fcc.gov/api/license-view/basicSearch/getLicenses?searchValue=ab3ww&format=json

{
	"status":"OK",
	"Licenses":{
		"page":"1",
		"rowPerPage":"100",
		"totalRows":"1",
		"lastUpdate":"Jun 29, 2019",
		"License":[
			{
				"licName":"McParland, Joseph E",
				"frn":"0003435047",
				"callsign":"AB3WW",
				"categoryDesc":"Personal Use",
				"serviceDesc":"Amateur",
				"statusDesc":"Active",
				"expiredDate":"06/25/2024",
				"licenseID":"3679808",
				"licDetailURL":"http://wireless2.fcc.gov/UlsApp/UlsSearch/license.jsp?__newWindow=false&licKey=3679808"
			}
		]
	}
}
```
## Sample FCC Response by FRN (XML format)
```
<Response xmlns="http://data.fcc.gov/api/license-view" status="OK">
  <Licenses page="1" rowPerPage="100" totalRows="3" lastUpdate="Jul 3, 2019">
    <License>
      <licName>MC PARLAND, JOSEPH E</licName>
      <frn>0003435047</frn>
      <callsign>KE4CGX</callsign>
      <categoryDesc>Personal Use</categoryDesc>
      <serviceDesc>Amateur</serviceDesc>
      <statusDesc>Expired</statusDesc>
      <expiredDate>02/22/2004</expiredDate>
      <licenseID>534318</licenseID>
      <licDetailURL>
        http://wireless2.fcc.gov/UlsApp/UlsSearch/license.jsp?__newWindow=false&licKey=534318
      </licDetailURL>
    </License>
    <License>
      <licName>McParland, Joseph E</licName>
      <frn>0003435047</frn>
      <callsign>AB3WW</callsign>
      <categoryDesc>Personal Use</categoryDesc>
      <serviceDesc>Amateur</serviceDesc>
      <statusDesc>Active</statusDesc>
      <expiredDate>06/25/2024</expiredDate>
      <licenseID>3679808</licenseID>
      <licDetailURL>
        http://wireless2.fcc.gov/UlsApp/UlsSearch/license.jsp?__newWindow=false&licKey=3679808
      </licDetailURL>
    </License>
    <License>
      <licName>McParland, Joseph E</licName>
      <frn>0003435047</frn>
      <callsign>KC3DCG</callsign>
      <categoryDesc>Personal Use</categoryDesc>
      <serviceDesc>Amateur</serviceDesc>
      <statusDesc>Cancelled</statusDesc>
      <expiredDate>06/25/2024</expiredDate>
      <licenseID>3609336</licenseID>
      <licDetailURL>
        http://wireless2.fcc.gov/UlsApp/UlsSearch/license.jsp?__newWindow=false&licKey=3609336
      </licDetailURL>
    </License>
  </Licenses>
</Response>
```

## Post-Processing

A table of callsigns associated with `Active` records (`statusDesc`) `UNION`ed with callsigns from the `errors` table` constitute a table of accepted callsigns.  Member callsigns not found in this table are considered "questionable" and set asside for further handling.  The questionable calls include Silent Keys, other expired calls, cancelled calls that were not updated with member new callsigns, etc.

[SQL instructions to be included here.]
