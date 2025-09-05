"""
Console logging API endpoints
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from ..websocket.handlers import get_websocket_manager
from ..models.entities import RunEvent, EventLevel, EventCategory
from ..database.repository import RunEventRepository

console_bp = Blueprint('console', __name__, url_prefix='/api')

@console_bp.route('/console-log', methods=['POST'])
def log_console():
    """Receive console logs from frontend and forward to terminal/WebSocket."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        level = data.get('level', 'INFO')
        message = data.get('message', '')
        source = data.get('source', 'FRONTEND')
        timestamp = data.get('timestamp', datetime.now().isoformat())
        
        # Map frontend levels to our event levels
        level_map = {
            'LOG': EventLevel.INFO,
            'INFO': EventLevel.INFO,
            'WARN': EventLevel.WARNING,
            'WARNING': EventLevel.WARNING,
            'ERROR': EventLevel.ERROR,
            'DEBUG': EventLevel.DEBUG
        }
        
        event_level = level_map.get(level, EventLevel.INFO)
        
        # Log to database (frontend logs don't have a run_id, so we'll skip database logging for now)
        # TODO: Consider creating a separate frontend_logs table or using a special run_id
        # event = RunEvent(
        #     run_id=0,  # Frontend logs don't have a run_id
        #     ts=timestamp,
        #     level=event_level,
        #     category=EventCategory.CONSOLE,
        #     message=f"Frontend {level}: {message}",
        #     data={
        #         'source': source,
        #         'original_level': level,
        #         'timestamp': timestamp
        #     }
        # )
        # 
        # RunEventRepository.create(event)
        
        # Emit via WebSocket
        ws_manager = get_websocket_manager()
        ws_manager.emit_console_log(0, {
            'level': level,
            'message': message,
            'timestamp': timestamp,
            'category': 'FRONTEND'
        })
        
        # Print to terminal with proper prefix (will be processed by log forwarder)
        import sys
        print(f"[BROWSER/VITE] {level}: {message}", file=sys.stderr)
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"❌ Error logging frontend console: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
