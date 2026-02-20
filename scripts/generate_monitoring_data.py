#!/usr/bin/env python3
"""
Скрипт для генерации тестовых данных для панелей мониторинга в Grafana.

Генерирует данные для следующих панелей:
1. HTTP Requests Rate - запросы с разными методами (GET, POST, PUT, DELETE) и статусами
2. HTTP Request Duration (p50, p95, p99) - запросы к разным путям (path) с разной длительностью
3. HTTP Status Codes - запросы с разными статус кодами (200, 400, 401, 404, 405, 500)
4. Active Requests - параллельные запросы для отслеживания активных запросов

Запуск:
    python scripts/generate_monitoring_data.py --base-url http://localhost:5001
    
    # С авторизацией (для админских endpoints)
    python scripts/generate_monitoring_data.py \\
        --base-url http://93.77.186.203:5001 \\
        --admin-username admin \\
        --admin-password ваш_пароль
    
    # Непрерывная генерация данных (для долгосрочного мониторинга)
    python scripts/generate_monitoring_data.py \\
        --base-url http://93.77.186.203:5001 \\
        --continuous \\
        --interval 5
"""

import argparse
import requests
import time
import random
import sys
from typing import Optional, List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event


class MonitoringDataGenerator:
    """Генератор данных для панелей мониторинга."""
    
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
                    return True
            return False
        except Exception:
            return False
    
    # ========== GET запросы (для разных путей) ==========
    
    def get_sync_check(self) -> requests.Response:
        """GET /api/v1/sync/check/raw - быстрый запрос"""
        return requests.get(
            f'{self.base_url}/api/v1/sync/check/raw',
            timeout=10
        )
    
    def get_sync_data(self) -> requests.Response:
        """GET /api/v1/sync/data/raw - более медленный запрос"""
        return requests.get(
            f'{self.base_url}/api/v1/sync/data/raw',
            timeout=30
        )
    
    def get_admin_signs(self, page: int = 1) -> requests.Response:
        """GET /api/v1/admin/signs - админский endpoint"""
        return requests.get(
            f'{self.base_url}/api/v1/admin/signs',
            params={'page': page, 'per_page': 20},
            headers=self._get_headers(auth=True),
            timeout=10
        )
    
    def get_admin_categories(self) -> requests.Response:
        """GET /api/v1/admin/categories - админский endpoint"""
        return requests.get(
            f'{self.base_url}/api/v1/admin/categories',
            headers=self._get_headers(auth=True),
            timeout=10
        )
    
    def get_admin_lessons(self) -> requests.Response:
        """GET /api/v1/admin/lessons - админский endpoint"""
        return requests.get(
            f'{self.base_url}/api/v1/admin/lessons',
            headers=self._get_headers(auth=True),
            timeout=10
        )
    
    # ========== POST запросы ==========
    
    def post_search_sbert(self, text: str = "привет") -> requests.Response:
        """POST /api/v1/search/sbert - поиск через SBERT"""
        return requests.post(
            f'{self.base_url}/api/v1/search/sbert',
            json={'text': text, 'limit': 10},
            headers=self._get_headers(),
            timeout=15
        )
    
    def post_admin_login(self, username: str = "admin", password: str = "wrong") -> requests.Response:
        """POST /api/v1/admin/auth/login - авторизация (может быть 200 или 401)"""
        return requests.post(
            f'{self.base_url}/api/v1/admin/auth/login',
            json={'username': username, 'password': password},
            headers=self._get_headers(),
            timeout=5
        )
    
    # ========== PUT запросы ==========
    
    def put_admin_sign(self, sign_id: str = "nonexistent") -> requests.Response:
        """
        PUT /api/v1/admin/signs/{id} - обновление жеста (может быть 200, 404, 401)
        
        ВАЖНО: В скрипте используется только для генерации 404 ошибок.
        Если жест существует, он будет ОБНОВЛЕН в базе данных!
        Поэтому в скрипте используются только заведомо несуществующие ID.
        """
        return requests.put(
            f'{self.base_url}/api/v1/admin/signs/{sign_id}',
            json={'word': 'test', 'description': 'test'},
            headers=self._get_headers(auth=True),
            timeout=10
        )
    
    # ========== DELETE запросы ==========
    
    def delete_admin_sign(self, sign_id: str = "nonexistent") -> requests.Response:
        """
        DELETE /api/v1/admin/signs/{id} - удаление жеста
        
        ВАЖНО: В скрипте используется только для генерации 404 ошибок.
        Если жест существует, он будет УДАЛЕН из базы данных вместе со всеми видео!
        Поэтому в скрипте используются только заведомо несуществующие ID.
        """
        return requests.delete(
            f'{self.base_url}/api/v1/admin/signs/{sign_id}',
            headers=self._get_headers(auth=True),
            timeout=10
        )
    
    # ========== Запросы для генерации ошибок ==========
    
    def get_404(self) -> requests.Response:
        """GET /api/v1/nonexistent - для генерации 404"""
        return requests.get(
            f'{self.base_url}/api/v1/nonexistent',
            timeout=5
        )
    
    def delete_sync_check(self) -> requests.Response:
        """DELETE /api/v1/sync/check/raw - для генерации 405 (Method Not Allowed)"""
        return requests.delete(
            f'{self.base_url}/api/v1/sync/check/raw',
            timeout=5
        )
    
    def post_invalid_json(self) -> requests.Response:
        """POST /api/v1/search/sbert с невалидным JSON - для генерации 400"""
        return requests.post(
            f'{self.base_url}/api/v1/search/sbert',
            data='invalid json',
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
    
    def get_unauthorized(self) -> requests.Response:
        """GET /api/v1/admin/signs без токена - для генерации 401"""
        return requests.get(
            f'{self.base_url}/api/v1/admin/signs',
            headers=self._get_headers(auth=False),
            timeout=5
        )
    
    def post_server_error(self) -> requests.Response:
        """POST /api/v1/search/sbert с очень большим текстом - может вызвать 500 или 413"""
        return requests.post(
            f'{self.base_url}/api/v1/search/sbert',
            json={'text': 'x' * 10000, 'limit': 10},
            headers=self._get_headers(),
            timeout=5
        )


def generate_search_queries() -> List[str]:
    """Генерация разнообразных поисковых запросов."""
    return [
        "привет", "спасибо", "пожалуйста", "извините", "до свидания",
        "как дела", "хорошо", "плохо", "да", "нет", "помощь", "вопрос",
        "ответ", "время", "день", "ночь", "утро", "вечер", "работа", "дом",
        "семья", "друг", "любовь", "счастье", "грусть", "еда", "вода",
        "кофе", "чай", "хлеб", "молоко", "яблоко", "книга", "школа",
        "университет", "учитель", "студент", "доктор", "больница", "машина",
        "автобус", "поезд", "самолет", "город", "деревня", "страна", "мир"
    ]


def create_request_plan(generator: MonitoringDataGenerator, num_requests: int = 200) -> List[Tuple[str, callable]]:
    """
    Создает план запросов для генерации данных для всех панелей мониторинга.
    
    Распределение:
    - 50% GET запросы (разные пути для перцентилей)
    - 25% POST запросы
    - 10% PUT запросы
    - 5% DELETE запросы
    - 10% запросы с ошибками (400, 401, 404, 405, 500)
    """
    request_functions = []
    
    # ========== GET запросы (50%) - для разных путей и перцентилей ==========
    # Разные пути важны для панели "HTTP Request Duration (p50, p95, p99)"
    
    # Быстрые запросы (sync/check) - 20%
    for _ in range(int(num_requests * 0.20)):
        request_functions.append(('GET /sync/check/raw', lambda: generator.get_sync_check()))
    
    # Медленные запросы (sync/data) - 15% - для более высоких перцентилей
    for _ in range(int(num_requests * 0.15)):
        request_functions.append(('GET /sync/data/raw', lambda: generator.get_sync_data()))
    
    # Админские GET запросы - 15% (только если авторизованы)
    if generator.admin_token:
        for _ in range(int(num_requests * 0.05)):
            request_functions.append(('GET /admin/signs', lambda: generator.get_admin_signs()))
        
        for _ in range(int(num_requests * 0.05)):
            request_functions.append(('GET /admin/categories', lambda: generator.get_admin_categories()))
        
        for _ in range(int(num_requests * 0.05)):
            request_functions.append(('GET /admin/lessons', lambda: generator.get_admin_lessons()))
    
    # ========== POST запросы (25%) ==========
    search_queries = generate_search_queries()
    
    # Успешные POST запросы - 20%
    for _ in range(int(num_requests * 0.20)):
        query = random.choice(search_queries)
        request_functions.append(('POST /search/sbert', lambda q=query: generator.post_search_sbert(q)))
    
    # POST запросы с ошибками - 5%
    # Неправильная авторизация (401) - 2%
    for _ in range(int(num_requests * 0.02)):
        request_functions.append(('POST /admin/auth/login (wrong)', 
                                 lambda: generator.post_admin_login("admin", "wrong_password")))
    
    # Невалидный JSON (400) - 1.5%
    for _ in range(int(num_requests * 0.015)):
        request_functions.append(('POST /search/sbert (invalid)', lambda: generator.post_invalid_json()))
    
    # Очень большой запрос (может быть 500 или 413) - 1.5%
    for _ in range(int(num_requests * 0.015)):
        request_functions.append(('POST /search/sbert (large)', lambda: generator.post_server_error()))
    
    # ========== PUT запросы (10%) ==========
    if generator.admin_token:
        # PUT запросы к несуществующим ресурсам (404) - 5%
        # ВАЖНО: Используем заведомо несуществующие ID (с префиксом "test_")
        # чтобы гарантированно получить 404 и не изменить реальные данные
        for _ in range(int(num_requests * 0.05)):
            # Используем префикс "test_" чтобы гарантировать, что ID не существует
            sign_id = f"test_nonexistent_{random.randint(100000, 999999)}"
            request_functions.append(('PUT /admin/signs/{id} (404)', 
                                     lambda sid=sign_id: generator.put_admin_sign(sid)))
    
    # ========== DELETE запросы (5%) ==========
    if generator.admin_token:
        # DELETE запросы к несуществующим ресурсам (404) - 5%
        # ВАЖНО: Используем заведомо несуществующие ID (с префиксом "test_")
        # чтобы гарантированно получить 404 и не удалить реальные данные
        for _ in range(int(num_requests * 0.05)):
            # Используем префикс "test_" чтобы гарантировать, что ID не существует
            sign_id = f"test_nonexistent_{random.randint(100000, 999999)}"
            request_functions.append(('DELETE /admin/signs/{id} (404)', 
                                     lambda sid=sign_id: generator.delete_admin_sign(sid)))
    
    # ========== Запросы для генерации ошибок (10%) ==========
    
    # 404 ошибки - 3%
    for _ in range(int(num_requests * 0.03)):
        request_functions.append(('GET /nonexistent (404)', lambda: generator.get_404()))
    
    # 405 ошибки (Method Not Allowed) - 2%
    for _ in range(int(num_requests * 0.02)):
        request_functions.append(('DELETE /sync/check/raw (405)', lambda: generator.delete_sync_check()))
    
    # 401 ошибки (Unauthorized) - 2%
    if not generator.admin_token:
        for _ in range(int(num_requests * 0.02)):
            request_functions.append(('GET /admin/signs (401)', lambda: generator.get_unauthorized()))
    
    # Перемешиваем для реалистичности
    random.shuffle(request_functions)
    
    return request_functions


def run_monitoring_generation(generator: MonitoringDataGenerator, 
                              num_requests: int = 200,
                              concurrent: int = 10,
                              verbose: bool = False):
    """Запуск генерации данных для мониторинга."""
    
    print(f"🚀 Генерация данных для панелей мониторинга")
    print(f"📍 Базовый URL: {generator.base_url}")
    print(f"📊 Количество запросов: {num_requests}")
    print(f"⚡ Параллельных потоков: {concurrent}\n")
    
    # Авторизация (если указаны credentials)
    if generator.admin_username:
        if generator.login_admin():
            print("✅ Авторизация успешна\n")
        else:
            print("⚠️  Авторизация не удалась, будут использоваться только публичные endpoints\n")
    
    # Создаем план запросов
    request_functions = create_request_plan(generator, num_requests)
    
    # Статистика
    stats = {
        'total': 0,
        'success': 0,
        'errors': 0,
        'status_codes': {},
        'methods': {},
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
            
            # Извлекаем метод и endpoint из имени
            if ' ' in name:
                method = name.split()[0]
                endpoint = name.split()[1] if len(name.split()) > 1 else name
            else:
                method = 'UNKNOWN'
                endpoint = name
            
            stats['methods'][method] = stats['methods'].get(method, 0) + 1
            stats['endpoints'][endpoint] = stats['endpoints'].get(endpoint, 0) + 1
            
            if 200 <= status_code < 400:
                stats['success'] += 1
            else:
                stats['errors'] += 1
            
            if verbose:
                print(f"  {name}: {status_code}")
            
            return response
        except requests.exceptions.RequestException as e:
            stats['total'] += 1
            stats['errors'] += 1
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                stats['status_codes'][status_code] = stats['status_codes'].get(status_code, 0) + 1
            else:
                stats['status_codes'][500] = stats['status_codes'].get(500, 0) + 1
            if verbose:
                print(f"  {name}: ERROR - {e}")
            return None
        except Exception as e:
            stats['total'] += 1
            stats['errors'] += 1
            stats['status_codes'][500] = stats['status_codes'].get(500, 0) + 1
            if verbose:
                print(f"  {name}: ERROR - {e}")
            return None
    
    # Выполняем запросы параллельно (для генерации active requests)
    with ThreadPoolExecutor(max_workers=concurrent) as executor:
        futures = [
            executor.submit(execute_request, name, func)
            for name, func in request_functions
        ]
        
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
    
    print("\n📈 Статус коды (для панели 'HTTP Status Codes'):")
    for code in sorted(stats['status_codes'].keys()):
        count = stats['status_codes'][code]
        percentage = (count / stats['total']) * 100
        print(f"  {code}: {count} ({percentage:.1f}%)")
    
    print("\n🔧 HTTP методы (для панели 'HTTP Requests Rate'):")
    for method in sorted(stats['methods'].keys()):
        count = stats['methods'][method]
        percentage = (count / stats['total']) * 100
        print(f"  {method}: {count} ({percentage:.1f}%)")
    
    print("\n🔗 Endpoints (для панели 'HTTP Request Duration'):")
    for endpoint in sorted(stats['endpoints'].keys()):
        count = stats['endpoints'][endpoint]
        percentage = (count / stats['total']) * 100
        print(f"  {endpoint}: {count} ({percentage:.1f}%)")
    
    print("\n✅ Генерация данных завершена!")
    print("💡 Проверьте панели в Grafana:")
    print("   - HTTP Requests Rate")
    print("   - HTTP Request Duration (p50, p95, p99)")
    print("   - HTTP Status Codes")
    print("   - Active Requests")


def run_continuous(generator: MonitoringDataGenerator, 
                   interval: int = 5,
                   concurrent: int = 10,
                   batch_size: int = 50,
                   verbose: bool = False,
                   stop_event: Event = None):
    """Непрерывная генерация данных для долгосрочного мониторинга."""
    
    print(f"🔄 Непрерывная генерация данных (интервал: {interval} сек, размер батча: {batch_size})")
    print("Нажмите Ctrl+C для остановки\n")
    
    iteration = 0
    
    try:
        while not (stop_event and stop_event.is_set()):
            iteration += 1
            print(f"\n{'='*60}")
            print(f"Итерация #{iteration} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            run_monitoring_generation(
                generator,
                num_requests=batch_size,
                concurrent=concurrent,
                verbose=verbose
            )
            
            if stop_event:
                if stop_event.wait(interval):
                    break
            else:
                time.sleep(interval)
                
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")


def main():
    parser = argparse.ArgumentParser(
        description='Генерация данных для панелей мониторинга в Grafana',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Базовый запуск (одна итерация)
  python scripts/generate_monitoring_data.py --base-url http://localhost:5001
  
  # С авторизацией (для админских endpoints)
  python scripts/generate_monitoring_data.py \\
    --base-url http://93.77.186.203:5001 \\
    --admin-username admin \\
    --admin-password ваш_пароль
  
  # Больше запросов, больше параллельных потоков
  python scripts/generate_monitoring_data.py \\
    --base-url http://93.77.186.203:5001 \\
    --num-requests 500 \\
    --concurrent 20
  
  # Непрерывная генерация (для долгосрочного мониторинга)
  python scripts/generate_monitoring_data.py \\
    --base-url http://93.77.186.203:5001 \\
    --continuous \\
    --interval 10 \\
    --batch-size 100
  
  # Подробный вывод
  python scripts/generate_monitoring_data.py \\
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
        default=200,
        help='Количество запросов для генерации (по умолчанию: 200)'
    )
    
    parser.add_argument(
        '--concurrent',
        type=int,
        default=10,
        help='Количество параллельных запросов (по умолчанию: 10, важно для панели Active Requests)'
    )
    
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Непрерывная генерация данных (для долгосрочного мониторинга)'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Интервал между итерациями в секундах (только для --continuous, по умолчанию: 5)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Размер батча запросов для каждой итерации (только для --continuous, по умолчанию: 50)'
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
    generator = MonitoringDataGenerator(
        base_url=args.base_url,
        admin_username=args.admin_username,
        admin_password=args.admin_password
    )
    
    # Запускаем генерацию
    try:
        if args.continuous:
            stop_event = Event()
            run_continuous(
                generator,
                interval=args.interval,
                concurrent=args.concurrent,
                batch_size=args.batch_size,
                verbose=args.verbose,
                stop_event=stop_event
            )
        else:
            run_monitoring_generation(
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
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
