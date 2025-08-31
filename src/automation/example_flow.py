"""Example automation flow demonstrating basic Playwright usage."""

from .browser import create_browser


def example_form_fill_flow(
    url: str = "https://httpbin.org/forms/post",
    screenshot_path: str = "example_form.png",
    headless: bool = True,
) -> None:
    """Example flow: navigate to a form, fill it out, and take a screenshot.

    Args:
        url: URL to navigate to
        screenshot_path: Path to save the screenshot
        headless: Whether to run browser in headless mode
    """
    with create_browser(headless=headless) as browser:
        # Create context with tracing enabled
        browser.create_context(tracing=True)
        page = browser.new_page()

        try:
            # Navigate to the form page
            print(f"Navigating to {url}")
            page.goto(url)
            page.wait_for_load_state("networkidle")

            # Fill out the form
            print("Filling out the form...")

            # Fill customer name
            page.fill('input[name="custname"]', "John Doe")

            # Fill phone number
            page.fill('input[name="custtel"]', "555-1234")

            # Fill email
            page.fill('input[name="custemail"]', "john.doe@example.com")

            # Select pizza size
            page.select_option('select[name="size"]', "large")

            # Select toppings
            page.check('input[value="bacon"]')
            page.check('input[value="cheese"]')

            # Fill delivery instructions
            page.fill('textarea[name="delivery"]', "Please deliver to the back door")

            # Take a screenshot before submission
            print(f"Taking screenshot: {screenshot_path}")
            browser.take_screenshot(page, screenshot_path)

            # Submit the form (optional - uncomment if you want to see the result)
            # page.click('input[type="submit"]')
            # page.wait_for_load_state("networkidle")
            # browser.take_screenshot(page, "after_submit.png")

            print("Form automation completed successfully!")

        except Exception as e:
            print(f"Error during automation: {e}")
            # Take error screenshot
            browser.take_screenshot(page, "error_screenshot.png")
            raise
        finally:
            # Stop tracing and save trace file
            browser.stop_tracing("example_flow_trace.zip")


def simple_navigation_flow(
    url: str = "https://example.com",
    screenshot_path: str = "example_page.png",
    headless: bool = True,
) -> None:
    """Simple flow: navigate to a page and take a screenshot.

    Args:
        url: URL to navigate to
        screenshot_path: Path to save the screenshot
        headless: Whether to run browser in headless mode
    """
    with create_browser(headless=headless) as browser:
        page = browser.new_page()

        try:
            print(f"Navigating to {url}")
            page.goto(url)
            page.wait_for_load_state("networkidle")

            print(f"Taking screenshot: {screenshot_path}")
            browser.take_screenshot(page, screenshot_path)

            print("Navigation completed successfully!")

        except Exception as e:
            print(f"Error during navigation: {e}")
            browser.take_screenshot(page, "error_screenshot.png")
            raise


if __name__ == "__main__":
    # Run the example flow
    example_form_fill_flow(headless=False)  # Set to False to see the browser in action
