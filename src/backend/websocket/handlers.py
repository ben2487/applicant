"""WebSocket handlers for real-time communication."""

import json
import asyncio
from typing import Any, Dict, Optional

from flask_socketio import emit, join_room, leave_room
from flask_socketio import SocketIO

from ..database.repository import RunRepository, RunEventRepository
from ..models.entities import RunEvent, EventLevel, EventCategory
from ..services.playwright_service import playwright_service


class WebSocketManager:
    """Manages WebSocket connections and real-time communication."""
    
    def __init__(self, socketio: SocketIO):
        """Initialize the WebSocket manager.
        
        Args:
            socketio: Flask-SocketIO instance
        """
        self.socketio = socketio
        self.active_runs: Dict[int, Dict[str, Any]] = {}
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up WebSocket event handlers."""
        
        @self.socketio.on("connect")
        def handle_connect(auth=None):
            """Handle client connection."""
            print(f"🔌 Client connected: {request.sid}")
            emit("connected", {"message": "Connected to WebSocket server"})
        
        @self.socketio.on("disconnect")
        def handle_disconnect():
            """Handle client disconnection."""
            print(f"❌ Client disconnected: {request.sid}")
        
        @self.socketio.on("join_run")
        def handle_join_run(data):
            """Join a specific run room for real-time updates."""
            run_id = data.get("run_id")
            if not run_id:
                print("❌ Join run failed: run_id is required")
                emit("error", {"message": "run_id is required"})
                return
            
            room = f"run_{run_id}"
            print(f"🚪 Client {request.sid} joining room: {room}")
            join_room(room)
            emit("joined_run", {"run_id": run_id, "room": room})
            
            # Send current run status if available
            if run_id in self.active_runs:
                print(f"📊 Sending current status for run {run_id}")
                emit("run_status", self.active_runs[run_id])
            else:
                print(f"ℹ️ No active status found for run {run_id}")
        
        @self.socketio.on("leave_run")
        def handle_leave_run(data):
            """Leave a specific run room."""
            run_id = data.get("run_id")
            if run_id:
                room = f"run_{run_id}"
                print(f"🚪 Client {request.sid} leaving room: {room}")
                leave_room(room)
                emit("left_run", {"run_id": run_id})
            else:
                print("❌ Leave run failed: run_id is required")
        
        @self.socketio.on("control_run")
        def handle_control_run(data):
            """Handle run control commands (pause, resume, stop)."""
            run_id = data.get("run_id")
            command = data.get("command")
            
            print(f"🎮 Control command received: {command} for run {run_id}")
            
            if not run_id or not command:
                print("❌ Control command failed: run_id and command are required")
                emit("error", {"message": "run_id and command are required"})
                return
            
            room = f"run_{run_id}"
            
            try:
                print(f"🔧 Executing {command} command for run {run_id}...")
                # Handle commands with Playwright service
                if command == 'pause':
                    result = asyncio.run(playwright_service.pause_run(run_id))
                elif command == 'resume':
                    result = asyncio.run(playwright_service.resume_run(run_id))
                elif command == 'stop':
                    result = asyncio.run(playwright_service.stop_run(run_id))
                else:
                    result = {'status': 'error', 'message': 'Unknown command'}
                
                print(f"✅ Control command {command} result: {result}")
                
                # Emit status update
                self.emit_run_status(run_id, {
                    'run_id': run_id,
                    'status': result.get('status', 'UNKNOWN'),
                    'message': result.get('message', ''),
                    'timestamp': self.socketio.server.manager.clock.time()
                })
                
                # Emit control acknowledgment
                emit("control_acknowledged", {
                    "run_id": run_id,
                    "command": command,
                    "status": "success"
                }, room=room)
                
            except Exception as e:
                print(f"❌ Error handling control command: {e}")
                emit("control_acknowledged", {
                    "run_id": run_id,
                    "command": command,
                    "status": "error",
                    "message": str(e)
                }, room=room)
    
    def log_control_event(self, run_id: int, action: str):
        """Log a control event to the database."""
        try:
            event = RunEvent(
                run_id=run_id,
                level=EventLevel.INFO,
                category=EventCategory.BROWSER,
                code=f"CONTROL_{action.upper()}",
                message=f"Run control: {action}",
                data={"action": action}
            )
            # Note: This would need to be async in a real implementation
            # For now, we'll just print it
            print(f"Control event: Run {run_id} - {action}")
        except Exception as e:
            print(f"Error logging control event: {e}")
    
    def emit_run_event(self, run_id: int, event_data: Dict[str, Any]):
        """Emit a run event to all clients monitoring the run."""
        room = f"run_{run_id}"
        print(f"📝 Emitting run event to room {room}: {event_data}")
        self.socketio.emit("run_event", event_data, room=room)
    
    def emit_run_status(self, run_id: int, status_data: Dict[str, Any]):
        """Emit run status update to all clients monitoring the run."""
        room = f"run_{run_id}"
        print(f"📊 Emitting run status to room {room}: {status_data}")
        self.socketio.emit("run_status", status_data, room=room)
        
        # Update active runs cache
        self.active_runs[run_id] = status_data
        print(f"💾 Updated active runs cache for run {run_id}")
    
    def emit_screencast_frame(self, run_id: int, frame_data: str):
        """Emit a screencast frame to all clients monitoring the run."""
        room = f"run_{run_id}"
        print(f"🖼️ Emitting screencast frame to room {room}, size: {len(frame_data)}")
        self.socketio.emit("screencast_frame", {
            "run_id": run_id,
            "frame": frame_data,
            "timestamp": self.socketio.server.manager.clock.time()
        }, room=room)
    
    def emit_console_log(self, run_id: int, log_data: Dict[str, Any]):
        """Emit console log to all clients monitoring the run."""
        room = f"run_{run_id}"
        self.socketio.emit("console_log", {
            "run_id": run_id,
            "level": log_data.get("level", "INFO"),
            "message": log_data.get("message", ""),
            "timestamp": log_data.get("timestamp"),
            "category": log_data.get("category", "CONSOLE")
        }, room=room)
    
    def emit_run_complete(self, run_id: int, result_data: Dict[str, Any]):
        """Emit run completion event."""
        room = f"run_{run_id}"
        self.socketio.emit("run_complete", {
            "run_id": run_id,
            "result": result_data,
            "timestamp": self.socketio.server.manager.clock.time()
        }, room=room)
        
        # Remove from active runs
        if run_id in self.active_runs:
            del self.active_runs[run_id]
    
    def emit_error(self, run_id: int, error_data: Dict[str, Any]):
        """Emit error event."""
        room = f"run_{run_id}"
        self.socketio.emit("run_error", {
            "run_id": run_id,
            "error": error_data,
            "timestamp": self.socketio.server.manager.clock.time()
        }, room=room)


# Global WebSocket manager instance
ws_manager: Optional[WebSocketManager] = None


def init_websocket_manager(socketio: SocketIO):
    """Initialize the global WebSocket manager."""
    global ws_manager
    ws_manager = WebSocketManager(socketio)


def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager."""
    if ws_manager is None:
        raise RuntimeError("WebSocket manager not initialized")
    return ws_manager
