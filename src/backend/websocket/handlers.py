"""WebSocket handlers for real-time communication."""

import json
from typing import Any, Dict, Optional

from flask_socketio import emit, join_room, leave_room
from flask_socketio import SocketIO

from ..database.repository import RunRepository, RunEventRepository
from ..models.entities import RunEvent, EventLevel, EventCategory


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
        def handle_connect():
            """Handle client connection."""
            emit("connected", {"message": "Connected to WebSocket server"})
        
        @self.socketio.on("disconnect")
        def handle_disconnect():
            """Handle client disconnection."""
            print("Client disconnected")
        
        @self.socketio.on("join_run")
        def handle_join_run(data):
            """Join a specific run room for real-time updates."""
            run_id = data.get("run_id")
            if not run_id:
                emit("error", {"message": "run_id is required"})
                return
            
            room = f"run_{run_id}"
            join_room(room)
            emit("joined_run", {"run_id": run_id, "room": room})
            
            # Send current run status if available
            if run_id in self.active_runs:
                emit("run_status", self.active_runs[run_id])
        
        @self.socketio.on("leave_run")
        def handle_leave_run(data):
            """Leave a specific run room."""
            run_id = data.get("run_id")
            if run_id:
                room = f"run_{run_id}"
                leave_room(room)
                emit("left_run", {"run_id": run_id})
        
        @self.socketio.on("control_run")
        def handle_control_run(data):
            """Handle run control commands (pause, resume, cancel)."""
            run_id = data.get("run_id")
            action = data.get("action")
            
            if not run_id or not action:
                emit("error", {"message": "run_id and action are required"})
                return
            
            room = f"run_{run_id}"
            
            # Emit control command to the run room
            emit("run_control", {
                "run_id": run_id,
                "action": action,
                "timestamp": self.socketio.server.manager.clock.time()
            }, room=room)
            
            # Log the control event
            self.log_control_event(run_id, action)
    
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
        self.socketio.emit("run_event", event_data, room=room)
    
    def emit_run_status(self, run_id: int, status_data: Dict[str, Any]):
        """Emit run status update to all clients monitoring the run."""
        room = f"run_{run_id}"
        self.socketio.emit("run_status", status_data, room=room)
        
        # Update active runs cache
        self.active_runs[run_id] = status_data
    
    def emit_screencast_frame(self, run_id: int, frame_data: str):
        """Emit a screencast frame to all clients monitoring the run."""
        room = f"run_{run_id}"
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
