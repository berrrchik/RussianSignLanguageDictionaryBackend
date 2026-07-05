"""
Health check endpoints.
"""
from typing import Dict

from flask import Blueprint, current_app


bp = Blueprint('health', __name__)


@bp.route('/health', methods=['GET'])
@bp.route('/api/health', methods=['GET'])
@bp.route('/api/v1/health', methods=['GET'])
def health() -> Dict[str, str]:
    """
    Service health check.
    ---
    tags:
      - Health
    responses:
      200:
        description: Service is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: ok
            version:
              type: string
              example: "1.0.0"
    """
    return {
        'status': 'ok',
        'version': current_app.config.get('APP_VERSION', '1.0.0'),
    }
