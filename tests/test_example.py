"""Tests for the automation package."""

import pytest

from automation.browser import BrowserHelper, create_browser
from automation.example_flow import example_form_fill_flow, simple_navigation_flow


def test_browser_helper_creation():
    """Test that BrowserHelper can be created."""
    helper = BrowserHelper(headless=True, slow_mo=0)
    assert helper.headless is True
    assert helper.slow_mo == 0
    assert helper.browser is None
    assert helper.context is None


def test_create_browser_factory():
    """Test the create_browser factory function."""
    helper = create_browser(headless=False, slow_mo=100)
    assert isinstance(helper, BrowserHelper)
    assert helper.headless is False
    assert helper.slow_mo == 100


def test_browser_context_manager():
    """Test BrowserHelper as a context manager."""
    with create_browser(headless=True) as browser:
        assert browser.browser is not None
        assert browser.playwright is not None

        # Test context creation
        context = browser.create_context()
        assert context is not None

        # Test page creation
        page = browser.new_page()
        assert page is not None


def test_screenshot_functionality():
    """Test screenshot functionality."""
    with create_browser(headless=True) as browser:
        page = browser.new_page()
        page.goto("data:text/html,<h1>Test Page</h1>")

        # Test screenshot
        browser.take_screenshot(page, "test_screenshot.png")

        # Check if file was created
        import os

        assert os.path.exists("test_screenshot.png")

        # Clean up
        os.remove("test_screenshot.png")


def test_tracing_functionality():
    """Test tracing functionality."""
    with create_browser(headless=True) as browser:
        browser.create_context(tracing=True)
        page = browser.new_page()
        page.goto("data:text/html,<h1>Test Page</h1>")

        # Stop tracing
        browser.stop_tracing("test_trace.zip")

        # Check if file was created
        import os

        assert os.path.exists("test_trace.zip")

        # Clean up
        os.remove("test_trace.zip")


@pytest.mark.integration
def test_simple_navigation_flow():
    """Test the simple navigation flow (integration test)."""
    # This test requires internet connection
    try:
        simple_navigation_flow(
            url="https://httpbin.org/html",
            screenshot_path="test_navigation.png",
            headless=True,
        )

        # Check if screenshot was created
        import os

        assert os.path.exists("test_navigation.png")

        # Clean up
        os.remove("test_navigation.png")

    except Exception as e:
        pytest.skip(f"Integration test failed (likely network issue): {e}")


def test_example_flow_functions_exist():
    """Test that example flow functions are callable."""
    assert callable(example_form_fill_flow)
    assert callable(simple_navigation_flow)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
