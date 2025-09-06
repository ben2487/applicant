"""Playwright automation service for job applications."""

import asyncio
import base64
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from ..database.repository import RunRepository, RunEventRepository
from ..models.entities import RunEvent, EventLevel, EventCategory

logger = logging.getLogger(__name__)


class PlaywrightService:
    """Service for managing Playwright browser automation."""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.active_runs: Dict[int, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize Playwright browser."""
        try:
            print(f"🔧 [VERBOSE] Starting Playwright initialization...")
            self.playwright = await async_playwright().start()
            print(f"✅ [VERBOSE] Playwright started successfully")
            
            print(f"🔧 [VERBOSE] Launching Chromium browser...")
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # We want to see the browser for debugging
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            print(f"✅ [VERBOSE] Chromium browser launched successfully")
            logger.info("Playwright browser initialized")
        except Exception as e:
            print(f"❌ [VERBOSE] Failed to initialize Playwright: {e}")
            import traceback
            print(f"❌ [VERBOSE] Playwright init error traceback: {traceback.format_exc()}")
            logger.error(f"Failed to initialize Playwright: {e}")
            raise

    def _handle_browser_close(self, run_id: int, reason: str):
        """Handle when the browser is closed by the user."""
        try:
            print(f"🚪 [VERBOSE] Handling browser close for run {run_id}: {reason}")
            
            # Update run status in database
            from ..database.repository import RunRepository
            from ..models.entities import RunResultStatus
            RunRepository.update_status(run_id, RunResultStatus.TERMINATED, f"Terminated by user: {reason}")
            
            # Cancel screenshot task and remove from active runs
            if run_id in self.active_runs:
                run_info = self.active_runs[run_id]
                if 'screenshot_task' in run_info:
                    run_info['screenshot_task'].cancel()
                    print(f"🛑 [VERBOSE] Cancelled screenshot task for run {run_id}")
                del self.active_runs[run_id]
                print(f"🗑️ [VERBOSE] Removed run {run_id} from active runs")
            
            # Emit WebSocket event
            from ..websocket.handlers import get_websocket_manager
            try:
                ws_manager = get_websocket_manager()
                ws_manager.emit_error(run_id, {
                    'run_id': run_id,
                    'error': f'Browser terminated by user: {reason}',
                    'status': 'TERMINATED',
                    'timestamp': datetime.now().isoformat()
                })
                print(f"📡 [VERBOSE] Emitted termination event via WebSocket for run {run_id}")
            except Exception as ws_error:
                print(f"⚠️ [VERBOSE] Failed to emit termination event via WebSocket: {ws_error}")
            
            # Log the event
            asyncio.create_task(self._log_event(run_id, EventLevel.INFO, EventCategory.SYSTEM, 
                                              f"Run terminated by user: {reason}"))
            
        except Exception as e:
            print(f"❌ [VERBOSE] Error handling browser close: {e}")
            import traceback
            print(f"❌ [VERBOSE] Browser close error traceback: {traceback.format_exc()}")

    async def cleanup(self):
        """Cleanup Playwright resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Playwright cleanup completed")
        except Exception as e:
            logger.error(f"Error during Playwright cleanup: {e}")

    async def start_run(self, run_id: int, initial_url: str, headless: bool = False) -> Dict[str, Any]:
        """Start a new automation run."""
        try:
            print(f"🚀 [VERBOSE] Starting Playwright automation for run {run_id}")
            print(f"🌐 [VERBOSE] URL: {initial_url}")
            print(f"👁️ [VERBOSE] Headless: {headless}")
            print(f"🔍 [VERBOSE] Current active runs: {list(self.active_runs.keys())}")
            
            # Initialize Playwright if not already done
            if not self.browser:
                print(f"🔧 [VERBOSE] Initializing Playwright for run {run_id}...")
                await self.initialize()
                print(f"✅ [VERBOSE] Playwright initialized successfully")
            else:
                print(f"✅ [VERBOSE] Playwright already initialized")
            
            # Create browser context for this run
            print(f"🔧 [VERBOSE] Creating browser context for run {run_id}...")
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                record_video_dir='./videos' if not headless else None
            )
            print(f"✅ [VERBOSE] Browser context created successfully")
            
            # Add context close detection
            def on_context_close():
                print(f"🔍 [VERBOSE] Browser context closed for run {run_id}")
                self._handle_browser_close(run_id, "Browser context closed")
            
            self.context.on("close", on_context_close)
            
            # Create new page
            print(f"📄 [VERBOSE] Creating new page for run {run_id}...")
            self.page = await self.context.new_page()
            print(f"✅ [VERBOSE] New page created successfully")
            
            # Add page close detection
            def on_page_close():
                print(f"🔍 [VERBOSE] Browser page closed for run {run_id}")
                self._handle_browser_close(run_id, "Browser page closed")
            
            self.page.on("close", on_page_close)
            
            # Set up console logging
            print(f"📝 [VERBOSE] Setting up console logging for run {run_id}...")
            await self._setup_console_logging(run_id)
            print(f"✅ [VERBOSE] Console logging setup complete")
            
            # Set up network monitoring
            print(f"🌐 [VERBOSE] Setting up network monitoring for run {run_id}...")
            await self._setup_network_monitoring(run_id)
            print(f"✅ [VERBOSE] Network monitoring setup complete")
            
            # Store run info
            print(f"💾 [VERBOSE] Storing run info for run {run_id}...")
            self.active_runs[run_id] = {
                'page': self.page,
                'context': self.context,
                'started_at': datetime.now(),
                'status': 'IN_PROGRESS'
            }
            print(f"✅ [VERBOSE] Run {run_id} stored in active runs. Total active runs: {len(self.active_runs)}")
            
            # Navigate to initial URL
            print(f"🧭 [VERBOSE] Navigating to {initial_url}...")
            await self._log_event(run_id, EventLevel.INFO, EventCategory.BROWSER, 
                                f"Navigating to {initial_url}")
            
            await self.page.goto(initial_url, wait_until='networkidle')
            print(f"✅ [VERBOSE] Successfully navigated to {initial_url}")
            
            # Take initial screenshot
            print(f"📸 [VERBOSE] Taking initial screenshot for run {run_id}...")
            await self._take_screenshot(run_id)
            print(f"✅ [VERBOSE] Initial screenshot taken and sent")
            
            # Start continuous screenshot loop
            print(f"🎬 [VERBOSE] Starting screenshot loop for run {run_id}...")
            screenshot_task = asyncio.create_task(self._screenshot_loop(run_id))
            print(f"✅ [VERBOSE] Screenshot loop task created: {screenshot_task}")
            
            # Store the task in active runs for cleanup
            if run_id in self.active_runs:
                self.active_runs[run_id]['screenshot_task'] = screenshot_task
            
            result = {
                'run_id': run_id,
                'status': 'IN_PROGRESS',
                'message': 'Run started successfully'
            }
            print(f"🎉 Run {run_id} started successfully: {result}")
            return result
            
        except Exception as e:
            print(f"❌ Error starting run {run_id}: {e}")
            logger.error(f"Error starting run {run_id}: {e}")
            await self._log_event(run_id, EventLevel.ERROR, EventCategory.SYSTEM, 
                                f"Failed to start run: {str(e)}")
            raise

    async def stop_run(self, run_id: int) -> Dict[str, Any]:
        """Stop an active run."""
        try:
            if run_id in self.active_runs:
                run_info = self.active_runs[run_id]
                
                # Close page and context
                if run_info['page']:
                    await run_info['page'].close()
                if run_info['context']:
                    await run_info['context'].close()
                
                # Remove from active runs
                del self.active_runs[run_id]
                
                await self._log_event(run_id, EventLevel.INFO, EventCategory.SYSTEM, 
                                    "Run stopped by user")
                
                return {
                    'run_id': run_id,
                    'status': 'CANCELLED',
                    'message': 'Run stopped successfully'
                }
            else:
                return {
                    'run_id': run_id,
                    'status': 'FAILED',
                    'message': 'Run not found'
                }
                
        except Exception as e:
            logger.error(f"Error stopping run {run_id}: {e}")
            raise

    async def pause_run(self, run_id: int) -> Dict[str, Any]:
        """Pause an active run."""
        try:
            if run_id in self.active_runs:
                # In a real implementation, you might pause the automation logic
                await self._log_event(run_id, EventLevel.INFO, EventCategory.SYSTEM, 
                                    "Run paused")
                
                return {
                    'run_id': run_id,
                    'status': 'PAUSED',
                    'message': 'Run paused'
                }
            else:
                return {
                    'run_id': run_id,
                    'status': 'FAILED',
                    'message': 'Run not found'
                }
                
        except Exception as e:
            logger.error(f"Error pausing run {run_id}: {e}")
            raise

    async def resume_run(self, run_id: int) -> Dict[str, Any]:
        """Resume a paused run."""
        try:
            if run_id in self.active_runs:
                # In a real implementation, you might resume the automation logic
                await self._log_event(run_id, EventLevel.INFO, EventCategory.SYSTEM, 
                                    "Run resumed")
                
                return {
                    'run_id': run_id,
                    'status': 'IN_PROGRESS',
                    'message': 'Run resumed'
                }
            else:
                return {
                    'run_id': run_id,
                    'status': 'FAILED',
                    'message': 'Run not found'
                }
                
        except Exception as e:
            logger.error(f"Error resuming run {run_id}: {e}")
            raise

    async def take_screenshot(self, run_id: int) -> str:
        """Take a screenshot of the current page."""
        try:
            print(f"🔍 [VERBOSE] Checking if run {run_id} is in active_runs: {list(self.active_runs.keys())}")
            if run_id in self.active_runs:
                run_info = self.active_runs[run_id]
                page = run_info['page']
                print(f"✅ [VERBOSE] Found run {run_id}, taking screenshot...")
                
                # Take screenshot
                screenshot_bytes = await page.screenshot(full_page=True)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                print(f"✅ [VERBOSE] Screenshot taken successfully, size: {len(screenshot_b64)} chars")
                
                return screenshot_b64
            else:
                print(f"❌ [VERBOSE] Run {run_id} not found in active_runs: {list(self.active_runs.keys())}")
                raise ValueError(f"Run {run_id} not found")
                
        except Exception as e:
            print(f"❌ [VERBOSE] Error taking screenshot for run {run_id}: {e}")
            import traceback
            print(f"❌ [VERBOSE] Screenshot error traceback: {traceback.format_exc()}")
            logger.error(f"Error taking screenshot for run {run_id}: {e}")
            raise

    async def _setup_console_logging(self, run_id: int):
        """Set up console logging for the page."""
        if not self.page:
            return
            
        async def handle_console(msg):
            level = msg.type
            message = msg.text
            
            # Map console levels to our event levels
            level_map = {
                'log': EventLevel.INFO,
                'info': EventLevel.INFO,
                'warn': EventLevel.WARNING,
                'error': EventLevel.ERROR,
                'debug': EventLevel.DEBUG
            }
            
            event_level = level_map.get(level, EventLevel.INFO)
            
            # Log as both a regular event and emit as console log
            await self._log_event(run_id, event_level, EventCategory.BROWSER, 
                                f"Console {level}: {message}")
            
            # Also emit as console log for the frontend
            await self._emit_console_log(run_id, level, message)
            
            # Print to terminal with proper prefix
            prefix = "\\033[0;35m[BROWSER/PLAYWRIGHT]\\033[0m"  # Magenta for Playwright
            print(f"{prefix} {level}: {message}")
        
        self.page.on('console', handle_console)

    async def _setup_network_monitoring(self, run_id: int):
        """Set up network request monitoring."""
        if not self.page:
            return
            
        async def handle_request(request):
            await self._log_event(run_id, EventLevel.DEBUG, EventCategory.NETWORK, 
                                f"Request: {request.method} {request.url}")
        
        async def handle_response(response):
            status = response.status
            url = response.url
            
            if status >= 400:
                level = EventLevel.ERROR if status >= 500 else EventLevel.WARNING
                await self._log_event(run_id, level, EventCategory.NETWORK, 
                                    f"Response: {status} {url}")
            else:
                await self._log_event(run_id, EventLevel.DEBUG, EventCategory.NETWORK, 
                                    f"Response: {status} {url}")
        
        self.page.on('request', handle_request)
        self.page.on('response', handle_response)

    async def _screenshot_loop(self, run_id: int):
        """Continuous screenshot loop for video streaming."""
        print(f"🎬 [VERBOSE] Screenshot loop started for run {run_id}")
        try:
            loop_count = 0
            while run_id in self.active_runs:
                loop_count += 1
                print(f"🔄 [VERBOSE] Screenshot loop iteration {loop_count} for run {run_id}")
                
                # Check if page is still available
                if run_id not in self.active_runs or not self.active_runs[run_id].get('page'):
                    print(f"🔍 [VERBOSE] Page no longer available for run {run_id}, stopping screenshot loop")
                    break
                
                try:
                    await self._take_screenshot(run_id)
                except Exception as screenshot_error:
                    print(f"❌ [VERBOSE] Screenshot failed for run {run_id}: {screenshot_error}")
                    # If screenshot fails, it might mean the page is closed
                    if "Target page, context or browser has been closed" in str(screenshot_error):
                        print(f"🔍 [VERBOSE] Page closed detected for run {run_id}, stopping screenshot loop")
                        self._handle_browser_close(run_id, "Page closed during screenshot")
                        break
                    # For other errors, continue but log them
                    logger.warning(f"Screenshot failed for run {run_id}: {screenshot_error}")
                
                print(f"⏰ [VERBOSE] Waiting 1 second before next screenshot for run {run_id}")
                await asyncio.sleep(1)  # Take screenshot every second
                
        except asyncio.CancelledError:
            print(f"🛑 [VERBOSE] Screenshot loop cancelled for run {run_id}")
            raise  # Re-raise CancelledError
        except Exception as e:
            print(f"❌ [VERBOSE] Error in screenshot loop for run {run_id}: {e}")
            logger.error(f"Error in screenshot loop for run {run_id}: {e}")
        print(f"🛑 [VERBOSE] Screenshot loop ended for run {run_id}")

    async def _take_screenshot(self, run_id: int):
        """Take a screenshot and emit it via WebSocket."""
        try:
            print(f"📸 [VERBOSE] Taking screenshot for run {run_id}...")
            screenshot_b64 = await self.take_screenshot(run_id)
            print(f"✅ [VERBOSE] Screenshot taken, size: {len(screenshot_b64)} chars")
            
            # Emit via WebSocket
            from ..websocket.handlers import get_websocket_manager
            try:
                print(f"📡 [VERBOSE] Getting WebSocket manager for run {run_id}...")
                ws_manager = get_websocket_manager()
                print(f"📡 [VERBOSE] Emitting screencast frame via WebSocket for run {run_id}...")
                ws_manager.emit_screencast_frame(run_id, screenshot_b64)
                print(f"🖼️ [VERBOSE] Screenshot emitted via WebSocket for run {run_id}")
            except Exception as ws_error:
                print(f"⚠️ [VERBOSE] Failed to emit screenshot via WebSocket: {ws_error}")
                import traceback
                print(f"⚠️ [VERBOSE] WebSocket error traceback: {traceback.format_exc()}")
            
            logger.info(f"Screenshot taken for run {run_id}")
            
        except Exception as e:
            print(f"❌ [VERBOSE] Error taking screenshot for run {run_id}: {e}")
            import traceback
            print(f"❌ [VERBOSE] Screenshot error traceback: {traceback.format_exc()}")
            logger.error(f"Error taking screenshot for run {run_id}: {e}")

    async def _log_event(self, run_id: int, level: EventLevel, category: EventCategory, 
                        message: str, code: Optional[str] = None, data: Optional[Dict] = None):
        """Log an event to the database."""
        try:
            event = RunEvent(
                run_id=run_id,
                ts=datetime.now(),
                level=level,
                category=category,
                message=message,
                code=code,
                data=data
            )
            
            # Save to database
            RunEventRepository.create(event)
            
            # Emit via WebSocket
            from ..websocket.handlers import get_websocket_manager
            try:
                ws_manager = get_websocket_manager()
                # Let the WebSocket handler handle all datetime serialization
                event_dict = event.dict()
                ws_manager.emit_run_event(run_id, event_dict)
                print(f"📝 Event emitted via WebSocket for run {run_id}: {level} - {message}")
            except Exception as ws_error:
                print(f"⚠️ Failed to emit event via WebSocket: {ws_error}")
            
            logger.info(f"Event logged for run {run_id}: {level} - {message}")
            
        except Exception as e:
            print(f"❌ Error logging event for run {run_id}: {e}")
            logger.error(f"Error logging event for run {run_id}: {e}")

    async def _emit_console_log(self, run_id: int, level: str, message: str):
        """Emit a console log via WebSocket."""
        try:
            from ..websocket.handlers import get_websocket_manager
            ws_manager = get_websocket_manager()
            
            log_data = {
                "level": level.upper(),
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "category": "CONSOLE"
            }
            
            ws_manager.emit_console_log(run_id, log_data)
            print(f"💬 Console log emitted for run {run_id}: {level} - {message}")
            
        except Exception as e:
            print(f"❌ Error emitting console log for run {run_id}: {e}")
            logger.error(f"Error emitting console log for run {run_id}: {e}")


# Global service instance
playwright_service = PlaywrightService()
