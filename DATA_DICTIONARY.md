# Data Dictionary

## Distribution point

| Field | Purpose | Control |
| --- | --- | --- |
| code | Stable official short code | Unique |
| name | Official display name | Managed by administrator or data manager |
| active | Allows or stops new entries | Existing history remains preserved |

## Household

| Field | Purpose | Control |
| --- | --- | --- |
| household_uid | Printed project household ID | Required, display value retained |
| household_uid_norm | Comparison key | Required, unique, system generated |
| household_head_name | Beneficiary household head | Required, personal data |
| family_name | Optional family name | Personal data |
| household_size | Household member count | One to 100 |
| phone_number | Main contact | Required, personal data |
| additional_contact | Secondary contact | Optional, personal data |
| district, subcounty, parish, village | Administrative location | Required |
| latitude, longitude, altitude_m, gps_precision_m | Field coordinates | Optional, sensitive location data |
| existing stove and fuel fields | Baseline cooking information | Optional |
| row_version | Optimistic concurrency value | System managed |

## Stove

| Field | Purpose | Control |
| --- | --- | --- |
| serial_number | Printed stove serial | Required, display value retained |
| serial_number_norm | Comparison key | Required, unique, system generated |
| stove_type | Product type | Required |
| stove_size | Large, medium, small, or configured value | Required |
| row_version | Optimistic concurrency value | System managed |

## Distribution

| Field | Purpose | Control |
| --- | --- | --- |
| household_id | Household receiving the stove | Unique foreign key |
| stove_id | Stove assigned to the household | Unique foreign key |
| distribution_point_id | Official distribution location | Required foreign key |
| distributed_on | Distribution date | Required |
| receiver_type, receiver_name, receiver_relationship | Actual person receiving | Representative name required when applicable |
| carbon_waiver_accepted | Recorded acceptance | Required Boolean |
| conditions_accepted | Recorded acceptance | Required Boolean |
| ambassador_name | Responsible field representative | Required |
| verification_code | Form and QR reference | Unique, system generated |
| signature_status | Unsigned, captured, verified, or rejected | System workflow |
| legacy source fields | Traceability to imported Kobo record | Optional |
| row_version | Optimistic concurrency value | System managed |

## Signature evidence

| Field | Purpose | Control |
| --- | --- | --- |
| beneficiary_name | Person whose signature appears | Required |
| witness_name | Witness or ambassador | Required |
| signed_at | Claimed signing time | Required, timezone aware |
| object_key | Private file storage reference | System generated |
| sha256 | Tamper evident content digest | System generated |
| captured_by_user_id | Authenticated capturing officer | Required |
| verified_by_user_id, verified_at | Independent review | Data manager or administrator |
| rejected_reason | Explains rejected evidence | Required on rejection |

## Audit log

The audit log records actor, action, entity, before values, after values, reason, request ID, source IP, and time. It is append only through the application. Database administrators should further restrict direct update and delete privileges in production.

