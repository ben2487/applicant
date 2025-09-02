from __future__ import annotations
import asyncio
import typer
from typing import Optional
from pathlib import Path
from .browser_profiles import discover_browser_profiles, find_browser_profile_by_name_or_dir, BrowserProfile
from .user_profiles import (
    discover_user_profiles,
    find_user_profile_by_name,
    UserProfile,
    create_user_profile,
    load_user_settings,
    save_user_settings,
)
from .browser import smart_launch_with_profile, goto_and_wait
from .forms import snapshot_page
from .forms.extractor import extract_form_schema_from_snapshot_dir, extract_form_schema_from_page
from .forms.executor import execute_fill_plan
from .forms.answerer import generate_answers
from .user_profiles import find_user_profile_by_name
from .extract import extract_visible_text
from .apply_finder import (
    load_do_not_apply_domains,
    domain,
    find_company_homepage_from_job_page,
    find_apply_url,
)
from .ai_search import get_openai_client, OpenAIConfigError
from .agents.find_apply_page import smart_find_apply_url
from .struct_extract import parse_job_page, AIMode, JobPostingExtract
from .google_drive import google_drive_login, refresh_resumes
from .resume_alignment import run_alignment_for_files, select_best_resume_for_job_description
from .config import repo_root

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback(invoke_without_command=True)
def _root(
    test_resume_selection: bool = typer.Option(
        False,
        "--test-resume-selection",
        help=(
            "Run a local resume alignment test using user 'user_ben' and "
            "data/test_job_desc1.txt with a strong OpenAI model."
        ),
    ),
) -> None:
    if test_resume_selection:
        profile = _resolve_user_profile("user_ben")
        job_path = repo_root() / "data/test_job_desc1.txt"
        try:
            result, trace = run_alignment_for_files(
                profile=profile, job_desc_path=job_path, model="gpt-4o"
            )

            typer.echo("\n" + "🔵" * 20 + " RESUME ALIGNMENT PROMPT " + "🔵" * 20)
            typer.echo(trace["prompt"])
            typer.echo("\n" + "🟢" * 20 + " RESUME ALIGNMENT RESPONSE " + "🟢" * 20)
            typer.echo(trace["response"])

            typer.echo("\n" + "🟡" * 20 + " SELECTION SUMMARY " + "🟡" * 20)
            typer.echo(f"Chosen resume id:   {result.chosen_resume_id}")
            typer.echo(f"Chosen resume name: {result.chosen_resume_name}")
            typer.echo(f"Confidence:         {result.confidence_label}")
            if result.missing_summary:
                typer.echo(f"Missing summary:    {result.missing_summary}")
            if result.reasoning:
                typer.echo(f"Reasoning:          {result.reasoning}")
        except Exception as e:
            typer.echo(f"❌ Resume alignment test failed: {e}")
            raise typer.Exit(code=1)

        raise typer.Exit(code=0)


def _pretty_print_extract(extract: JobPostingExtract) -> None:
    """Pretty print the structured job posting extract."""
    typer.echo("\n" + "="*60)
    typer.echo("📋 STRUCTURED JOB POSTING EXTRACT")
    typer.echo("="*60)
    
    typer.echo(f"🔍 Is Job Posting:     {extract.is_job_posting}")
    typer.echo(f"📝 Title:              {extract.title or 'Not found'}")
    typer.echo(f"🏢 Company:            {extract.company_name or 'Not found'}")
    typer.echo(f"💼 Work Mode:          {extract.work_mode or 'Not specified'}")
    typer.echo(f"📍 Locations:          {', '.join(extract.locations) if extract.locations else 'Not specified'}")
    typer.echo(f"💰 Currencies:         {', '.join(extract.currencies_detected) if extract.currencies_detected else 'None detected'}")
    typer.echo(f"🌍 Non-US Indicia:     {', '.join(extract.non_us_indicia) if extract.non_us_indicia else 'None detected'}")
    
    if extract.requirements:
        typer.echo(f"📋 Requirements:")
        for req in extract.requirements:
            typer.echo(f"    • {req}")
    
    typer.echo("="*60 + "\n")


@app.command()
def list_browser_profiles() -> None:
    """List available Chrome browser profiles."""
    profs = discover_browser_profiles()
    if not profs:
        typer.echo(
            "No Chrome browser profiles found. Make sure Chrome is installed and has been launched at least once."
        )
        raise typer.Exit(code=2)
    for p in profs:
        typer.echo(f"- name: {p.name}")
        typer.echo(f"  dir_name: {p.dir_name}{'  (default)' if p.is_default else ''}")
        typer.echo(f"  path: {p.path}")
        if p.email:
            typer.echo(f"  email: {p.email}")
        typer.echo("")


@app.command()
def list_user_profiles() -> None:
    """List available user profiles."""
    profs = discover_user_profiles()
    if not profs:
        typer.echo(
            "No user profiles found. Create one with the run command using --user-profile."
        )
        raise typer.Exit(code=2)
    for p in profs:
        typer.echo(f"- name: {p.name}")
        typer.echo(f"  path: {p.path}")
        # Secrets are sensitive; only show whether linked
        settings = load_user_settings(p)
        gd_user = p.secrets.google_drive_user or "(not linked)"
        typer.echo(f"  google_drive: {gd_user}")
        typer.echo(f"  name: {settings.human_name}")
        typer.echo("")


@app.command()
def list_users() -> None:
    """List user profile names available."""
    profs = discover_user_profiles()
    if not profs:
        typer.echo("No user profiles found.")
        raise typer.Exit(code=0)
    for p in profs:
        settings = load_user_settings(p)
        gd_user = p.secrets.google_drive_user or "(not linked)"
        typer.echo(f"- {p.name}  |  human: {settings.human_name}  |  google: {gd_user}")


@app.command()
def create_user(
    user_profile: str = typer.Argument(..., help="New user profile folder name"),
):
    """Create a new user profile and prompt for human name."""
    try:
        p = create_user_profile(user_profile)
    except ValueError as e:
        typer.echo(str(e))
        raise typer.Exit(code=2)

    # Prompt for human name
    human = typer.prompt("Enter human name", default="Ben Mowery")
    settings = load_user_settings(p)
    settings.human_name = human
    save_user_settings(p, settings)

    typer.echo(f"✅ Created user profile '{user_profile}' at {p.path}")


@app.command()
def test_openai_key() -> None:
    """Test OpenAI API key with a simple query using GPT-4o-mini."""
    try:
        client = get_openai_client()
        typer.echo("✅ OpenAI API key loaded successfully!")
        
        # Test with a simple query
        typer.echo("🤖 Testing GPT-4o-mini with a simple query...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Keep responses brief and friendly."},
                {"role": "user", "content": "Say 'Hello from WebBot!' and tell me one interesting fact about browser automation."}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        if response.choices and response.choices[0].message.content:
            typer.echo("✅ API call successful!")
            typer.echo(f"🤖 Response: {response.choices[0].message.content}")
        else:
            typer.echo("❌ No response content received")
            
    except Exception as e:
        typer.echo(f"❌ OpenAI API test failed: {e}")
        raise typer.Exit(code=1)


def _resolve_browser_profile(name_or_dir: Optional[str]) -> BrowserProfile:
    if name_or_dir:
        p = find_browser_profile_by_name_or_dir(name_or_dir)
        if not p:
            typer.echo(
                f"Browser profile '{name_or_dir}' not found. Use `list-browser-profiles` to see options."
            )
            raise typer.Exit(code=2)
        return p
    # default to the first discovered default, else first one
    profs = discover_browser_profiles()
    if not profs:
        typer.echo("No Chrome browser profiles found.")
        raise typer.Exit(code=2)
    for p in profs:
        if p.is_default:
            return p
    return profs[0]


def _resolve_user_profile(name: str) -> UserProfile:
    p = find_user_profile_by_name(name)
    if not p:
        typer.echo(
            f"User profile '{name}' not found. It will be created automatically."
        )
        # Import here to avoid circular imports
        from .user_profiles import create_user_profile
        try:
            p = create_user_profile(name)
            typer.echo(f"✅ Created new user profile '{name}' at {p.path}")
        except Exception as e:
            typer.echo(f"❌ Failed to create user profile: {e}")
            raise typer.Exit(code=1)
    return p


@app.command("google-drive-login")
def google_drive_login_cmd(
    user_profile: str = typer.Argument(..., help="User profile name to link to Google Drive"),
    client_secret: Optional[Path] = typer.Option(
        None,
        "--client-secret",
        help="Path to Google OAuth client JSON. If omitted, env vars and common paths are tried.",
    ),
):
    """Interactive Google Drive login and link to the specified user profile."""
    profile = _resolve_user_profile(user_profile)
    try:
        google_drive_login(profile, client_secret_path=client_secret)
        typer.echo("✅ Google Drive linked successfully!")
    except Exception as e:
        typer.echo(f"❌ Google Drive login failed: {e}")
        raise typer.Exit(code=1)


@app.command()
def sync_resumes(
    user_profile: str = typer.Argument(..., help="User profile name to sync resumes for"),
):
    """Sync resumes from Google Drive to the local user profile directory."""
    profile = _resolve_user_profile(user_profile)
    try:
        count = refresh_resumes(profile)
        if count > 0:
            typer.echo(f"✅ Resumes synced successfully! ({count} found)")
        else:
            typer.echo("⚠️  No matching resumes found.")
            typer.echo("   Tip: Update google_drive_resume_path in settings.json, e.g., 'J/Resumes'.")
            typer.echo("   We searched globally for [AP]* resumes containing 'Resume' and your human name.")
    except Exception as e:
        typer.echo(f"❌ Resume sync failed: {e}")
        raise typer.Exit(code=1)


@app.command()
def run(
    user_profile: str = typer.Argument(
        ...,
        help="User profile name (e.g., 'JohnDoe', 'WorkAccount'). Will be created if it doesn't exist.",
    ),
    use_browser_profile: Optional[str] = typer.Option(
        None,
        "--use-browser-profile",
        help="Chrome browser profile name or dir (e.g., 'Default', 'Profile 1').",
    ),
    initial_job_url: Optional[str] = typer.Option(
        None,
        "--initial-job-url",
        help="URL to a job page for first-pass extraction & apply-link discovery.",
    ),
    ai_mode: AIMode = typer.Option(
        AIMode.OPEN_AI,
        "--ai-mode",
        help="AI mode for structured extraction: OPEN_AI (default) or LLM_OFF for heuristics only.",
    ),
):
    """
    Intelligently launch Chrome: attach to existing instance if possible, otherwise launch new instance with chosen profile.
    Optionally visit a job page, extract structured data, and attempt to locate a direct 'applyable' URL using agentic AI.
    """
    # Resolve both profiles
    browser_profile = _resolve_browser_profile(use_browser_profile)
    user_profile_obj = _resolve_user_profile(user_profile)
    
    typer.echo(f"👤 Using user profile: {user_profile_obj.name} ({user_profile_obj.path})")
    typer.echo(f"🌐 Using browser profile: {browser_profile.name}")

    async def main():
        try:
            ctx, page = await smart_launch_with_profile(browser_profile, headless=False)
            
            # Check if we're using an existing instance or new one
            if hasattr(page, '_playwright'):
                typer.echo("✅ Attached to existing Chrome instance!")
            else:
                typer.echo(f"✅ Launched new Chrome instance with profile '{browser_profile.name}'")
            
            if initial_job_url:
                await goto_and_wait(page, initial_job_url)
                text = await extract_visible_text(page)
                typer.echo("===== Page Text (truncated to 4000 chars) =====")
                typer.echo(text[:4000])
                typer.echo("===== End Page Text =====\n")

                # Extract structured data from the page
                try:
                    extract = await parse_job_page(page, mode=ai_mode)
                    _pretty_print_extract(extract)
                except OpenAIConfigError as e:
                    typer.echo(f"⚠️  AI mode requested but OpenAI not configured: {e}")
                    typer.echo("Falling back to heuristic extraction...")
                    extract = await parse_job_page(page, mode=AIMode.LLM_OFF)
                    _pretty_print_extract(extract)
                except Exception as e:
                    typer.echo(f"❌ Error during structured extraction: {e}")

                # Decide whether to search for an external "apply" page
                dna = load_do_not_apply_domains()
                host = domain(initial_job_url)
                if host in dna:
                    typer.echo(
                        f"'{host}' is in do-not-apply list. Searching for company careers/apply page..."
                    )
                    
                    # Use extracted company name and job title for better search
                    company_name = extract.company_name or "Unknown Company"
                    job_title = extract.title or "Unknown Position"
                    
                    typer.echo(f"🔍 Searching for apply URL for: {company_name} - {job_title}")
                    
                    # Agentic approach (default) - use LLM to find the best apply URL
                    try:
                        typer.echo("\n🤖 Using agentic AI approach...")
                        agentic_url, agentic_trace = await smart_find_apply_url(
                            page, company_name=company_name, job_title=job_title
                        )
                        
                        # Print LLM prompts and responses with colored separators
                        typer.echo("\n" + "🔵"*20 + " AGENTIC AI PROMPT " + "🔵"*20)
                        typer.echo(agentic_trace["prompt"])
                        typer.echo("\n" + "🟢"*20 + " AGENTIC AI RESPONSE " + "🟢"*20)
                        typer.echo(agentic_trace["response"])
                        typer.echo("\n" + "🟡"*20 + " AGENTIC AI PICKS " + "🟡"*20)
                        for key, value in agentic_trace["picks"].items():
                            typer.echo(f"  {key}: {value}")
                        
                        if agentic_url:
                            typer.echo(f"\n✅ Agentic AI found apply URL: {agentic_url}")
                        else:
                            typer.echo("\n❌ Agentic AI found no apply URL")
                            
                    except Exception as e:
                        typer.echo(f"❌ Agentic AI approach failed: {e}")
                        agentic_url = None
                    
                    # Legacy approach for comparison
                    try:
                        typer.echo("\n🔍 Using legacy heuristic approach...")
                        company_home = await find_company_homepage_from_job_page(page)
                        title_txt = (await page.title()) or ""
                        company_dom = domain(company_home) if company_home else None
                        legacy_url = await find_apply_url(
                            page, company_name, title_txt, company_dom
                        )
                        
                        if legacy_url:
                            typer.echo(f"✅ Legacy approach found apply URL: {legacy_url}")
                        else:
                            typer.echo("❌ Legacy approach found no apply URL")
                            
                    except Exception as e:
                        typer.echo(f"❌ Legacy approach failed: {e}")
                        legacy_url = None
                    
                    # Compare results
                    typer.echo("\n" + "🔄"*20 + " COMPARISON " + "🔄"*20)
                    typer.echo(f"Agentic AI:  {agentic_url or 'None'}")
                    typer.echo(f"Legacy:      {legacy_url or 'None'}")
                    
                    if agentic_url and legacy_url:
                        if agentic_url == legacy_url:
                            typer.echo("✅ Both approaches found the same URL!")
                        else:
                            typer.echo("⚠️  Approaches found different URLs")
                    elif agentic_url:
                        typer.echo("✅ Only agentic AI found a URL")
                    elif legacy_url:
                        typer.echo("✅ Only legacy approach found a URL")
                    else:
                        typer.echo("❌ Neither approach found a URL")
                        
                else:
                    typer.echo(
                        f"Host '{host}' is not in do-not-apply list. (Add it to data/do-not-apply.txt to exclude.)"
                    )
        except Exception as e:
            typer.echo(f"❌ Error: {e}")
            raise typer.Exit(code=1)
        finally:
            # Clean up based on how we launched
            if hasattr(page, '_playwright'):
                # We attached to existing Chrome, just close the page
                await page.close()
            else:
                # We launched new instance, close the context
                await ctx.close()

    asyncio.run(main())


@app.command("apply-flow")
def apply_flow(
    initial_job_url: str = typer.Argument(..., help="Starting URL (job post or company page)"),
    user_profile: str = typer.Option("user_ben", "--user-profile", help="User profile for resumes and settings"),
    use_browser_profile: Optional[str] = typer.Option(
        None,
        "--use-browser-profile",
        help="Chrome browser profile name or dir (e.g., 'Default', 'Profile 1').",
    ),
    headless: bool = typer.Option(False, "--headless/--no-headless", help="Run in headless mode"),
    ignore_optional: bool = typer.Option(True, "--ignore-optional/--no-ignore-optional"),
    model: str = typer.Option("gpt-4o", "--model", help="Model for answer generation and resume selection"),
    hold_seconds: int = typer.Option(45, "--hold-seconds", help="Seconds to keep browser open for manual review"),
):
    """
    End-to-end application flow in one command:
    1) Launch/attach Chrome with selected browser profile
    2) Open the starting URL and extract job context
    3) Find an applyable URL (Agentic AI + legacy DuckDuckGo comparison)
    4) Navigate to the application form (or click Apply heuristically)
    5) Extract form schema, select best resume, generate LLM answers
    6) Fill the form and upload resume (no submit)
    """

    browser_profile = _resolve_browser_profile(use_browser_profile)
    user_profile_obj = _resolve_user_profile(user_profile)

    async def _heuristic_click_apply(page):
        import re as _re
        # Try role=button/link with accessible name containing 'apply'
        for role in ("button", "link"):
            try:
                loc = page.get_by_role(role, name=_re.compile(r"apply|submit application", _re.I))
                if await loc.count() > 0:
                    await loc.first.scroll_into_view_if_needed()
                    await loc.first.click()
                    return True
            except Exception:
                pass
        # Fallback: visible text
        try:
            loc = page.locator(":text-matches('^\\s*(Apply|Apply now|Apply for this job|Submit application)\\b', 'i')")
            if await loc.count() > 0:
                await loc.first.scroll_into_view_if_needed()
                await loc.first.click()
                return True
        except Exception:
            pass
        return False

    async def main():
        ctx, page = await smart_launch_with_profile(browser_profile, headless=headless)
        try:
            await goto_and_wait(page, initial_job_url)
            try:
                await page.wait_for_load_state(state="networkidle", timeout=20000)
            except Exception:
                pass

            # Extract job context from live DOM
            try:
                initial_text = await extract_visible_text(page)
            except Exception:
                initial_text = ""

            # Structured extract for company/title
            try:
                extract = await parse_job_page(page, mode=AIMode.OPEN_AI)
                _pretty_print_extract(extract)
            except OpenAIConfigError:
                extract = await parse_job_page(page, mode=AIMode.LLM_OFF)
                _pretty_print_extract(extract)
            except Exception:
                extract = None

            company_name = (extract.company_name if extract else None) or "Unknown Company"
            job_title = (extract.title if extract else None) or (await page.title() or "Unknown Role")

            # Find apply URL using both methods (agentic vs legacy) and compare
            agentic_url = None
            legacy_url = None
            try:
                typer.echo("\n🤖 Using agentic AI approach to find apply URL...")
                agentic_url, agentic_trace = await smart_find_apply_url(page, company_name=company_name, job_title=job_title)
                typer.echo("\n" + "🔵"*20 + " AGENTIC AI PROMPT " + "🔵"*20)
                typer.echo(agentic_trace.get("prompt") or "")
                typer.echo("\n" + "🟢"*20 + " AGENTIC AI RESPONSE " + "🟢"*20)
                typer.echo(agentic_trace.get("response") or "")
                typer.echo("\n" + "🟡"*20 + " AGENTIC AI PICKS " + "🟡"*20)
                for k, v in (agentic_trace.get("picks") or {}).items():
                    typer.echo(f"  {k}: {v}")
                if agentic_url:
                    typer.echo(f"\n✅ Agentic AI found apply URL: {agentic_url}")
                else:
                    typer.echo("\n❌ Agentic AI found no apply URL")
            except Exception as e:
                typer.echo(f"❌ Agentic AI approach failed: {e}")

            try:
                typer.echo("\n🔍 Using legacy heuristic DuckDuckGo approach...")
                company_home = await find_company_homepage_from_job_page(page)
                title_txt = (await page.title()) or ""
                company_dom = domain(company_home) if company_home else None
                legacy_url = await find_apply_url(page, company_name, title_txt, company_dom)
                if legacy_url:
                    typer.echo(f"✅ Legacy approach found apply URL: {legacy_url}")
                else:
                    typer.echo("❌ Legacy approach found no apply URL")
            except Exception as e:
                typer.echo(f"❌ Legacy approach failed: {e}")

            typer.echo("\n" + "🔄"*20 + " COMPARISON " + "🔄"*20)
            typer.echo(f"Agentic AI:  {agentic_url or 'None'}")
            typer.echo(f"Legacy:      {legacy_url or 'None'}")

            chosen_apply_url = agentic_url or legacy_url

            # Navigate to the application form
            if chosen_apply_url:
                await goto_and_wait(page, chosen_apply_url)
                try:
                    await page.wait_for_load_state(state="networkidle", timeout=20000)
                except Exception:
                    pass
            else:
                clicked = await _heuristic_click_apply(page)
                if not clicked:
                    typer.echo("⚠️  No 'Apply' control found via heuristics; staying on current page.")
                try:
                    await page.wait_for_load_state(state="networkidle", timeout=20000)
                except Exception:
                    pass

            # Extract form schema from the live form page
            schema = await extract_form_schema_from_page(page, url=page.url)
            typer.echo("[apply-flow] Extracted schema; selecting best resume and generating answers...")

            # Select best resume for this job using live job description text
            try:
                alignment, align_trace = select_best_resume_for_job_description(
                    profile=user_profile_obj, job_description_text=initial_text or (await page.title() or ""), model=model
                )
                typer.echo("\n" + "🔵"*20 + " RESUME ALIGNMENT PROMPT " + "🔵"*20)
                typer.echo(align_trace.get("prompt") or "")
                typer.echo("\n" + "🟢"*20 + " RESUME ALIGNMENT RESPONSE " + "🟢"*20)
                typer.echo(align_trace.get("response") or "")
                chosen_resume_id = alignment.chosen_resume_id
            except Exception as e:
                typer.echo(f"⚠️ Resume alignment failed: {e}. Proceeding with best available resume text.")
                chosen_resume_id = None

            # Load chosen resume text/pdf paths
            from pathlib import Path as _P
            chosen_resume_txt = ""
            preferred_pdf_path: Optional[_P] = None
            try:
                import json as _json
                idx_path = user_profile_obj.path / "resumes.json"
                if idx_path.exists():
                    idx = _json.loads(idx_path.read_text(encoding="utf-8"))
                    for itm in idx.get("resumes", []):
                        if not chosen_resume_id or itm.get("id") == chosen_resume_id:
                            txt_p = itm.get("txt_path")
                            pdf_p = itm.get("pdf_path")
                            if txt_p and _P(txt_p).exists():
                                chosen_resume_txt = _P(txt_p).read_text(encoding="utf-8")
                            if pdf_p and _P(pdf_p).exists():
                                preferred_pdf_path = _P(pdf_p)
                            if chosen_resume_id:
                                break
            except Exception:
                pass
            if not chosen_resume_txt:
                # Fallback: read all available resume.txt under profile
                try:
                    import glob
                    txts = []
                    for p in glob.glob(str(user_profile_obj.path / "**/resume_pdf/**/resume.txt"), recursive=True):
                        try:
                            txts.append(_P(p).read_text(encoding="utf-8"))
                        except Exception:
                            pass
                    chosen_resume_txt = "\n\n".join(txts)[:20000]
                except Exception:
                    chosen_resume_txt = ""

            # Generate answers with resume + context
            answered_schema = generate_answers(
                schema,
                resume_text=chosen_resume_txt,
                job_context=f"URL: {page.url}",
                ignore_optional=ignore_optional,
                model=model,
            )

            # Execute fill plan (no submit)
            await execute_fill_plan(
                page,
                answered_schema,
                user_profile_obj.path,
                wait_seconds=hold_seconds,
                preferred_resume_pdf=preferred_pdf_path,
            )

        finally:
            if hasattr(page, '_playwright'):
                await page.close()
            else:
                await ctx.close()

    asyncio.run(main())

@app.command("snapshot-url")
def snapshot_url(
    url: str = typer.Argument(..., help="URL to snapshot for fixture generation"),
    use_browser_profile: Optional[str] = typer.Option(
        None,
        "--use-browser-profile",
        help="Chrome browser profile name or dir (e.g., 'Default', 'Profile 1').",
    ),
    out_dir: Optional[Path] = typer.Option(
        None,
        "--out-dir",
        help="Directory to write snapshot artifacts. Defaults to repo_root()/snapshots/<domain>-<ts>",
    ),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="Run in headless mode"),
    wait_selector: Optional[str] = typer.Option(
        None,
        "--wait-selector",
        help="Optional CSS selector to wait for before snapshot (e.g., input[type='file'])",
    ),
):
    """
    Visit a URL and save an on-disk snapshot (HTML + screenshot). Use this to
    collect real-world pages to drive tests.
    """
    from .config import repo_root
    import datetime as _dt

    browser_profile = _resolve_browser_profile(use_browser_profile)

    async def main():
        ctx, page = await smart_launch_with_profile(browser_profile, headless=headless)
        try:
            await goto_and_wait(page, url)
            # Give dynamic apps time to hydrate
            try:
                await page.wait_for_load_state(state="networkidle", timeout=20000)
            except Exception:
                pass
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=20000)
                except Exception:
                    pass

            # Determine output directory
            base = out_dir or (repo_root() / "snapshots")
            base.mkdir(parents=True, exist_ok=True)
            ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            import tldextract as _tld

            d = _tld.extract(url)
            dom = ".".join([p for p in [d.domain, d.suffix] if p]) or "page"
            dest = base / f"{dom}-{ts}"

            art = await snapshot_page(page, dest, with_screenshot=True)
            typer.echo(f"✅ Snapshot saved to {art.out_dir}")
            typer.echo(f"   HTML: {art.html_path}")
            if art.screenshot_path:
                typer.echo(f"   Screenshot: {art.screenshot_path}")
            typer.echo(f"   Frames: {len(art.frames)}")
        finally:
            if hasattr(page, '_playwright'):
                await page.close()
            else:
                await ctx.close()

    try:
        asyncio.run(main())
    except Exception as e:
        typer.echo(f"❌ Snapshot failed: {e}")
        raise typer.Exit(code=1)


@app.command("download-test-url")
def download_test_url(
    url: str = typer.Argument(..., help="URL to snapshot into tests/fixtures/realworld"),
    use_browser_profile: Optional[str] = typer.Option(
        None,
        "--use-browser-profile",
        help="Chrome browser profile name or dir (e.g., 'Default', 'Profile 1').",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        help="Folder name under tests/fixtures/realworld to save into. Defaults to <domain>-<lastpath>",
    ),
    click_apply: bool = typer.Option(
        False,
        "--click-apply/--no-click-apply",
        help="Attempt to click an 'Apply' button and snapshot the resulting form view as well.",
    ),
    apply_selector: Optional[str] = typer.Option(
        None,
        "--apply-selector",
        help="Optional CSS selector to click instead of heuristic detection.",
    ),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="Run in headless mode"),
    wait_selector: Optional[str] = typer.Option(
        None,
        "--wait-selector",
        help="Optional CSS selector to wait for before initial snapshot.",
    ),
    manual_after_apply: bool = typer.Option(
        False,
        "--manual-after-apply/--no-manual-after-apply",
        help="If set with --no-headless, allows user to click Apply manually; press Enter to capture after_apply.",
    ),
    manual_after_apply_delay: Optional[int] = typer.Option(
        None,
        "--manual-after-apply-delay",
        help="Optional seconds to wait in manual mode before capturing after_apply (skips Enter).",
    ),
):
    """
    Snapshot a page into tests/fixtures/realworld/<name>/ as HTML and screenshot.
    Optionally click an 'Apply' button (heuristic or selector) and take a second snapshot.
    """
    from .config import repo_root
    import re as _re
    import tldextract as _tld
    from pathlib import Path as _P

    browser_profile = _resolve_browser_profile(use_browser_profile)

    async def _heuristic_click_apply(page):
        # If a CSS selector override was provided, try a sequence of click strategies
        if apply_selector:
            candidates = [
                apply_selector,
                f"{apply_selector} >> nth=0",
                "a:has(button:has-text('Apply'))",
                "button:has-text('Apply')",
                "a:has-text('Apply')",
                "button:has-text('Apply for this Job')",
                "a:has-text('Apply for this Job')",
            ]
            for sel in candidates:
                try:
                    await page.wait_for_selector(sel, timeout=5000)
                except Exception:
                    # keep trying other candidates
                    continue
                loc = page.locator(sel)
                # Attempt to reveal by scrolling
                if await loc.count() == 0:
                    try:
                        for _ in range(8):
                            await page.mouse.wheel(0, 1800)
                            await page.wait_for_timeout(200)
                            if await loc.count() > 0:
                                break
                    except Exception:
                        pass
                if await loc.count() == 0:
                    continue
                # Try normal click
                try:
                    await loc.first.scroll_into_view_if_needed()
                except Exception:
                    pass
                try:
                    await loc.first.click()
                    return True
                except Exception:
                    # Try JS click
                    try:
                        clicked = await page.evaluate(
                            "(sel) => {\n"
                            "  const el = document.querySelector(sel);\n"
                            "  if (!el) return false;\n"
                            "  const a = el.closest('a') || (el.tagName === 'A' ? el : null);\n"
                            "  (a || el).scrollIntoView({block: 'center'});\n"
                            "  (a || el).click();\n"
                            "  return true;\n"
                            "}",
                            sel,
                        )
                        if clicked:
                            try:
                                await page.wait_for_load_state(state="networkidle", timeout=20000)
                            except Exception:
                                pass
                            return True
                    except Exception:
                        # Try focusing and pressing Enter
                        try:
                            await loc.first.focus()
                            await page.keyboard.press("Enter")
                            return True
                        except Exception:
                            continue
        # Try role=button/link with accessible name containing 'apply'
        for role in ("button", "link"):
            try:
                loc = page.get_by_role(role, name=_re.compile(r"apply|submit application", _re.I))
                if await loc.count() > 0:
                    await loc.first.scroll_into_view_if_needed()
                    await loc.first.click()
                    return True
            except Exception:
                pass
        # Fallback: visible text
        try:
            loc = page.locator(":text-matches('^\\s*(Apply|Apply now|Apply for this job|Submit application)\\b', 'i')")
            if await loc.count() > 0:
                await loc.first.scroll_into_view_if_needed()
                await loc.first.click()
                return True
        except Exception:
            pass
        return False

    async def main():
        ctx, page = await smart_launch_with_profile(browser_profile, headless=headless)
        try:
            await goto_and_wait(page, url)
            try:
                await page.wait_for_load_state(state="networkidle", timeout=20000)
            except Exception:
                pass
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=20000)
                except Exception:
                    pass

            d = _tld.extract(url)
            dom = ".".join([p for p in [d.domain, d.suffix] if p]) or "page"
            # derive a short path suffix for naming
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                tail = parsed.path.rstrip("/").split("/")[-1] or "root"
            except Exception:
                tail = "page"

            folder = name or f"{dom}-{tail}"
            base = repo_root() / "tests" / "fixtures" / "realworld" / folder
            base.mkdir(parents=True, exist_ok=True)

            # Snapshot initial view
            initial_dir = base / "initial"
            art1 = await snapshot_page(page, initial_dir, with_screenshot=True)
            typer.echo(f"✅ Initial snapshot saved: {art1.out_dir}")

            if click_apply or manual_after_apply:
                if manual_after_apply and not headless:
                    if manual_after_apply_delay and manual_after_apply_delay > 0:
                        typer.echo(
                            f"⏳ Manual mode: Click Apply in the browser. Auto-capturing after_apply in {manual_after_apply_delay}s..."
                        )
                        await asyncio.sleep(manual_after_apply_delay)
                    else:
                        typer.echo(
                            "⏳ Manual mode: Please click the Apply button in the browser, then press Enter here to capture after_apply..."
                        )
                        try:
                            input()
                        except EOFError:
                            pass
                else:
                    clicked = await _heuristic_click_apply(page)
                    if not clicked:
                        typer.echo("⚠️  No 'Apply' control found via heuristics.")
                # Give the page a moment to render dynamic forms/tabs
                try:
                    await page.wait_for_load_state(state="networkidle", timeout=20000)
                except Exception:
                    pass
                after_dir = base / "after_apply"
                art2 = await snapshot_page(page, after_dir, with_screenshot=True)
                typer.echo(f"✅ After-apply snapshot saved: {art2.out_dir}")
        finally:
            if hasattr(page, '_playwright'):
                await page.close()
            else:
                await ctx.close()

    try:
        asyncio.run(main())
    except Exception as e:
        typer.echo(f"❌ Download failed: {e}")
        raise typer.Exit(code=1)


@app.command("extract-form-from-snapshot")
def extract_form_from_snapshot(
    snapshot_dir: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, readable=True),
):
    """Extract and pretty-print form schema from a saved snapshot directory."""
    async def main():
        try:
            schema = await extract_form_schema_from_snapshot_dir(snapshot_dir)
        except Exception as e:
            typer.echo(f"❌ Extraction failed: {e}")
            raise typer.Exit(code=1)
        import json

        typer.echo(json.dumps(schema.model_dump(), indent=2))

    asyncio.run(main())


@app.command("answer-form-from-snapshot")
def answer_form_from_snapshot(
    snapshot_dir: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, readable=True),
    user_profile: str = typer.Option("user_ben", "--user-profile", help="User profile for resume selection"),
    ignore_optional: bool = typer.Option(True, "--ignore-optional/--no-ignore-optional"),
    model: str = typer.Option("gpt-4o", "--model"),
):
    """Extract a form schema from a saved snapshot, generate LLM answers using the user's resumes, and print key Q&A pairs."""
    import json as _json
    from .resume_alignment import run_alignment_for_files

    profile = _resolve_user_profile(user_profile)
    job_desc_path = repo_root() / "data/test_job_desc1.txt"

    async def main():
        # Extract schema from snapshot
        schema = await extract_form_schema_from_snapshot_dir(snapshot_dir)

        # Pick best resume for the provided job description (existing flow)
        try:
            alignment, trace = run_alignment_for_files(profile=profile, job_desc_path=job_desc_path, model="gpt-4o")
            chosen_resume_txt = ""
            # Find chosen resume txt from user profile's resumes.json (already handled in alignment module)
            # We don't have a direct path here; fallback: read all resume txts under the profile and concatenate
            # or just use the alignment trace response as high-level context if needed.
        except Exception as e:
            typer.echo(f"⚠️ Resume alignment failed: {e}. Proceeding with empty resume context.")
            alignment = None
            chosen_resume_txt = ""

        # If we can't pull the chosen resume text via alignment module, fallback to any available resume.txt under the profile
        if not chosen_resume_txt:
            try:
                import glob
                txts = []
                for p in glob.glob(str(profile.path / "**/resume_pdf/**/resume.txt"), recursive=True):
                    try:
                        txts.append(Path(p).read_text(encoding="utf-8"))
                    except Exception:
                        pass
                chosen_resume_txt = "\n\n".join(txts)[:20000]
            except Exception:
                chosen_resume_txt = ""

        # Build a minimal job context from snapshot manifest URL
        try:
            from .forms.snapshot_loader import load_snapshot_manifest
            man = load_snapshot_manifest(snapshot_dir)
            job_context = f"Form URL: {man.url}"
        except Exception:
            job_context = None

        # Generate answers
        answered = generate_answers(
            schema,
            resume_text=chosen_resume_txt,
            job_context=job_context,
            ignore_optional=ignore_optional,
            model=model,
        )

        # Print key questions and answers
        pairs = []
        for s in answered.sections:
            for f in s.fields:
                label = f.label or f.name or f.field_id
                ans = f.meta.get("answer") if isinstance(f.meta, dict) else None
                if ans:
                    pairs.append({"id": f.field_id, "label": label, "type": f.type, "answer": ans})

        typer.echo(_json.dumps({
            "url": job_context,
            "valid": answered.validity.is_valid_job_application_form,
            "qa": pairs,
        }, indent=2))

    asyncio.run(main())


@app.command("answer-realworld-fixtures")
def answer_realworld_fixtures(
    user_profile: str = typer.Option("user_ben", "--user-profile", help="User profile for resume selection"),
    base_dir: Path = typer.Option(
        Path("tests/fixtures/realworld"),
        "--base-dir",
        help="Base directory of realworld fixtures",
    ),
    model: str = typer.Option("gpt-4o", "--model"),
    ignore_optional: bool = typer.Option(True, "--ignore-optional/--no-ignore-optional"),
):
    """Iterate each realworld fixture folder, load its initial/after_apply snapshots when present, generate answers, and print key Q&A."""
    import json as _json
    from .forms.snapshot_loader import load_snapshot_manifest
    from .resume_alignment import run_alignment_for_files

    profile = _resolve_user_profile(user_profile)
    job_desc_path = repo_root() / "data/test_job_desc1.txt"

    async def main():
        results: list[dict] = []

        # Precompute resume text once
        chosen_resume_txt = ""
        try:
            alignment, trace = run_alignment_for_files(profile=profile, job_desc_path=job_desc_path, model="gpt-4o")
        except Exception:
            alignment = None
        if not chosen_resume_txt:
            try:
                import glob
                txts = []
                for p in glob.glob(str(profile.path / "**/resume_pdf/**/resume.txt"), recursive=True):
                    try:
                        txts.append(Path(p).read_text(encoding="utf-8"))
                    except Exception:
                        pass
                chosen_resume_txt = "\n\n".join(txts)[:20000]
            except Exception:
                chosen_resume_txt = ""

        # Iterate folders under base_dir
        if not base_dir.exists():
            typer.echo(f"⚠️ Base dir not found: {base_dir}")
            raise typer.Exit(code=2)

        for folder in sorted([p for p in base_dir.iterdir() if p.is_dir()]):
            for phase in ("after_apply", "initial"):
                snap = folder / phase
                if not snap.exists():
                    continue
                try:
                    schema = await extract_form_schema_from_snapshot_dir(snap)
                    man = load_snapshot_manifest(snap)
                    answered = generate_answers(
                        schema,
                        resume_text=chosen_resume_txt,
                        job_context=f"Fixture: {folder.name} | Phase: {phase} | URL: {man.url}",
                        ignore_optional=ignore_optional,
                        model=model,
                    )
                    qa = []
                    for s in answered.sections:
                        for f in s.fields:
                            label = f.label or f.name or f.field_id
                            ans = f.meta.get("answer") if isinstance(f.meta, dict) else None
                            if ans:
                                qa.append({"id": f.field_id, "label": label, "type": f.type, "answer": ans})
                    results.append({
                        "fixture": folder.name,
                        "phase": phase,
                        "url": man.url,
                        "valid": answered.validity.is_valid_job_application_form,
                        "qa": qa,
                    })
                except Exception as e:
                    results.append({"fixture": folder.name, "phase": phase, "error": str(e)})

        typer.echo(_json.dumps(results, indent=2))

    asyncio.run(main())

@app.command("execute-form-url")
def execute_form_url(
    url: str = typer.Argument(..., help="URL of the application form page to execute (no submit)"),
    user_profile: str = typer.Option("user_ben", "--user-profile", help="User profile to pick resumes from"),
    use_browser_profile: Optional[str] = typer.Option(
        None,
        "--use-browser-profile",
        help="Chrome browser profile name or dir (e.g., 'Default', 'Profile 1').",
    ),
    headless: bool = typer.Option(False, "--headless/--no-headless", help="Run in headless mode"),
    wait_selector: Optional[str] = typer.Option(
        None,
        "--wait-selector",
        help="Optional CSS selector to wait for before executing (e.g., input[type='file'])",
    ),
    hold_seconds: int = typer.Option(60, "--hold-seconds", help="Seconds to keep browser open for manual review"),
):
    """Open a browser, navigate to URL, extract schema, and fill answers + upload resume; do not submit."""
    browser_profile = _resolve_browser_profile(use_browser_profile)
    prof = find_user_profile_by_name(user_profile)
    if not prof:
        typer.echo(f"❌ User profile not found: {user_profile}")
        raise typer.Exit(code=2)

    async def main():
        ctx, page = await smart_launch_with_profile(browser_profile, headless=headless)
        try:
            await goto_and_wait(page, url)
            try:
                await page.wait_for_load_state(state="networkidle", timeout=20000)
            except Exception:
                pass
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=20000)
                except Exception:
                    pass
            schema = await extract_form_schema_from_page(page, url=url)
            typer.echo("[cli] Extracted schema; generating demo answers...")
            # Hardcode simple answers into meta.answer for demo
            for section in schema.sections:
                for f in section.fields:
                    if f.type in {"text", "email", "tel"}:
                        f.meta["answer"] = "Test Value"
                    elif f.type == "textarea":
                        f.meta["answer"] = "This is a test answer for validation."
                    elif f.type == "select":
                        f.meta["answer"] = "yes"
                    elif f.type == "checkbox":
                        # randomly select ~30% of checkboxes
                        import random as _r
                        f.meta["answer"] = "true" if _r.random() < 0.3 else "false"
                    elif f.type == "radio":
                        f.meta["answer"] = "true"
            # Print a compact summary of planned answers
            checks = [ (f.label or f.name or f.field_id, f.meta.get("answer")) for s in schema.sections for f in s.fields if f.type == "checkbox" ]
            texts  = [ (f.label or f.name or f.field_id, f.meta.get("answer")) for s in schema.sections for f in s.fields if f.type in {"text","email","tel","textarea"} ]
            typer.echo(f"[cli] Text fields to fill: {len(texts)}; Checkboxes planned true: {sum(1 for _,v in checks if v=='true')} of {len(checks)}")
            await execute_fill_plan(page, schema, prof.path, wait_seconds=hold_seconds)
        finally:
            if hasattr(page, '_playwright'):
                await page.close()
            else:
                await ctx.close()

    asyncio.run(main())


@app.command("extract-form-url")
def extract_form_url(
    url: str = typer.Argument(..., help="URL of the application form page to extract"),
    use_browser_profile: Optional[str] = typer.Option(
        None,
        "--use-browser-profile",
        help="Chrome browser profile name or dir (e.g., 'Default', 'Profile 1').",
    ),
    headless: bool = typer.Option(False, "--headless/--no-headless", help="Run in headless mode"),
    wait_selector: Optional[str] = typer.Option(
        None,
        "--wait-selector",
        help="Optional CSS selector to wait for before extraction (e.g., input[type='file'])",
    ),
):
    """Open a browser, navigate to URL, extract form schema from live DOM, and print JSON."""
    browser_profile = _resolve_browser_profile(use_browser_profile)

    async def main():
        ctx, page = await smart_launch_with_profile(browser_profile, headless=headless)
        try:
            await goto_and_wait(page, url)
            try:
                await page.wait_for_load_state(state="networkidle", timeout=20000)
            except Exception:
                pass
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=20000)
                except Exception:
                    pass
            schema = await extract_form_schema_from_page(page, url=url)
            import json as _json
            typer.echo(_json.dumps(schema.model_dump(), indent=2))
        finally:
            if hasattr(page, '_playwright'):
                await page.close()
            else:
                await ctx.close()

    asyncio.run(main())

if __name__ == "__main__":
    app()
