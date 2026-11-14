# IT policy discussion - 22 Oct 2026

Attendees: Riya, Dev, Meera

## Context
Prof. Iyer forwarded the college IT policy. It says student personal data (names, roll numbers, phone numbers) must be stored on college-managed servers, not on third-party clouds.

## Options discussed
1. Keep Firebase and store only anonymised IDs. Rejected as too fiddly: the staff screen needs names.
2. Host our own PostgreSQL on the campus VM and issue login tokens from our FastAPI backend.

## Outcome
Option 2 looks right. Riya will confirm after checking how long the migration takes.

## Consequences if we go with option 2
- No more Firebase live updates. The canteen screen would poll every 5 seconds.
- Kabir's login screen has to be reworked.
- Dev has to update the test data scripts.

## Risks
- The campus VM has no automatic backups. Nobody owns this yet.

## Open questions
- Who will ask IT for a nightly backup of the VM?
