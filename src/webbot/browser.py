from __future__ import annotations
from playwright.async_api import async_playwright, BrowserContext, Page
from .profiles import ChromeProfile
import asyncio


class BrowserLaunchError(RuntimeError): ...


async def try_attach_to_existing_chrome() -> tuple[BrowserContext, Page] | None:
    """Try to attach to an existing Chrome instance. Returns None if not possible."""
    try:
        # Try to connect to existing Chrome instance
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(
            channel="chrome",
            headless=False,
            args=["--remote-debugging-port=0"]  # Use any available port
        )
        
        # Connect to the browser
        context = await browser.new_context()
        page = await context.new_page()
        
        # Store the playwright instance for cleanup
        page._playwright = pw
        page._browser = browser
        
        return context, page
    except Exception:
        return None


async def smart_launch_with_profile(
    profile: ChromeProfile, *, headless: bool = False
) -> tuple[BrowserContext, Page]:
    """
    Intelligently launch Chrome: attach to existing instance if possible, 
    otherwise launch new instance with the specified profile.
    """
    # First, try to attach to existing Chrome
    existing = await try_attach_to_existing_chrome()
    if existing:
        return existing
    
    # If attachment failed, launch new instance with profile
    if not profile.user_data_root.exists():
        raise BrowserLaunchError(f"User data root not found: {profile.user_data_root}")
    if not profile.path.exists():
        raise BrowserLaunchError(f"Profile path not found: {profile.path}")

    pw = await async_playwright().start()
    try:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(profile.user_data_root),
            channel="chrome",
            headless=headless,
            args=[f"--profile-directory={profile.dir_name}"],  # pick specific profile
        )
        page = await ctx.new_page()
        return ctx, page
    except Exception as e:
        await pw.stop()
        raise BrowserLaunchError(
            f"Failed to launch Chrome with profile '{profile.dir_name}'. "
            "If Chrome is already running with this profile, close it and try again."
        ) from e


async def launch_with_profile(
    profile: ChromeProfile, *, headless: bool = False
) -> tuple[BrowserContext, Page]:
    # Using Chrome channel + persistent context. user_data_dir is the *root*; profile chosen via arg.
    if not profile.user_data_root.exists():
        raise BrowserLaunchError(f"User data root not found: {profile.user_data_root}")
    if not profile.path.exists():
        raise BrowserLaunchError(f"Profile path not found: {profile.path}")

    pw = await async_playwright().start()
    try:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(profile.user_data_root),
            channel="chrome",
            headless=headless,
            args=[f"--profile-directory={profile.dir_name}"],  # pick specific profile
        )
        page = await ctx.new_page()
        return ctx, page
    except Exception as e:
        await pw.stop()
        raise BrowserLaunchError(
            f"Failed to launch Chrome with profile '{profile.dir_name}'. "
            "If Chrome is already running with this profile, close it and try again."
        ) from e


async def goto_and_wait(page: Page, url: str) -> None:
    resp = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    if not resp:
        raise RuntimeError(f"Navigation returned no response for {url}")
