# Trailmark demo files

Synthetic test data for Trailmark (Team ERROR404). Every name, company, number and credential is invented. Nothing here is real, and the "keys" and "passwords" are obviously fake on purpose.

## What is in the box

| Folder | What it is | Use it for |
|---|---|---|
| `campus_food_app/` | Main sample: a 4-person student team whose backend lead is leaving. 5 meeting notes (.md), a chat export (.txt, about 170 messages), a task board (.csv), a GitHub issues export (.json). | Prompt 9 sample project, prompts 6 to 8 and 12 |
| `ngo_event/` | Volunteer charity walk. Email thread (.txt), plan (.md), budget (.csv), volunteers (.json). Formal tone, different vocabulary. | Proving it works on a different case (prompt 11) |
| `research_lab/` | PhD student leaving a lab. Formal notes (.md) and an experiments table (.csv). | Proving it works on a third case (prompt 11) |
| `stress/` | Six deliberately awkward inputs. | Prompts 5, 10 and 11 |
| `edge_cases/` | File-format oddities: empty file, over-limit file, Windows line endings with BOM, markdown noise, tricky CSV, unknown extension, paste snippet. | Prompts 3 and 10 |
| `answer_keys/` | What was planted and where. **Never upload these to the app.** | Checking results by hand and in `scripts/eval.py` |

## How to use them

1. Copy `campus_food_app/` to `samples/campus_food_app/` in your repo, and the other case folders next to it. Copy each key from `answer_keys/` to `samples/<case>/ANSWER_KEY.md` only once your sample loader skips that file, or keep the keys outside `samples/`.
2. In the app, upload all files from one case folder together as one case. Fill in: project `CampusBite`, leaver `Riya Kulkarni`, role `Backend developer`.
3. Use the table below to know which file to use for each test step in the build pack.

## Which file tests what

| Build pack step | File(s) | What you should see |
|---|---|---|
| Prompt 3: size limits | `edge_cases/too_large.txt`, `edge_cases/empty.txt` | A clear "too large" message for the first (over 1,000,000 bytes). A clear "empty file" message for the second. No crash. |
| Prompt 3: CSV chunking | `campus_food_app/tasks.csv`, `edge_cases/csv_edge.csv` | Header repeated in every chunk. The quoted comma, the doubled quote, the line break inside a cell and the Hindi text all survive. |
| Prompt 3: odd encodings | `edge_cases/windows_crlf_bom.txt` | Reads cleanly; no stray BOM character at the start; line numbers still right. |
| Prompt 3: unknown extension | `edge_cases/unknown_extension.log` | Treated as plain text with a visible warning. |
| Prompt 3: JSON | `campus_food_app/github_issues.json`, `ngo_event/volunteers.json` | Pretty-printed, chunked, searchable. |
| Prompt 5: quote normalisation | `edge_cases/markdown_noise.md`, `edge_cases/windows_crlf_bom.txt` | Quotes copied from these with straight quotes or single spaces still verify. |
| Prompt 6: paste box | `edge_cases/paste_snippet.txt` | Paste it into the paste box. You get about 4 items: invoice template gap, CRM decision, contract renewal risk, domain-renewal question. |
| Prompt 7 and 8: review and handover | `campus_food_app/*` | Several dozen items across all six types, with the traps below. Mark the fake credential items confidential and confirm they never reach the share page. |
| Prompt 10: thin input | `stress/01_five_lines.txt` | "Not enough evidence" state, not an empty table. |
| Prompt 10: injection | `stress/03_injection_only.txt`, plus the injection line in `campus_food_app/chat_export.txt` | A notice that the text looks like instructions. Nothing is approved. No items from the commands themselves. |
| Prompt 10: secrets | the `FAKE-...` lines in `chat_export.txt`, emails in `ngo_event/email_thread.txt`, phones in `ngo_event/volunteers.json` | Auto-flagged confidential. |
| Prompt 11: contradictions | `stress/02_contradictory.md` | Both launch dates, both database owners and both database decisions appear as separate items, each with its own quote. The tool must not pick a winner silently. |
| Prompt 11: other languages | `stress/04_hinglish_chat.txt`, `stress/05_hindi_notes.md` | Items extracted with quotes in the original language that still verify. |
| Prompt 11: messy chat | `stress/06_emoji_chat.txt` | Sensible items (demo day unclear, slides owner, rendering bug as a risk) despite emoji. |
| Prompt 11: other cases | `ngo_event/*`, `research_lab/*` | Similar verification rates to the main sample, with no code changes. |

## Honest notes

- The sample data was written with an AI assistant. Say so in `docs/AI_DISCLOSURE.md`.
- Several planted traps are only partly findable on purpose (for example the unexplained `pos-bridge`). The tool should show a gap or an open question, never invent an explanation.
- Do not tune your prompts to the answer keys. If a trap is missed, record it as missed in your evaluation results.
