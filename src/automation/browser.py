"""Browser automation helper module using Playwright."""

from typing import Optional

from playwright.sync_api import BrowserContext, Page, sync_playwright


class BrowserHelper:
    """Helper class for browser automation with Playwright."""

    def __init__(self, headless: bool = True, slow_mo: int = 0):
        """Initialize the browser helper.

        Args:
            headless: Whether to run browser in headless mode
            slow_mo: Delay between operations in milliseconds
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.playwright = None
        self.browser = None
        self.context = None

    def __enter__(self):
        """Context manager entry."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless, slow_mo=self.slow_mo
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def create_context(
        self, tracing: bool = False, trace_file: Optional[str] = None
    ) -> BrowserContext:
        """Create a new browser context.

        Args:
            tracing: Whether to enable tracing
            trace_file: Path to save trace file

        Returns:
            Browser context
        """
        context_options = {}

        if tracing:
            context_options["record_video_dir"] = "./videos"
            if trace_file:
                context_options["record_har_path"] = trace_file

        self.context = self.browser.new_context(**context_options)

        if tracing:
            self.context.tracing.start(screenshots=True, snapshots=True)

        return self.context

    def new_page(self) -> Page:
        """Create a new page in the current context.

        Returns:
            New page
        """
        if not self.context:
            self.create_context()
        return self.context.new_page()

    def take_screenshot(self, page: Page, path: str = "screenshot.png"):
        """Take a screenshot of the current page.

        Args:
            page: Page to screenshot
            path: Path to save screenshot
        """
        page.screenshot(path=path)

    def stop_tracing(self, trace_file: str = "trace.zip"):
        """Stop tracing and save trace file.

        Args:
            trace_file: Path to save trace file
        """
        if self.context:
            self.context.tracing.stop(path=trace_file)


def create_browser(headless: bool = True, slow_mo: int = 0) -> BrowserHelper:
    """Factory function to create a browser helper.

    Args:
        headless: Whether to run browser in headless mode
        slow_mo: Delay between operations in milliseconds

    Returns:
        Browser helper instance
    """
    return BrowserHelper(headless=headless, slow_mo=slow_mo)
