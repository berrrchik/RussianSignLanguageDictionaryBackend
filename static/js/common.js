/**
 * Общие утилиты для административной панели.
 * Используется во всех страницах админки.
 */

// Базовый URL API
const API_BASE = '/api/v1/admin';

/**
 * Получение токена авторизации из localStorage
 */
function getAuthToken() {
    return localStorage.getItem('authToken');
}

/**
 * Проверка авторизации пользователя
 * @returns {boolean} true если авторизован, false иначе
 */
function checkAuth() {
    const token = getAuthToken();
    if (!token) {
        window.location.href = '/admin/login';
        return false;
    }
    return true;
}

/**
 * Выполнение авторизованного API запроса
 * @param {string} url - URL для запроса
 * @param {Object} options - Опции для fetch (method, body, headers и т.д.)
 * @returns {Promise<Response|null>} Response объект или null если не авторизован
 */
async function apiRequest(url, options = {}) {
    const token = getAuthToken();
    if (!token) {
        window.location.href = '/admin/login';
        return null;
    }

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        }
    };

    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    const response = await fetch(url, mergedOptions);
    
    if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/admin/login';
        return null;
    }

    return response;
}

/**
 * Показать уведомление пользователю
 * @param {string} message - Текст уведомления
 * @param {string} type - Тип уведомления ('success', 'error', 'warning')
 */
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

/**
 * Показать ошибку в элементе формы
 * @param {string} elementId - ID элемента для отображения ошибки
 * @param {string} message - Текст ошибки
 */
function showError(elementId, message) {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }
}

/**
 * Скрыть ошибку в элементе формы
 * @param {string} elementId - ID элемента с ошибкой
 */
function hideError(elementId) {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.style.display = 'none';
        errorElement.textContent = '';
    }
}

/**
 * Выход из системы
 */
function logout() {
    if (confirm('Вы уверены, что хотите выйти?')) {
        localStorage.removeItem('authToken');
        window.location.href = '/admin/login';
    }
}

/**
 * Экранирование HTML для безопасной вставки в DOM
 * @param {string} text - Текст для экранирования
 * @returns {string} Экранированный текст
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Закрытие модального окна при клике вне его
 * @param {string} modalId - ID модального окна
 */
function setupModalCloseOnClickOutside(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                const closeFunction = window[`close${modalId.charAt(0).toUpperCase() + modalId.slice(1)}`];
                if (closeFunction && typeof closeFunction === 'function') {
                    closeFunction();
                }
            }
        });
    }
}

// Автоматическая проверка авторизации при загрузке страницы
window.addEventListener('load', () => {
    // Проверка выполняется только если на странице есть функции, требующие авторизации
    // Это позволяет использовать common.js на страницах без авторизации
    if (typeof checkAuth === 'function') {
        // Проверка выполняется в каждом конкретном файле при необходимости
    }
});
