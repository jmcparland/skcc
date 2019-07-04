import requests

from bs4 import BeautifulSoup
import re

def licenseRecordsByCall(callsign, statusFilter=""):
	"""Returns a list of license records associated with a callsign (exact match)"""
	csu = callsign.upper()
	FCCURL = 'https://data.fcc.gov/api/license-view/basicSearch/getLicenses'
	params = {
		"searchValue": csu,
		"format": "json"
	}
	rr = requests.get(url=FCCURL, params=params)

	response = {"status_code": rr.status_code, "licenses": []}

	if rr.status_code != 200:
		return response

	data = rr.json()
	status = data.get("status")  # returns None if not set
	if status == "OK":
		licenses = data["Licenses"]["License"]
		for license in licenses:
			# {'licName': 'McParland, Joseph E', 'frn': '0003435047', 'callsign': 'AB3WW', 'categoryDesc': 'Personal Use', 'serviceDesc': 'Amateur', 'statusDesc': 'Active', 'expiredDate': '06/25/2024', 'licenseID': '3679808', 'licDetailURL': 'http://wireless2.fcc.gov/UlsApp/UlsSearch/license.jsp?__newWindow=false&licKey=3679808'}
			# want: licName, frn, statusDesc, expiredDate, licenseID
			# the fcc search returns callsign stem matches with no provision for exact match. lesson learned.
			if csu == license.get("callsign"):
				if statusFilter and license.get("statusDesc") != statusFilter:
					continue
				response["licenses"].append(license)

	return response


def licenseHasSkNotation(licenseID):
	"""Checks the license admin page for the word 'deceased'."""
	# licenseID = license_record.get("licenseID")
	FCCURL = "https://wireless2.fcc.gov/UlsApp/UlsSearch/licenseAdminSum.jsp?licKey=%s" % licenseID
	rr = requests.get(FCCURL)
	response = {"status":rr.status_code}
	if rr.status_code != 200:
		response["sk_comments"] = []
		return response

	soup = BeautifulSoup(rr.text, features="html.parser")
	response["sk_comments"] = soup.body.findAll(text=re.compile("deceased", re.I))

	return response
