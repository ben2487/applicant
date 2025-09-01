from __future__ import annotations
import asyncio
import typer
from typing import Optional
from .browser_profiles import discover_browser_profiles, find_browser_profile_by_name_or_dir, BrowserProfile
from .user_profiles import discover_user_profiles, find_user_profile_by_name, UserProfile
from .browser import smart_launch_with_profile, goto_and_wait
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

app = typer.Typer(add_completion=False, no_args_is_help=True)


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
        typer.echo(f"  has_google_drive: {p.secrets.google_drive_credentials is not None}")
        typer.echo("")


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


if __name__ == "__main__":
    app()
