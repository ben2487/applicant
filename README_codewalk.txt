Project Codewalk and CLI Flows

This document summarizes the command-line interface in `src/webbot/cli.py`, the code paths each command exercises, and the key data structures. It ends with a step-by-step guide for a full, single-command application flow.

How to Run

- Base entrypoint: poetry run python -m src.webbot.cli <command> [options]
- Help: poetry run python -m src.webbot.cli --help

Commands and Code Flow

list-browser-profiles
- Purpose: list local Chrome profiles to use for automation.
- Entry: src/webbot/cli.py:list_browser_profiles
- Flow: browser_profiles.discover_browser_profiles() → prints fields (name, dir_name, path, email, default).

list-user-profiles
- Purpose: list app user profiles (settings/secrets/resume index live here).
- Entry: src/webbot/cli.py:list_user_profiles
- Flow: user_profiles.discover_user_profiles() → load_user_settings(profile) → display .secrets.google_drive_user and human name.

list-users
- Purpose: compact list of user profile names and key info.
- Entry: src/webbot/cli.py:list_users
- Flow: Same sources as list-user-profiles; single-line per profile.

create-user <user_profile>
- Purpose: create a new user profile directory.
- Entry: src/webbot/cli.py:create_user
- Flow: user_profiles.create_user_profile(name) → prompt human name → load_user_settings/save_user_settings.

test-openai-key
- Purpose: sanity-check OpenAI credentials.
- Entry: src/webbot/cli.py:test_openai_key
- Flow: ai_search.get_openai_client() then a small chat.completions.create (gpt-4o-mini).

google-drive-login <user_profile> [--client-secret <path>]
- Purpose: OAuth link the profile to Google Drive.
- Entry: src/webbot/cli.py:google_drive_login_cmd
- Flow: google_drive.google_drive_login(profile, client_secret_path) → persists credentials + account into <profile>/secrets.json.

sync-resumes <user_profile>
- Purpose: fetch resumes from Drive into the user profile and index them.
- Entry: src/webbot/cli.py:sync_resumes
- Flow: google_drive.refresh_resumes(profile) → exports Google Docs to resume_pdf/<base>/resume.pdf and resume.txt → updates <profile>/resumes.json.

run <user_profile> [--use-browser-profile <ChromeProfile>] [--initial-job-url <URL>] [--ai-mode OPEN_AI|LLM_OFF]
- Purpose: launch or attach to Chrome with a chosen Chrome profile; optionally visit a job URL, extract text and structured job info, and (if the host is in do-not-apply) search for an apply URL.
- Entry: src/webbot/cli.py:run
- Flow:
  - Browser attach/launch: browser.smart_launch_with_profile(profile).
  - If initial_job_url:
    - Navigation: browser.goto_and_wait(page, url); extract text via extract.extract_visible_text.
    - Job extract: struct_extract.parse_job_page (heuristics + optional OpenAI JSON refinement).
    - If domain(initial_job_url) is in data/do-not-apply.txt:
      - Agentic search: agents.find_apply_page.smart_find_apply_url(page, company_name, job_title) → prints prompt/response and picks.
      - Legacy search: apply_finder.find_company_homepage_from_job_page + apply_finder.find_apply_url (DuckDuckGo HTML) → prints comparison.

snapshot-url <url> [--use-browser-profile ...] [--out-dir ...] [--headless/--no-headless] [--wait-selector ...]
- Purpose: save a local snapshot (HTML + DOM HTML + screenshot + frames) of any page.
- Entry: src/webbot/cli.py:snapshot_url
- Flow: goto_and_wait → optional waits → forms.snapshot.snapshot_page() writes manifest.json, page.html, dom.html, screenshot and frame files.

download-test-url <url> [--use-browser-profile ...] [--name ...] [--click-apply] [--apply-selector ...] [--headless/--no-headless] [--wait-selector ...] [--manual-after-apply]
- Purpose: persist a real-world fixture under tests/fixtures/realworld/<name>/{initial,after_apply}.
- Entry: src/webbot/cli.py:download_test_url
- Flow: snapshot initial; optionally click an Apply control (heuristic or manual) to reach the form; snapshot after_apply. Uses an internal _heuristic_click_apply.

extract-form-from-snapshot <snapshot_dir>
- Purpose: parse a saved snapshot directory into a structured form schema.
- Entry: src/webbot/cli.py:extract_form_from_snapshot
- Flow: forms.extractor.extract_form_schema_from_snapshot_dir → emit JSON of FormSchema.

answer-form-from-snapshot <snapshot_dir> [--user-profile ...] [--ignore-optional/--no-ignore-optional] [--model ...]
- Purpose: load schema from snapshot, choose a resume, generate LLM answers, and print key Q&A pairs.
- Entry: src/webbot/cli.py:answer_form_from_snapshot
- Flow:
  - Extract schema.
  - Resume selection: resume_alignment.run_alignment_for_files(profile, job_desc_path) (OpenAI JSON) → falls back to concatenating available resume.txt content.
  - Answering: forms.answerer.generate_answers(schema, resume_text, job_context, ignore_optional, model) → answers stored in field.meta["answer"].

answer-realworld-fixtures [--user-profile ...] [--base-dir ...] [--model ...] [--ignore-optional/--no-ignore-optional]
- Purpose: batch process real snapshots (initial/after_apply) to validate extraction + answering.
- Entry: src/webbot/cli.py:answer_realworld_fixtures
- Flow: iterate fixture folders; extract schema; generate answers; emit a compact summary per fixture/phase.

extract-form-url <url> [--use-browser-profile ...] [--headless/--no-headless] [--wait-selector ...]
- Purpose: navigate to a live URL and print its inferred form schema JSON (no filling).
- Entry: src/webbot/cli.py:extract_form_url
- Flow: launch → navigate → forms.extractor.extract_form_schema_from_page(page, url) → print JSON.

execute-form-url <url> [--user-profile ...] [--use-browser-profile ...] [--headless/--no-headless] [--wait-selector ...] [--hold-seconds N]
- Purpose: open a live application form URL, generate demo answers, upload a resume, and fill the form (does not submit) and hold the browser open briefly.
- Entry: src/webbot/cli.py:execute_form_url
- Flow:
  - Extract schema: forms.extractor.extract_form_schema_from_page.
  - Fill demo answers directly (text/select/checkbox/radio).
  - Execute: forms.executor.execute_fill_plan(page, schema, profile_root, wait_seconds).

apply-flow <starting_url> [--user-profile ...] [--use-browser-profile ...] [--headless/--no-headless] [--ignore-optional/--no-ignore-optional] [--model ...] [--hold-seconds N]
- Purpose: run the entire application flow end-to-end in one command.
- Entry: src/webbot/cli.py:apply_flow
- Flow:
  1) Attach/launch Chrome context: browser.smart_launch_with_profile.
  2) Open starting URL and extract visible text: extract.extract_visible_text.
  3) Structured job extract: struct_extract.parse_job_page (LLM or heuristics) to get company/title.
  4) Find an applyable URL:
     - Agentic: agents.find_apply_page.smart_find_apply_url (DuckDuckGo candidates + OpenAI JSON chooser) with prompts/responses printed.
     - Legacy: apply_finder.find_company_homepage_from_job_page + apply_finder.find_apply_url (DuckDuckGo HTML heuristics).
     - Side-by-side comparison printed.
  5) Navigate to the application form (if URL found) or attempt a heuristic Apply click in-place.
  6) Extract form schema from the live DOM: forms.extractor.extract_form_schema_from_page.
  7) Select best resume for this job: resume_alignment.select_best_resume_for_job_description over <profile>/resumes.json; fallback concatenation of resume.txt files.
  8) Generate LLM answers: forms.answerer.generate_answers(schema, resume_text, job_context, model, ignore_optional) → answers in field.meta["answer"].
  9) Execute the fill (no submit): forms.executor.execute_fill_plan(page, answered_schema, profile_root, preferred_resume_pdf=<chosen_pdf>, wait_seconds=<hold_seconds>).

Key Data Structures

- FormSchema (src/webbot/forms/schema.py)
  - sections: List[FormSection] with fields: List[FormField]
  - FormField: field_id, name, label, placeholder, type, required, options, locators.css/xpath/aria/nth, meta
  - validity: Validity{ is_valid_job_application_form: bool, confidence: float, meta: dict }

- Snapshot artifacts (src/webbot/forms/snapshot.py)
  - snapshot_page() writes manifest.json with page/frame listings, page.html, dom.html, screenshot.png, frame-*.html, frame-*-dom.html.

- Resume index (user profile directory)
  - <profile>/resumes.json maintained by google_drive.refresh_resumes: items have id, name, base_name, modifiedTime, pdf_path, txt_path.

- Job posting extract (src/webbot/struct_extract.py)
  - JobPostingExtract contains: is_job_posting, title, company_name, requirements, work_mode/notes, locations, currencies_detected, non_us_indicia.

Core Modules and Responsibilities

- browser.py: Chrome attach/launch; goto_and_wait.
- browser_profiles.py: discover Chrome profiles; detect default/last-used.
- apply_finder.py: do-not-apply list; DuckDuckGo HTML querying; homepage/apply URL heuristics.
- agents/find_apply_page.py: agentic (LLM-guided) selection of official domain/careers/apply URL from search candidates.
- extract.py: extract visible body text.
- struct_extract.py: heuristics + (optional) OpenAI JSON refinement of job posting metadata.
- forms/extractor.py: live DOM/snapshot scanning to infer fields and validity.
- forms/answerer.py: compose and call OpenAI to generate answers; inject into schema meta.
- forms/executor.py: resume upload + field filling (no submit), respects prefilled values; now supports preferred resume PDF.
- forms/snapshot.py and forms/snapshot_loader.py: write/read snapshots (HTML/DOM/screenshot/frames-manifest), and load snapshots in headless mode.
- user_profiles.py: create/find profiles; secrets and settings read/write.
- google_drive.py: OAuth login; export Google Docs PDF/text; maintain resumes.json; sync local copies.
- ai_search.py: OpenAI client configuration and search-query generation.

End Section: Steps, Code Flow, and Data Structures for a Full Application

1) Starting with a URL, auto-search/navigate to the company official page and find an applyable link
   - Use: apply-flow <starting_url>
   - Code:
     - extract.extract_visible_text to get page content; struct_extract.parse_job_page for company/title.
     - Agentic: agents.find_apply_page.smart_find_apply_url (DuckDuckGo candidates → OpenAI choose JSON).
     - Legacy: apply_finder.find_company_homepage_from_job_page + apply_finder.find_apply_url.
   - Data exercised: JobPostingExtract, do-not-apply domain list (data/do-not-apply.txt), DuckDuckGo HTML results.

2) Then, in the same browser session, navigate to the actual form (same tab)
   - Use: same playwright Page from browser.smart_launch_with_profile; either goto chosen apply URL or heuristic Apply click.
   - Note: A dedicated reusable “navigate-to-form” function can be factored if needed; current flow performs it inline using the same Page.

3) Extract the job description from the live DOM and select the closest match resume
   - Live DOM text: extract.extract_visible_text.
   - Resume selection: resume_alignment.select_best_resume_for_job_description (operates over <profile>/resumes.json) with OpenAI JSON selection; fallback: concatenated resume.txt.
   - Data exercised: resumes.json entries with pdf_path/txt_path; chosen resume id/name/paths.

4) Use that resume to prepare LLM responses for the questions extracted from the form
   - Extract schema: forms.extractor.extract_form_schema_from_page.
   - Generate answers: forms.answerer.generate_answers(schema, resume_text, job_context, model, ignore_optional) → answers placed into field.meta["answer"].
   - Data exercised: FormSchema, per-field metadata (type/required/labels/options), LLM prompt/response.

5) Actually fill out the form and upload the selected resume, doing everything except clicking submit
   - Execute: forms.executor.execute_fill_plan(page, answered_schema, profile_root, preferred_resume_pdf=<chosen pdf>, wait_seconds=N).
   - Behavior: upload (visible/hidden file inputs; click upload-ish controls if needed), avoid overriding prefilled values, fill remaining fields, then wait for manual review. No submit action is triggered.

One-Command Option

- Use apply-flow for end-to-end automation:
  - poetry run python -m src.webbot.cli apply-flow --user-profile <profile> --use-browser-profile <ChromeProfile> <starting_url>
  - Options: --headless/--no-headless, --ignore-optional/--no-ignore-optional, --model, --hold-seconds

Notes

- OpenAI key required for agentic search, structured extract (OPEN_AI), resume alignment, and answer generation. See ai_search.get_openai_client.
- Use google-drive-login and sync-resumes to populate resumes.json and local resume files before running application flows.
- The tool prints LLM prompts/responses and compares agentic vs legacy apply URL choices side-by-side where applicable.
