# Preliminary Data Quality Findings

These findings were calculated from the supplied semicolon separated Kobo export. No beneficiary names, phone numbers, coordinates, serial values, or household values are reproduced here.

| Check | Finding |
| --- | ---: |
| Rows in supplied export | 2,964 |
| Columns | 45 |
| Unique normalized household IDs | 2,942 |
| Household identifiers repeated after normalization | 22 keys, representing 22 extra rows |
| Unique normalized stove serials | 2,924 |
| Stove serials repeated after normalization | 39 keys, representing 40 extra rows |
| Raw distribution center spelling variants after whitespace cleanup | 91 |
| Distribution center variants after removing case and punctuation | 66 |
| Blank household IDs | 0 |
| Blank stove serials | 0 |
| Blank household head names | 0 |
| Blank telephone numbers | 0 |
| Blank distribution dates | 0 |
| Blank legacy photograph URLs | 0 |

## Decisions required before migration

i. Confirm why the export contains 2,964 rows when the stated working population is approximately 1,256 households.

ii. Confirm the exact three official distribution points. The export contains many distinct location labels and cannot safely be collapsed to three by software without an authorized mapping.

iii. Adjudicate every duplicate household ID and stove serial. The importer will quarantine every row involved in an internal duplicate instead of retaining an arbitrary first occurrence.

iv. Validate phone number length and format. Completeness does not prove validity.

v. Decide whether the legacy photograph proves receipt, proves a signature, or is merely a distribution photograph. The importer retains its URL for traceability but does not mark the record signed.

vi. Review the consent fields. Blank legacy responses are imported as false and should not be transformed into acceptance without evidence.

Run the repeatable analysis with:

```bash
python scripts/analyze_kobo.py data/private/your-kobo-export.csv
```
