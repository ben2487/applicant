"""Runs API blueprint."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from ..database.repository import RunRepository, RunEventRepository, ArtifactRepository
from ..models.entities import Run, RunEvent, RunResultStatus
from ..services.playwright_service import playwright_service
from ..websocket.handlers import get_websocket_manager

runs_bp = Blueprint("runs", __name__, url_prefix="/api/runs")


@runs_bp.route("/", methods=["GET"])
def get_runs():
    """Get recent runs."""
    try:
        limit = request.args.get("limit", 50, type=int)
        runs = RunRepository.get_recent_runs(limit=limit)
        
        # Convert to dict for JSON serialization
        runs_data = []
        for run in runs:
            run_dict = run.dict()
            # Convert datetime objects to ISO format
            if run_dict.get("started_at"):
                run_dict["started_at"] = run_dict["started_at"].isoformat()
            if run_dict.get("ended_at"):
                run_dict["ended_at"] = run_dict["ended_at"].isoformat()
            if run_dict.get("created_at"):
                run_dict["created_at"] = run_dict["created_at"].isoformat()
            runs_data.append(run_dict)
        
        return jsonify({"runs": runs_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@runs_bp.route("/<int:run_id>", methods=["GET"])
def get_run(run_id: int):
    """Get a specific run by ID."""
    try:
        run = RunRepository.get_by_id(run_id)
        if not run:
            return jsonify({"error": "Run not found"}), 404
        
        run_dict = run.dict()
        # Convert datetime objects to ISO format
        if run_dict.get("started_at"):
            run_dict["started_at"] = run_dict["started_at"].isoformat()
        if run_dict.get("ended_at"):
            run_dict["ended_at"] = run_dict["ended_at"].isoformat()
        if run_dict.get("created_at"):
            run_dict["created_at"] = run_dict["created_at"].isoformat()
        
        return jsonify(run_dict)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@runs_bp.route("/<int:run_id>/events", methods=["GET"])
def get_run_events(run_id: int):
    """Get events for a specific run."""
    try:
        limit = request.args.get("limit", 1000, type=int)
        events = RunEventRepository.get_by_run(run_id, limit=limit)
        
        events_data = []
        for event in events:
            event_dict = event.dict()
            # Convert datetime objects to ISO format
            if event_dict.get("ts"):
                event_dict["ts"] = event_dict["ts"].isoformat()
            if event_dict.get("created_at"):
                event_dict["created_at"] = event_dict["created_at"].isoformat()
            events_data.append(event_dict)
        
        return jsonify({"events": events_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@runs_bp.route("/<int:run_id>/artifacts", methods=["GET"])
def get_run_artifacts(run_id: int):
    """Get artifacts for a specific run."""
    try:
        artifacts = ArtifactRepository.get_by_run(run_id)
        
        artifacts_data = []
        for artifact in artifacts:
            artifact_dict = artifact.dict()
            # Convert datetime objects to ISO format
            if artifact_dict.get("created_at"):
                artifact_dict["created_at"] = artifact_dict["created_at"].isoformat()
            artifacts_data.append(artifact_dict)
        
        return jsonify({"artifacts": artifacts_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@runs_bp.route("/", methods=["POST"])
def create_run():
    """Create a new run."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        required_fields = ["initial_url"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create run object
        run_data = {
            "initial_url": data["initial_url"],
            "headless": data.get("headless", False),  # Default to False for web interface
            "application_id": data.get("application_id"),
            "result_status": data.get("result_status", RunResultStatus.IN_PROGRESS),
            "summary": data.get("summary"),
            "raw": data.get("raw"),
        }
        
        run = Run(**run_data)
        created_run = RunRepository.create(run)
        
        # Start Playwright automation
        try:
            result = asyncio.run(playwright_service.start_run(
                created_run.id, 
                created_run.initial_url, 
                created_run.headless
            ))
            
            # Emit WebSocket status update
            ws_manager = get_websocket_manager()
            ws_manager.emit_run_status(created_run.id, {
                'run_id': created_run.id,
                'status': result.get('status', 'IN_PROGRESS'),
                'message': result.get('message', 'Run started'),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            print(f"Error starting Playwright automation: {e}")
            # Update run status to failed
            RunRepository.update_status(created_run.id, RunResultStatus.FAILED)
            created_run.result_status = RunResultStatus.FAILED
        
        run_dict = created_run.dict()
        # Convert datetime objects to ISO format
        if run_dict.get("started_at"):
            run_dict["started_at"] = run_dict["started_at"].isoformat()
        if run_dict.get("ended_at"):
            run_dict["ended_at"] = run_dict["ended_at"].isoformat()
        if run_dict.get("created_at"):
            run_dict["created_at"] = run_dict["created_at"].isoformat()
        
        return jsonify(run_dict), 201
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@runs_bp.route("/<int:run_id>/status", methods=["PUT"])
def update_run_status(run_id: int):
    """Update run status."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        result_status = data.get("result_status")
        summary = data.get("summary")
        ended_at = data.get("ended_at")
        
        if ended_at:
            try:
                ended_at = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "Invalid ended_at format"}), 400
        
        RunRepository.update_status(run_id, result_status, summary, ended_at)
        
        return jsonify({"message": "Run status updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@runs_bp.route("/<int:run_id>/events", methods=["POST"])
def create_run_event(run_id: int):
    """Create a new event for a run."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        required_fields = ["level", "category"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create event object
        event_data = {
            "run_id": run_id,
            "level": data["level"],
            "category": data["category"],
            "code": data.get("code"),
            "message": data.get("message"),
            "data": data.get("data"),
            "ts": data.get("ts"),
        }
        
        if event_data["ts"]:
            try:
                event_data["ts"] = datetime.fromisoformat(event_data["ts"].replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "Invalid ts format"}), 400
        
        event = RunEvent(**event_data)
        created_event = RunEventRepository.create(event)
        
        event_dict = created_event.dict()
        # Convert datetime objects to ISO format
        if event_dict.get("ts"):
            event_dict["ts"] = event_dict["ts"].isoformat()
        if event_dict.get("created_at"):
            event_dict["created_at"] = event_dict["created_at"].isoformat()
        
        return jsonify(event_dict), 201
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@runs_bp.route("/error-summary", methods=["GET"])
def get_error_summary():
    """Get summary of error codes for triage."""
    try:
        error_summary = RunEventRepository.get_error_summary()
        return jsonify({"error_summary": [{"code": code, "count": count} for code, count in error_summary]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
