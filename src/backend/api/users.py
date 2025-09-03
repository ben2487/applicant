"""Users API blueprint."""

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from ..database.repository import UserProfileRepository
from ..models.entities import UserProfile

users_bp = Blueprint("users", __name__, url_prefix="/api/users")


@users_bp.route("/", methods=["GET"])
def get_users():
    """Get all user profiles."""
    try:
        users = UserProfileRepository.get_all()
        
        users_data = []
        for user in users:
            user_dict = user.dict()
            # Convert datetime objects to ISO format
            if user_dict.get("created_at"):
                user_dict["created_at"] = user_dict["created_at"].isoformat()
            if user_dict.get("updated_at"):
                user_dict["updated_at"] = user_dict["updated_at"].isoformat()
            users_data.append(user_dict)
        
        return jsonify({"users": users_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@users_bp.route("/<slug>", methods=["GET"])
def get_user(slug: str):
    """Get a specific user profile by slug."""
    try:
        user = UserProfileRepository.get_by_slug(slug)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user_dict = user.dict()
        # Convert datetime objects to ISO format
        if user_dict.get("created_at"):
            user_dict["created_at"] = user_dict["created_at"].isoformat()
        if user_dict.get("updated_at"):
            user_dict["updated_at"] = user_dict["updated_at"].isoformat()
        
        return jsonify(user_dict)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@users_bp.route("/", methods=["POST"])
def create_user():
    """Create a new user profile."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        required_fields = ["slug", "display_name"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create user object
        user_data = {
            "slug": data["slug"],
            "display_name": data["display_name"],
            "meta": data.get("meta"),
        }
        
        user = UserProfile(**user_data)
        created_user = UserProfileRepository.create(user)
        
        user_dict = created_user.dict()
        # Convert datetime objects to ISO format
        if user_dict.get("created_at"):
            user_dict["created_at"] = user_dict["created_at"].isoformat()
        if user_dict.get("updated_at"):
            user_dict["updated_at"] = user_dict["updated_at"].isoformat()
        
        return jsonify(user_dict), 201
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
