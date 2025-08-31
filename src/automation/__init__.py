"""Browser automation package using Playwright."""

from .browser import BrowserHelper, create_browser
from .example_flow import example_form_fill_flow, simple_navigation_flow

__version__ = "0.1.0"
__all__ = [
    "BrowserHelper",
    "create_browser",
    "example_form_fill_flow",
    "simple_navigation_flow",
]
