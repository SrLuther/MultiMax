"""
API Blueprint - Maintenance Mode

This file will be completely refactored in v3.4.0 after migration
of all business models to PostgreSQL.

Pending models:
- Produto: Product and inventory management
- Historico: Operation history
- NotificationRead: Read notification tracking
- CleaningTask: Cleaning tasks
- Recipe: Production recipes
"""

from flask import Blueprint, jsonify

bp = Blueprint("api", __name__, url_prefix="/api/v1")


@bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint - returns maintenance status."""
    return (
        jsonify(
            {
                "status": "maintenance",
                "message": "API in maintenance - models being migrated to PostgreSQL",
                "version": "3.3.2",
                "estimated_completion": "v3.4.0",
                "endpoints_available": [],
            }
        ),
        503,
    )
