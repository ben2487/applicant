from __future__ import annotations
import asyncio
import typer
from typing import Optional
from .profiles import discover_profiles, find_profile_by_name_or_dir, ChromeProfile
from .browser import smart_launch_with_profile, goto_and_wait
from .extract import extract_visible_text
from .apply_finder import (
    load_do_not_apply_domains,
    domain,
    find_company_homepage_from_job_page,
    find_apply_url,
)
from .ai_search import get_openai_client

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def list_browser_profiles() -> None:
    profs = discover_profiles()
    if not profs:
        typer.echo(
            "No Chrome profiles found. Make sure Chrome is installed and has been launched at least once."
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
def test_openai_key() -> None:
    """Test OpenAI API key with a simple query using GPT-5o-mini."""
    try:
        client = get_openai_client()
        typer.echo("✅ OpenAI API key loaded successfully!")
        
        # Test with a simple query
        typer.echo("🤖 Testing GPT-5o-mini with a simple query...")
        
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


def _resolve_profile(name_or_dir: Optional[str]) -> ChromeProfile:
    if name_or_dir:
        p = find_profile_by_name_or_dir(name_or_dir)
        if not p:
            typer.echo(
                f"Profile '{name_or_dir}' not found. Use `list-browser-profiles` to see options."
            )
            raise typer.Exit(code=2)
        return p
    # default to the first discovered default, else first one
    profs = discover_profiles()
    if not profs:
        typer.echo("No Chrome profiles found.")
        raise typer.Exit(code=2)
    for p in profs:
        if p.is_default:
            return p
    return profs[0]


@app.command()
def run(
    use_browser_profile: Optional[str] = typer.Option(
        None,
        "--use-browser-profile",
        help="Profile name or dir (e.g., 'Default', 'Profile 1').",
    ),
    initial_job_url: Optional[str] = typer.Option(
        None,
        "--initial-job-url",
        help="URL to a job page for first-pass extraction & apply-link discovery.",
    ),
):
    """
    Intelligently launch Chrome: attach to existing instance if possible, otherwise launch new instance with chosen profile.
    Optionally visit a job page, print text, and attempt to locate a direct 'applyable' URL.
    """
    profile = _resolve_profile(use_browser_profile)

    async def main():
        try:
            ctx, page = await smart_launch_with_profile(profile, headless=False)
            
            # Check if we're using an existing instance or new one
            if hasattr(page, '_playwright'):
                typer.echo("✅ Attached to existing Chrome instance!")
            else:
                typer.echo(f"✅ Launched new Chrome instance with profile '{profile.name}'")
            
            if initial_job_url:
                await goto_and_wait(page, initial_job_url)
                text = await extract_visible_text(page)
                typer.echo("===== Page Text (truncated to 4000 chars) =====")
                typer.echo(text[:4000])
                typer.echo("===== End Page Text =====\n")

                # Decide whether to search for an external "apply" page
                dna = load_do_not_apply_domains()
                host = domain(initial_job_url)
                if host in dna:
                    typer.echo(
                        f"'{host}' is in do-not-apply list. Searching for company careers/apply page..."
                    )
                    company_home = await find_company_homepage_from_job_page(page)
                    # Fallback: try to infer company name from <title> if homepage couldn't be derived
                    title_txt = (await page.title()) or ""
                    company_name = (
                        company_home.replace("https://", "")
                        if company_home
                        else title_txt.split(" – ")[0][:80]
                    )
                    company_dom = domain(company_home) if company_home else None
                    apply_url = await find_apply_url(
                        page, company_name, title_txt, company_dom
                    )
                    if apply_url:
                        typer.echo(f"Applyable URL candidate: {apply_url}")
                    else:
                        typer.echo(
                            "No applyable URL found via search. You can add custom rules later."
                        )
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
