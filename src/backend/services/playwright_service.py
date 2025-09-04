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
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # We want to see the browser for debugging
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            logger.info("Playwright browser initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            raise

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
            print(f"🚀 Starting Playwright automation for run {run_id}")
            print(f"🌐 URL: {initial_url}")
            print(f"👁️ Headless: {headless}")
            
            # Create browser context for this run
            print(f"🔧 Creating browser context for run {run_id}...")
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                record_video_dir='./videos' if not headless else None
            )
            
            # Create new page
            print(f"📄 Creating new page for run {run_id}...")
            self.page = await self.context.new_page()
            
            # Set up console logging
            print(f"📝 Setting up console logging for run {run_id}...")
            await self._setup_console_logging(run_id)
            
            # Set up network monitoring
            print(f"🌐 Setting up network monitoring for run {run_id}...")
            await self._setup_network_monitoring(run_id)
            
            # Store run info
            self.active_runs[run_id] = {
                'page': self.page,
                'context': self.context,
                'started_at': datetime.now(),
                'status': 'IN_PROGRESS'
            }
            print(f"💾 Run {run_id} stored in active runs")
            
            # Navigate to initial URL
            print(f"🧭 Navigating to {initial_url}...")
            await self._log_event(run_id, EventLevel.INFO, EventCategory.BROWSER, 
                                f"Navigating to {initial_url}")
            
            await self.page.goto(initial_url, wait_until='networkidle')
            print(f"✅ Successfully navigated to {initial_url}")
            
            # Take initial screenshot
            print(f"📸 Taking initial screenshot for run {run_id}...")
            await self._take_screenshot(run_id)
            
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
            if run_id in self.active_runs:
                run_info = self.active_runs[run_id]
                page = run_info['page']
                
                # Take screenshot
                screenshot_bytes = await page.screenshot(full_page=True)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                return screenshot_b64
            else:
                raise ValueError(f"Run {run_id} not found")
                
        except Exception as e:
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
            
            await self._log_event(run_id, event_level, EventCategory.BROWSER, 
                                f"Console {level}: {message}")
        
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

    async def _take_screenshot(self, run_id: int):
        """Take a screenshot and emit it via WebSocket."""
        try:
            screenshot_b64 = await self.take_screenshot(run_id)
            
            # Emit via WebSocket
            from ..websocket.handlers import get_websocket_manager
            try:
                ws_manager = get_websocket_manager()
                ws_manager.emit_screencast_frame(run_id, screenshot_b64)
                print(f"🖼️ Screenshot emitted via WebSocket for run {run_id}")
            except Exception as ws_error:
                print(f"⚠️ Failed to emit screenshot via WebSocket: {ws_error}")
            
            logger.info(f"Screenshot taken for run {run_id}")
            
        except Exception as e:
            print(f"❌ Error taking screenshot for run {run_id}: {e}")
            logger.error(f"Error taking screenshot for run {run_id}: {e}")

    async def _log_event(self, run_id: int, level: EventLevel, category: EventCategory, 
                        message: str, code: Optional[str] = None, data: Optional[Dict] = None):
        """Log an event to the database."""
        try:
            event = RunEvent(
                run_id=run_id,
                ts=datetime.now().isoformat(),
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
                ws_manager.emit_run_event(run_id, event.dict())
                print(f"📝 Event emitted via WebSocket for run {run_id}: {level} - {message}")
            except Exception as ws_error:
                print(f"⚠️ Failed to emit event via WebSocket: {ws_error}")
            
            logger.info(f"Event logged for run {run_id}: {level} - {message}")
            
        except Exception as e:
            print(f"❌ Error logging event for run {run_id}: {e}")
            logger.error(f"Error logging event for run {run_id}: {e}")


# Global service instance
playwright_service = PlaywrightService()
