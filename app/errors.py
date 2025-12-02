"""
Обработка ошибок для всех endpoints.
"""
from flask import jsonify


def register_error_handlers(app):
    """Регистрация обработчиков ошибок."""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Обработка ошибок валидации (400)."""
        return jsonify({
            'success': False,
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Некорректный запрос. Проверьте данные.'
            }
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Обработка ошибок авторизации (401)."""
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Требуется авторизация.'
            }
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Обработка ошибок доступа (403)."""
        return jsonify({
            'success': False,
            'error': {
                'code': 'FORBIDDEN',
                'message': 'Доступ запрещён.'
            }
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Обработка ошибок не найдено (404)."""
        return jsonify({
            'success': False,
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Ресурс не найден.'
            }
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Обработка внутренних ошибок (500)."""
        app.logger.error(f'Внутренняя ошибка: {error}')
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Внутренняя ошибка сервера.'
            }
        }), 500
    
    @app.errorhandler(ValueError)
    def value_error(error):
        """Обработка ошибок валидации значений."""
        return jsonify({
            'success': False,
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': str(error)
            }
        }), 400

