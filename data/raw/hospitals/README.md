# Massachusetts hospitals

Saved 2026-10-18 for Hackachusetts.

Every facility in the MassGIS hospital layer, not only western Massachusetts. The page preview is a western acute-hospital slice.

Rows in data.csv: 103

Columns: name, facility_type, municipality, county, icu_beds, med_surg_beds, pediatric_beds

How to use it

- Spreadsheets: open data.csv in Excel or Google Sheets.
- Fresh copy: run `python fetch.py` or `node fetch.js`. Both call the URL below and save the response.
- The preview on the Hackachusetts site is a few rows of this same table.

Direct request

https://arcgisserver.digital.mass.gov/arcgisserver/rest/services/AGOL/Hospitals/MapServer/0/query?where=1%3D1&outFields=FACILITY_NAME,FACILITY_TYPE,MUNICIPALITY,COUNTY,ICU,MED_SURG,PEDIATRIC&returnGeometry=false&resultRecordCount=200&f=json

Check the source license before publishing a project.
