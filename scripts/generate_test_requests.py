#!/usr/bin/env python3
"""
Скрипт для генерации тестовых HTTP запросов к API.
Используется для заполнения дашборда "Flask HTTP Metrics" в Grafana.

Запуск:
    python scripts/generate_test_requests.py --base-url http://localhost:5001

Или для сервера:
    python scripts/generate_test_requests.py --base-url http://93.77.186.203:5001
"""

import argparse
import requests
import time
import random
import sys
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed


class RequestGenerator:
    """Генератор тестовых запросов для мониторинга."""
    
    def __init__(self, base_url: str, admin_username: Optional[str] = None, 
                 admin_password: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.admin_token: Optional[str] = None
        
    def _get_headers(self, auth: bool = False) -> Dict[str, str]:
        """Получить заголовки для запроса."""
        headers = {'Content-Type': 'application/json'}
        if auth and self.admin_token:
            headers['Authorization'] = f'Bearer {self.admin_token}'
        return headers
    
    def login_admin(self) -> bool:
        """Авторизация администратора."""
        if not self.admin_username or not self.admin_password:
            print("⚠️  Пропускаем авторизацию (не указаны username/password)")
            return False
            
        try:
            response = requests.post(
                f'{self.base_url}/api/v1/admin/auth/login',
                json={
                    'username': self.admin_username,
                    'password': self.admin_password
                },
                headers=self._get_headers(),
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'data' in data:
                    self.admin_token = data['data'].get('token')
                    print(f"✅ Авторизация успешна")
                    return True
            else:
                print(f"⚠️  Авторизация не удалась: {response.status_code}")
                return False
        except Exception as e:
            print(f"⚠️  Ошибка авторизации: {e}")
            return False
    
    def sync_check(self, last_updated: Optional[int] = None) -> requests.Response:
        """GET /api/v1/sync/check/raw"""
        params = {}
        if last_updated:
            params['last_updated'] = last_updated
        return requests.get(
            f'{self.base_url}/api/v1/sync/check/raw',
            params=params,
            timeout=10
        )
    
    def sync_data(self) -> requests.Response:
        """GET /api/v1/sync/data/raw"""
        return requests.get(
            f'{self.base_url}/api/v1/sync/data/raw',
            timeout=30
        )
    
    def search_sbert(self, text: str, limit: int = 10) -> requests.Response:
        """POST /api/v1/search/sbert"""
        return requests.post(
            f'{self.base_url}/api/v1/search/sbert',
            json={'text': text, 'limit': limit},
            headers=self._get_headers(),
            timeout=15
        )
    
    def admin_get_signs(self, page: int = 1, per_page: int = 20) -> requests.Response:
        """GET /api/v1/admin/signs"""
        return requests.get(
            f'{self.base_url}/api/v1/admin/signs',
            params={'page': page, 'per_page': per_page},
            headers=self._get_headers(auth=True),
            timeout=10
        )
    
    def admin_get_categories(self) -> requests.Response:
        """GET /api/v1/admin/categories"""
        return requests.get(
            f'{self.base_url}/api/v1/admin/categories',
            headers=self._get_headers(auth=True),
            timeout=10
        )
    
    def admin_get_lessons(self) -> requests.Response:
        """GET /api/v1/admin/lessons"""
        return requests.get(
            f'{self.base_url}/api/v1/admin/lessons',
            headers=self._get_headers(auth=True),
            timeout=10
        )
    
    def invalid_endpoint(self) -> requests.Response:
        """GET /api/v1/nonexistent - для генерации 404"""
        return requests.get(
            f'{self.base_url}/api/v1/nonexistent',
            timeout=5
        )
    
    def invalid_method(self) -> requests.Response:
        """DELETE /api/v1/sync/check/raw - для генерации 405"""
        return requests.delete(
            f'{self.base_url}/api/v1/sync/check/raw',
            timeout=5
        )
    
    def invalid_json(self) -> requests.Response:
        """POST /api/v1/search/sbert с невалидным JSON - для генерации 400"""
        return requests.post(
            f'{self.base_url}/api/v1/search/sbert',
            data='invalid json',
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
    
    def unauthorized_request(self) -> requests.Response:
        """GET /api/v1/admin/signs без токена - для генерации 401"""
        return requests.get(
            f'{self.base_url}/api/v1/admin/signs',
            headers=self._get_headers(auth=False),
            timeout=5
        )
    
    def server_error_request(self) -> requests.Response:
        """POST /api/v1/search/sbert с очень большим текстом - может вызвать 500 или 413"""
        # Попытка вызвать ошибку сервера через очень большой запрос
        try:
            return requests.post(
                f'{self.base_url}/api/v1/search/sbert',
                json={'text': 'x' * 10000, 'limit': 10},  # Очень длинный текст
                headers=self._get_headers(),
                timeout=5
            )
        except:
            # Если запрос упал, это тоже может быть 5xx
            raise
    
    def invalid_sign_id(self) -> requests.Response:
        """GET /api/v1/admin/signs/invalid_id_12345 - для генерации 404 (если авторизован)"""
        return requests.get(
            f'{self.base_url}/api/v1/admin/signs/invalid_id_12345',
            headers=self._get_headers(auth=True),
            timeout=5
        )


def generate_search_queries() -> List[str]:
    """Генерация разнообразных поисковых запросов."""
    return [
        "привет",
        "спасибо",
        "пожалуйста",
        "извините",
        "до свидания",
        "как дела",
        "хорошо",
        "плохо",
        "да",
        "нет",
        "помощь",
        "вопрос",
        "ответ",
        "время",
        "день",
        "ночь",
        "утро",
        "вечер",
        "работа",
        "дом",
        "семья",
        "друг",
        "любовь",
        "счастье",
        "грусть",
        "еда",
        "вода",
        "кофе",
        "чай",
        "хлеб",
        "молоко",
        "яблоко",
        "книга",
        "школа",
        "университет",
        "учитель",
        "студент",
        "доктор",
        "больница",
        "машина",
        "автобус",
        "поезд",
        "самолет",
        "город",
        "деревня",
        "страна",
        "мир",
        "Россия",
        "Москва",
        "язык",
        "общение",
    ]


def run_requests(generator: RequestGenerator, num_requests: int = 100, 
                 concurrent: int = 5, verbose: bool = False):
    """Запуск множества запросов для генерации метрик."""
    
    print(f"🚀 Начинаем генерацию {num_requests} запросов (параллельно: {concurrent})...")
    print(f"📍 Базовый URL: {generator.base_url}\n")
    
    # Авторизация (если указаны credentials)
    if generator.admin_username:
        generator.login_admin()
    
    # Список всех функций для запросов
    request_functions = []
    
    # Публичные endpoints (70% запросов)
    for _ in range(int(num_requests * 0.4)):
        request_functions.append(('sync_check', lambda: generator.sync_check()))
    
    for _ in range(int(num_requests * 0.2)):
        request_functions.append(('sync_data', lambda: generator.sync_data()))
    
    search_queries = generate_search_queries()
    for _ in range(int(num_requests * 0.1)):
        query = random.choice(search_queries)
        request_functions.append(('search_sbert', lambda q=query: generator.search_sbert(q)))
    
    # Административные endpoints (20% запросов, только если авторизованы)
    if generator.admin_token:
        for _ in range(int(num_requests * 0.1)):
            request_functions.append(('admin_get_signs', lambda: generator.admin_get_signs()))
        
        for _ in range(int(num_requests * 0.05)):
            request_functions.append(('admin_get_categories', lambda: generator.admin_get_categories()))
        
        for _ in range(int(num_requests * 0.05)):
            request_functions.append(('admin_get_lessons', lambda: generator.admin_get_lessons()))
    
    # Ошибки (10% запросов)
    # 4xx ошибки
    for _ in range(int(num_requests * 0.05)):
        request_functions.append(('invalid_endpoint', lambda: generator.invalid_endpoint()))
    
    for _ in range(int(num_requests * 0.03)):
        request_functions.append(('invalid_method', lambda: generator.invalid_method()))
    
    for _ in range(int(num_requests * 0.01)):
        request_functions.append(('invalid_json', lambda: generator.invalid_json()))
    
    if not generator.admin_token:
        for _ in range(int(num_requests * 0.01)):
            request_functions.append(('unauthorized', lambda: generator.unauthorized_request()))
    elif generator.admin_token:
        # Если авторизованы, можем попробовать получить несуществующий жест
        for _ in range(int(num_requests * 0.01)):
            request_functions.append(('invalid_sign_id', lambda: generator.invalid_sign_id()))
    
    # 5xx ошибки (попытка вызвать серверную ошибку)
    for _ in range(int(num_requests * 0.01)):
        request_functions.append(('server_error', lambda: generator.server_error_request()))
    
    # Перемешиваем для реалистичности
    random.shuffle(request_functions)
    
    # Статистика
    stats = {
        'total': 0,
        'success': 0,
        'errors': 0,
        'status_codes': {},
        'endpoints': {}
    }
    
    start_time = time.time()
    
    def execute_request(name: str, func):
        """Выполнить один запрос."""
        try:
            response = func()
            status_code = response.status_code
            
            stats['total'] += 1
            stats['status_codes'][status_code] = stats['status_codes'].get(status_code, 0) + 1
            stats['endpoints'][name] = stats['endpoints'].get(name, 0) + 1
            
            if 200 <= status_code < 400:
                stats['success'] += 1
            else:
                stats['errors'] += 1
            
            if verbose:
                print(f"  {name}: {status_code}")
            
            return response
        except requests.exceptions.RequestException as e:
            # Ошибки сети или таймауты могут быть связаны с 5xx
            stats['total'] += 1
            stats['errors'] += 1
            # Пытаемся определить статус код из исключения
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                stats['status_codes'][status_code] = stats['status_codes'].get(status_code, 0) + 1
            else:
                # Таймаут или сетевая ошибка - считаем как 500
                stats['status_codes'][500] = stats['status_codes'].get(500, 0) + 1
            if verbose:
                print(f"  {name}: ERROR - {e}")
            return None
        except Exception as e:
            stats['total'] += 1
            stats['errors'] += 1
            # Неожиданные ошибки считаем как 500
            stats['status_codes'][500] = stats['status_codes'].get(500, 0) + 1
            if verbose:
                print(f"  {name}: ERROR - {e}")
            return None
    
    # Выполняем запросы параллельно
    with ThreadPoolExecutor(max_workers=concurrent) as executor:
        futures = [
            executor.submit(execute_request, name, func)
            for name, func in request_functions
        ]
        
        # Ждем завершения всех запросов
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                if verbose:
                    print(f"  Ошибка выполнения: {e}")
    
    elapsed_time = time.time() - start_time
    
    # Выводим статистику
    print("\n" + "="*60)
    print("📊 Статистика выполнения:")
    print("="*60)
    print(f"Всего запросов: {stats['total']}")
    print(f"Успешных (2xx/3xx): {stats['success']}")
    print(f"Ошибок (4xx/5xx): {stats['errors']}")
    print(f"Время выполнения: {elapsed_time:.2f} сек")
    print(f"Запросов в секунду: {stats['total'] / elapsed_time:.2f}")
    
    print("\n📈 Статус коды:")
    for code in sorted(stats['status_codes'].keys()):
        count = stats['status_codes'][code]
        percentage = (count / stats['total']) * 100
        print(f"  {code}: {count} ({percentage:.1f}%)")
    
    print("\n🔗 Endpoints:")
    for endpoint in sorted(stats['endpoints'].keys()):
        count = stats['endpoints'][endpoint]
        percentage = (count / stats['total']) * 100
        print(f"  {endpoint}: {count} ({percentage:.1f}%)")
    
    print("\n✅ Генерация запросов завершена!")
    print("💡 Теперь проверьте дашборд в Grafana: http://93.77.186.203:3000")


def main():
    parser = argparse.ArgumentParser(
        description='Генерация тестовых HTTP запросов для мониторинга',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Базовый запуск (только публичные endpoints)
  python scripts/generate_test_requests.py --base-url http://localhost:5001
  
  # С авторизацией (для админских endpoints)
  python scripts/generate_test_requests.py \\
    --base-url http://93.77.186.203:5001 \\
    --admin-username admin \\
    --admin-password ваш_пароль
  
  # Больше запросов, параллельно
  python scripts/generate_test_requests.py \\
    --base-url http://93.77.186.203:5001 \\
    --num-requests 500 \\
    --concurrent 10
  
  # Подробный вывод
  python scripts/generate_test_requests.py \\
    --base-url http://93.77.186.203:5001 \\
    --verbose
        """
    )
    
    parser.add_argument(
        '--base-url',
        type=str,
        required=True,
        help='Базовый URL API (например: http://localhost:5001 или http://93.77.186.203:5001)'
    )
    
    parser.add_argument(
        '--admin-username',
        type=str,
        default=None,
        help='Имя пользователя администратора (для админских endpoints)'
    )
    
    parser.add_argument(
        '--admin-password',
        type=str,
        default=None,
        help='Пароль администратора (для админских endpoints)'
    )
    
    parser.add_argument(
        '--num-requests',
        type=int,
        default=100,
        help='Количество запросов для генерации (по умолчанию: 100)'
    )
    
    parser.add_argument(
        '--concurrent',
        type=int,
        default=5,
        help='Количество параллельных запросов (по умолчанию: 5)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Подробный вывод каждого запроса'
    )
    
    args = parser.parse_args()
    
    # Проверка URL
    if not args.base_url.startswith(('http://', 'https://')):
        print("❌ Ошибка: base-url должен начинаться с http:// или https://")
        sys.exit(1)
    
    # Создаем генератор
    generator = RequestGenerator(
        base_url=args.base_url,
        admin_username=args.admin_username,
        admin_password=args.admin_password
    )
    
    # Запускаем генерацию запросов
    try:
        run_requests(
            generator,
            num_requests=args.num_requests,
            concurrent=args.concurrent,
            verbose=args.verbose
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
