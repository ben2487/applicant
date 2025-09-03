"""Main Flask application."""

import os
from contextlib import asynccontextmanager

from flask import Flask
from flask_socketio import SocketIO

from .database.connection import db_manager
from .api.runs import runs_bp
from .api.users import users_bp
from .websocket.handlers import init_websocket_manager


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configuration
    if test_config is None:
        app.config.from_mapping(
            SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
            DATABASE_URL=os.environ.get("DATABASE_URL", "postgresql://localhost/webbot"),
        )
    else:
        app.config.update(test_config)
    
    # Initialize SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode="threading",
        logger=True,
        engineio_logger=True
    )
    
    # Initialize WebSocket manager
    init_websocket_manager(socketio)
    
    # Register blueprints
    app.register_blueprint(runs_bp)
    app.register_blueprint(users_bp)
    
    # Health check endpoint
    @app.route("/health")
    def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "message": "WebBot backend is running"}
    
    # Initialize database on startup
    with app.app_context():
        try:
            db_manager.initialize()
            print("Database connection initialized")
        except Exception as e:
            print(f"Failed to initialize database: {e}")
            raise
    
    # Note: We don't close the connection pool on each request teardown
    # The pool will be closed when the application shuts down
    
    return app


def create_test_app():
    """Create Flask app for testing."""
    return create_app({
        "TESTING": True,
        "DATABASE_URL": "postgresql://localhost/webbot_test",
    })


if __name__ == "__main__":
    app = create_app()
    socketio = SocketIO(app)
    socketio.run(app, host="0.0.0.0", port=8000, debug=True)
