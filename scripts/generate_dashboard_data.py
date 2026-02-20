#!/usr/bin/env python3
"""
Универсальный скрипт для генерации тестовых данных для всех дашбордов Grafana.

Поддерживает генерацию данных для:
1. System Overview - HTTP метрики, производительность
2. Business Metrics - синхронизация, поиск, админ операции
3. Application Logs - логи приложения (автоматически через запросы)
4. Database Metrics - метрики БД (автоматически через запросы)
5. ML Components - метрики SBERT (автоматически через поисковые запросы)
6. Content Statistics - статистика контента (обновляется автоматически)
7. Errors and Warnings - ошибки (генерируются через запросы с ошибками)

Запуск:
    # Для всех дашбордов (минимальная нагрузка для слабой VM)
    python scripts/generate_dashboard_data.py --base-url http://localhost:5001 --dashboard all --num-requests 50 --concurrent 2
    
    # Для конкретного дашборда (ещё меньше нагрузки)
    python scripts/generate_dashboard_data.py --base-url http://localhost:5001 --dashboard system-overview --num-requests 30 --concurrent 1
    
    # С авторизацией (для админских endpoints)
    python scripts/generate_dashboard_data.py \\
        --base-url http://localhost:5001 \\
        --dashboard all \\
        --num-requests 50 \\
        --concurrent 2 \\
        --admin-username admin \\
        --admin-password ваш_пароль
    
    # Для слабой VM: минимальные параметры
    python scripts/generate_dashboard_data.py \\
        --base-url http://localhost:5001 \\
        --dashboard system-overview \\
        --num-requests 20 \\
        --concurrent 1
"""

import argparse
import requests
import time
import random
import sys
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed


class DashboardDataGenerator:
    """Генератор данных для дашбордов Grafana."""
    
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
    
    # ========== Методы для System Overview ==========
    
    def generate_system_overview_data(self, num_requests: int = 200, concurrent: int = 10, verbose: bool = False):
        """Генерация данных для дашборда System Overview."""
        print("📊 Генерация данных для дашборда 'System Overview'...")
        print("   - HTTP Requests Rate")
        print("   - HTTP Request Duration (p50, p95, p99)")
        print("   - HTTP Status Codes")
        print("   - Active Requests\n")
        
        print(f"🚀 Генерация данных для панелей мониторинга")
        print(f"📍 Базовый URL: {self.base_url}")
        print(f"📊 Количество запросов: {num_requests}")
        print(f"⚡ Параллельных потоков: {concurrent}\n")
        
        # Проверка доступности сервера
        print("🔍 Проверка доступности сервера...")
        try:
            test_response = requests.get(f'{self.base_url}/api/v1/sync/check/raw', timeout=5)
            print(f"✅ Сервер доступен (статус: {test_response.status_code})\n")
        except requests.exceptions.ConnectionError:
            print(f"❌ ОШИБКА: Не удалось подключиться к {self.base_url}")
            print("   Убедитесь, что приложение запущено и доступно по указанному адресу.\n")
            return
        except Exception as e:
            print(f"⚠️  Предупреждение: {type(e).__name__}: {str(e)[:100]}\n")
        
        # Авторизация (если указаны credentials)
        if self.admin_username:
            if self.login_admin():
                print("✅ Авторизация успешна\n")
            else:
                print("⚠️  Авторизация не удалась, будут использоваться только публичные endpoints\n")
        
        # Создаем план запросов
        request_functions = []
        search_queries = [
            "привет", "спасибо", "пожалуйста", "извините", "до свидания",
            "как дела", "хорошо", "плохо", "да", "нет", "помощь", "вопрос"
        ]
        
        # GET запросы (50%)
        # Быстрые запросы (sync/check) - 30%
        for _ in range(int(num_requests * 0.30)):
            def make_sync_check():
                return requests.get(f'{self.base_url}/api/v1/sync/check/raw', timeout=5)
            request_functions.append(('GET /sync/check/raw', make_sync_check))
        
        # Медленные запросы (sync/data) - только для больших объёмов
        # Для слабой VM лучше убрать эти запросы, они очень медленные
        if num_requests >= 50:  # Только если достаточно запросов
            for _ in range(int(num_requests * 0.05)):
                def make_sync_data():
                    return requests.get(f'{self.base_url}/api/v1/sync/data/raw', timeout=10)
                request_functions.append(('GET /sync/data/raw', make_sync_data))
        
        if self.admin_token:
            for _ in range(int(num_requests * 0.05)):
                def make_admin_signs():
                    return requests.get(
                        f'{self.base_url}/api/v1/admin/signs',
                        params={'page': 1, 'per_page': 20},
                        headers=self._get_headers(auth=True),
                        timeout=10)
                request_functions.append(('GET /admin/signs', make_admin_signs))
            
            for _ in range(int(num_requests * 0.05)):
                def make_admin_categories():
                    return requests.get(
                        f'{self.base_url}/api/v1/admin/categories',
                        headers=self._get_headers(auth=True),
                        timeout=10)
                request_functions.append(('GET /admin/categories', make_admin_categories))
        
        # POST запросы (25%)
        for _ in range(int(num_requests * 0.20)):
            query = random.choice(search_queries)
            def make_search(q=query):
                return requests.post(
                    f'{self.base_url}/api/v1/search/sbert',
                    json={'text': q, 'limit': 10},
                    headers=self._get_headers(),
                    timeout=10)
            request_functions.append(('POST /search/sbert', make_search))
        
        # Ошибки (25%)
        for _ in range(int(num_requests * 0.10)):
            def make_404():
                return requests.get(f'{self.base_url}/api/v1/nonexistent', timeout=5)
            request_functions.append(('GET /nonexistent (404)', make_404))
        
        for _ in range(int(num_requests * 0.05)):
            def make_405():
                return requests.delete(f'{self.base_url}/api/v1/sync/check/raw', timeout=5)
            request_functions.append(('DELETE /sync/check/raw (405)', make_405))
        
        for _ in range(int(num_requests * 0.05)):
            def make_invalid():
                return requests.post(
                    f'{self.base_url}/api/v1/search/sbert',
                    data='invalid json',
                    headers={'Content-Type': 'application/json'},
                    timeout=5)
            request_functions.append(('POST /search/sbert (invalid)', make_invalid))
        
        if not self.admin_token:
            for _ in range(int(num_requests * 0.05)):
                def make_401():
                    return requests.get(
                        f'{self.base_url}/api/v1/admin/signs',
                        headers=self._get_headers(auth=False),
                        timeout=5)
                request_functions.append(('GET /admin/signs (401)', make_401))
        
        random.shuffle(request_functions)
        
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
                    if verbose:
                        print(f"  ✅ {name}: {status_code}")
                else:
                    stats['errors'] += 1
                    if verbose:
                        print(f"  ⚠️  {name}: {status_code}")
                
                return response
            except requests.exceptions.ConnectionError as e:
                stats['total'] += 1
                stats['errors'] += 1
                stats['status_codes']['CONN_ERROR'] = stats['status_codes'].get('CONN_ERROR', 0) + 1
                if verbose:
                    print(f"  ❌ {name}: Connection Error - {str(e)[:100]}")
                return None
            except requests.exceptions.Timeout as e:
                stats['total'] += 1
                stats['errors'] += 1
                stats['status_codes']['TIMEOUT'] = stats['status_codes'].get('TIMEOUT', 0) + 1
                if verbose:
                    print(f"  ⏱️  {name}: Timeout - {str(e)[:100]}")
                return None
            except requests.exceptions.RequestException as e:
                stats['total'] += 1
                stats['errors'] += 1
                if hasattr(e, 'response') and e.response is not None:
                    status_code = e.response.status_code
                    stats['status_codes'][status_code] = stats['status_codes'].get(status_code, 0) + 1
                else:
                    stats['status_codes']['REQ_ERROR'] = stats['status_codes'].get('REQ_ERROR', 0) + 1
                if verbose:
                    print(f"  ⚠️  {name}: Request Error - {str(e)[:100]}")
                return None
            except Exception as e:
                stats['total'] += 1
                stats['errors'] += 1
                stats['status_codes']['UNKNOWN'] = stats['status_codes'].get('UNKNOWN', 0) + 1
                if verbose:
                    print(f"  ❌ {name}: Unknown Error - {type(e).__name__}: {str(e)[:100]}")
                return None
        
        # Выполняем запросы параллельно
        completed = 0
        total = len(request_functions)
        
        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = [
                executor.submit(execute_request, name, func)
                for name, func in request_functions
            ]
            
            for future in as_completed(futures):
                try:
                    future.result()
                    completed += 1
                    if completed % 5 == 0 or completed == total:
                        print(f"  Прогресс: {completed}/{total} запросов выполнено...")
                except Exception as e:
                    completed += 1
                    if verbose:
                        print(f"  ⚠️  Ошибка выполнения: {type(e).__name__}: {str(e)[:100]}")
                    pass
        
        elapsed_time = time.time() - start_time
        
        # Выводим статистику
        print("\n" + "="*60)
        print("📊 Статистика выполнения:")
        print("="*60)
        print(f"Всего запросов: {stats['total']}")
        print(f"Успешных (2xx/3xx): {stats['success']}")
        print(f"Ошибок (4xx/5xx): {stats['errors']}")
        print(f"Время выполнения: {elapsed_time:.2f} сек")
        if stats['total'] > 0:
            print(f"Запросов в секунду: {stats['total'] / elapsed_time:.2f}")
        
        print("\n📈 Статус коды:")
        for code in sorted(stats['status_codes'].keys()):
            count = stats['status_codes'][code]
            percentage = (count / stats['total']) * 100 if stats['total'] > 0 else 0
            print(f"  {code}: {count} ({percentage:.1f}%)")
        
        print("\n🔧 HTTP методы:")
        for method in sorted(stats['methods'].keys()):
            count = stats['methods'][method]
            percentage = (count / stats['total']) * 100 if stats['total'] > 0 else 0
            print(f"  {method}: {count} ({percentage:.1f}%)")
        
        print("\n✅ Генерация данных завершена!")
        print("💡 Проверьте панели в Grafana:")
        print("   - HTTP Requests Rate")
        print("   - HTTP Request Duration (p50, p95, p99)")
        print("   - HTTP Status Codes")
        print("   - Active Requests\n")
    
    # ========== Методы для Business Metrics ==========
    
    def generate_business_metrics_data(self, num_requests: int = 300, concurrent: int = 5, verbose: bool = False):
        """Генерация данных для дашборда Business Metrics."""
        print("📊 Генерация данных для дашборда 'Business Metrics'...")
        print("   - Sync Check Requests")
        print("   - Full Sync Requests")
        print("   - Search Requests")
        print("   - Admin Operations\n")
        
        request_functions = []
        
        # Синхронизация (40%)
        for _ in range(int(num_requests * 0.30)):
            request_functions.append(('sync_check', lambda: requests.get(
                f'{self.base_url}/api/v1/sync/check/raw', timeout=10)))
        
        for _ in range(int(num_requests * 0.10)):
            request_functions.append(('sync_data', lambda: requests.get(
                f'{self.base_url}/api/v1/sync/data/raw', timeout=30)))
        
        # Поиск (30%)
        search_queries = [
            "привет", "спасибо", "пожалуйста", "извините", "до свидания",
            "как дела", "хорошо", "плохо", "да", "нет", "помощь", "вопрос"
        ]
        for _ in range(int(num_requests * 0.30)):
            query = random.choice(search_queries)
            request_functions.append(('search', lambda q=query: requests.post(
                f'{self.base_url}/api/v1/search/sbert',
                json={'text': q, 'limit': 10},
                headers=self._get_headers(),
                timeout=15)))
        
        # Админ операции (30%, только если авторизованы)
        if self.admin_token:
            for _ in range(int(num_requests * 0.10)):
                request_functions.append(('admin_signs', lambda: requests.get(
                    f'{self.base_url}/api/v1/admin/signs',
                    params={'page': 1, 'per_page': 20},
                    headers=self._get_headers(auth=True),
                    timeout=10)))
            
            for _ in range(int(num_requests * 0.10)):
                request_functions.append(('admin_categories', lambda: requests.get(
                    f'{self.base_url}/api/v1/admin/categories',
                    headers=self._get_headers(auth=True),
                    timeout=10)))
            
            for _ in range(int(num_requests * 0.10)):
                request_functions.append(('admin_lessons', lambda: requests.get(
                    f'{self.base_url}/api/v1/admin/lessons',
                    headers=self._get_headers(auth=True),
                    timeout=10)))
        
        random.shuffle(request_functions)
        
        # Выполняем запросы
        stats = {'total': 0, 'success': 0, 'errors': 0}
        start_time = time.time()
        
        def execute_request(name: str, func):
            try:
                response = func()
                stats['total'] += 1
                if 200 <= response.status_code < 400:
                    stats['success'] += 1
                else:
                    stats['errors'] += 1
                return response
            except Exception:
                stats['total'] += 1
                stats['errors'] += 1
                return None
        
        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = [
                executor.submit(execute_request, name, func)
                for name, func in request_functions
            ]
            for future in as_completed(futures):
                future.result()
        
        elapsed = time.time() - start_time
        print(f"✅ Выполнено {stats['total']} запросов за {elapsed:.2f} сек")
        print(f"   Успешных: {stats['success']}, Ошибок: {stats['errors']}\n")
    
    # ========== Методы для Errors and Warnings ==========
    
    def generate_errors_data(self, num_requests: int = 100, concurrent: int = 5, verbose: bool = False):
        """Генерация данных для дашборда Errors and Warnings."""
        print("📊 Генерация данных для дашборда 'Errors and Warnings'...")
        print("   - HTTP 5xx Error Rate")
        print("   - Error Logs")
        print("   - Database Connection Errors")
        print("   - SBERT Errors\n")
        
        request_functions = []
        
        # 4xx ошибки (40%)
        for _ in range(int(num_requests * 0.20)):
            request_functions.append(('404', lambda: requests.get(
                f'{self.base_url}/api/v1/nonexistent', timeout=5)))
        
        for _ in range(int(num_requests * 0.10)):
            request_functions.append(('401', lambda: requests.get(
                f'{self.base_url}/api/v1/admin/signs',
                headers=self._get_headers(auth=False),
                timeout=5)))
        
        for _ in range(int(num_requests * 0.10)):
            request_functions.append(('405', lambda: requests.delete(
                f'{self.base_url}/api/v1/sync/check/raw', timeout=5)))
        
        # 5xx ошибки (30%)
        for _ in range(int(num_requests * 0.15)):
            request_functions.append(('400', lambda: requests.post(
                f'{self.base_url}/api/v1/search/sbert',
                data='invalid json',
                headers={'Content-Type': 'application/json'},
                timeout=5)))
        
        for _ in range(int(num_requests * 0.15)):
            request_functions.append(('500', lambda: requests.post(
                f'{self.base_url}/api/v1/search/sbert',
                json={'text': 'x' * 10000, 'limit': 10},
                headers=self._get_headers(),
                timeout=5)))
        
        # Успешные запросы (30%) - для контраста
        for _ in range(int(num_requests * 0.30)):
            request_functions.append(('200', lambda: requests.get(
                f'{self.base_url}/api/v1/sync/check/raw', timeout=10)))
        
        random.shuffle(request_functions)
        
        # Выполняем запросы
        stats = {'total': 0, 'success': 0, 'errors': 0, 'status_codes': {}}
        start_time = time.time()
        
        def execute_request(name: str, func):
            try:
                response = func()
                stats['total'] += 1
                status_code = response.status_code
                stats['status_codes'][status_code] = stats['status_codes'].get(status_code, 0) + 1
                if 200 <= status_code < 400:
                    stats['success'] += 1
                else:
                    stats['errors'] += 1
                return response
            except Exception:
                stats['total'] += 1
                stats['errors'] += 1
                stats['status_codes'][500] = stats['status_codes'].get(500, 0) + 1
                return None
        
        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = [
                executor.submit(execute_request, name, func)
                for name, func in request_functions
            ]
            for future in as_completed(futures):
                future.result()
        
        elapsed = time.time() - start_time
        print(f"✅ Выполнено {stats['total']} запросов за {elapsed:.2f} сек")
        print(f"   Успешных: {stats['success']}, Ошибок: {stats['errors']}")
        print("\n📈 Статус коды:")
        for code in sorted(stats['status_codes'].keys()):
            print(f"   {code}: {stats['status_codes'][code]}")
        print()
    
    # ========== Универсальный метод ==========
    
    def generate_all_data(self, num_requests: int = 500, concurrent: int = 10, verbose: bool = False):
        """Генерация данных для всех дашбордов."""
        print("="*60)
        print("🚀 Генерация данных для всех дашбордов")
        print("="*60 + "\n")
        
        # Авторизация
        if self.admin_username:
            if self.login_admin():
                print("✅ Авторизация успешна\n")
            else:
                print("⚠️  Авторизация не удалась, будут использоваться только публичные endpoints\n")
        
        # System Overview
        self.generate_system_overview_data(num_requests // 2, concurrent, verbose)
        time.sleep(2)
        
        # Business Metrics
        self.generate_business_metrics_data(num_requests, concurrent, verbose)
        time.sleep(2)
        
        # Errors and Warnings
        self.generate_errors_data(num_requests // 3, concurrent)
        
        print("="*60)
        print("✅ Генерация данных для всех дашбордов завершена!")
        print("="*60)
        print("\n💡 Проверьте дашборды в Grafana:")
        print("   - System Overview")
        print("   - Business Metrics")
        print("   - Application Logs (логи появятся автоматически)")
        print("   - Database Metrics (метрики обновятся автоматически)")
        print("   - ML Components (метрики обновятся через поисковые запросы)")
        print("   - Content Statistics (обновляется автоматически)")
        print("   - Errors and Warnings")


def main():
    parser = argparse.ArgumentParser(
        description='Генерация тестовых данных для дашбордов Grafana',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Для слабой VM: минимальная нагрузка (рекомендуется)
  python scripts/generate_dashboard_data.py \\
    --base-url http://localhost:5001 \\
    --dashboard system-overview \\
    --num-requests 30 \\
    --concurrent 1
  
  # Для всех дашбордов (умеренная нагрузка)
  python scripts/generate_dashboard_data.py \\
    --base-url http://localhost:5001 \\
    --dashboard all \\
    --num-requests 50 \\
    --concurrent 2
  
  # Для конкретного дашборда
  python scripts/generate_dashboard_data.py \\
    --base-url http://localhost:5001 \\
    --dashboard system-overview \\
    --num-requests 30 \\
    --concurrent 1
  
  python scripts/generate_dashboard_data.py \\
    --base-url http://localhost:5001 \\
    --dashboard business-metrics \\
    --num-requests 30 \\
    --concurrent 1
  
  python scripts/generate_dashboard_data.py \\
    --base-url http://localhost:5001 \\
    --dashboard errors \\
    --num-requests 20 \\
    --concurrent 1
  
  # С авторизацией (для админских endpoints)
  python scripts/generate_dashboard_data.py \\
    --base-url http://localhost:5001 \\
    --dashboard all \\
    --num-requests 50 \\
    --concurrent 2 \\
    --admin-username admin \\
    --admin-password ваш_пароль
  
  # Для мощной VM: больше запросов
  python scripts/generate_dashboard_data.py \\
    --base-url http://localhost:5001 \\
    --dashboard all \\
    --num-requests 500 \\
    --concurrent 10
        """
    )
    
    parser.add_argument(
        '--base-url',
        type=str,
        required=True,
        help='Базовый URL API (например: http://localhost:5001)'
    )
    
    parser.add_argument(
        '--dashboard',
        type=str,
        required=True,
        choices=['all', 'system-overview', 'business-metrics', 'errors'],
        help='Дашборд для генерации данных (all = все дашборды)'
    )
    
    parser.add_argument(
        '--admin-username',
        type=str,
        default=None,
        help='Имя пользователя администратора'
    )
    
    parser.add_argument(
        '--admin-password',
        type=str,
        default=None,
        help='Пароль администратора'
    )
    
    parser.add_argument(
        '--num-requests',
        type=int,
        default=500,
        help='Количество запросов (по умолчанию: 500)'
    )
    
    parser.add_argument(
        '--concurrent',
        type=int,
        default=10,
        help='Количество параллельных запросов (по умолчанию: 10)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Подробный вывод (показывать детали каждого запроса)'
    )
    
    args = parser.parse_args()
    
    if not args.base_url.startswith(('http://', 'https://')):
        print("❌ Ошибка: base-url должен начинаться с http:// или https://")
        sys.exit(1)
    
    generator = DashboardDataGenerator(
        base_url=args.base_url,
        admin_username=args.admin_username,
        admin_password=args.admin_password
    )
    
    try:
        if args.dashboard == 'all':
            generator.generate_all_data(args.num_requests, args.concurrent, args.verbose)
        elif args.dashboard == 'system-overview':
            generator.generate_system_overview_data(args.num_requests, args.concurrent, args.verbose)
        elif args.dashboard == 'business-metrics':
            generator.generate_business_metrics_data(args.num_requests, args.concurrent, args.verbose)
        elif args.dashboard == 'errors':
            generator.generate_errors_data(args.num_requests // 3, args.concurrent, args.verbose)
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
