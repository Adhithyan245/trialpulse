# ClinicalTrials.gov studies recruiting in Massachusetts

Saved 2026-10-18 for Hackachusetts.

Studies recruiting with a Massachusetts location. The live call returns 20 studies as JSON. data.csv has a larger saved list with the city in Massachusetts.

Rows in data.csv: 3131

Columns: nct_id, title, phase, conditions, massachusetts_city, status

How to use it

- Spreadsheets: open data.csv in Excel or Google Sheets.
- Fresh copy: run `python fetch.py` or `node fetch.js`. Both call the URL below and save the response.
- The preview on the Hackachusetts site is a few rows of this same table.

Direct request

https://clinicaltrials.gov/api/v2/studies?query.locn=Massachusetts&filter.overallStatus=RECRUITING&pageSize=20&fields=NCTId,BriefTitle,OverallStatus,Condition,Phase

Check the source license before publishing a project.
