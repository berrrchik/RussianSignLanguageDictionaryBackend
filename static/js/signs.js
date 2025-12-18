// Глобальные переменные
let allSigns = [];
let allCategories = [];
let currentPage = 1;
let perPage = 50;
let currentSignId = null;
let searchTimeout = null;

// Проверка авторизации при загрузке
window.addEventListener('load', () => {
    const token = localStorage.getItem('authToken');
    if (!token) {
        window.location.href = '/admin/login';
        return;
    }
    loadCategories();
    loadSigns();
});

// Функция выхода
function logout() {
    if (confirm('Вы уверены, что хотите выйти?')) {
        localStorage.removeItem('authToken');
        window.location.href = '/admin/login';
    }
}

// Утилиты для API запросов
async function apiRequest(url, options = {}) {
    const token = localStorage.getItem('authToken');
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

// Показать уведомление
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Показать/скрыть индикатор загрузки (только в области таблицы)
function showLoading() {
    const tbody = document.getElementById('signsTableBody');
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem;"><div class="loading" style="margin: 0 auto; width: 20px; height: 20px;"></div> Загрузка...</td></tr>';
    }
}

function hideLoading() {
    // Индикатор скрывается автоматически при обновлении таблицы через renderSigns()
}

// Загрузка категорий
async function loadCategories() {
    try {
        const response = await apiRequest('/api/v1/admin/categories');
        if (!response) return;
        
        const data = await response.json();
        if (data.success) {
            allCategories = data.data;
            const categoryFilter = document.getElementById('categoryFilter');
            categoryFilter.innerHTML = '<option value="">Все категории</option>';
            allCategories.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.id;
                option.textContent = cat.name;
                categoryFilter.appendChild(option);
            });
            
            // Заполнить select в модальных окнах
            fillCategorySelects();
        }
    } catch (error) {
        console.error('Ошибка загрузки категорий:', error);
    }
}

function fillCategorySelects() {
    const selects = ['signCategory', 'editSignCategory'];
    selects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            select.innerHTML = '<option value="">Выберите категорию</option>';
            allCategories.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.id;
                option.textContent = cat.name;
                select.appendChild(option);
            });
        }
    });
}

// Загрузка жестов
async function loadSigns(page = 1) {
    await loadSignsWithFilters(page, '', '');
}

// Загрузка жестов с фильтрами
async function loadSignsWithFilters(page = 1, searchTerm = '', categoryFilter = '') {
    try {
        showLoading();
        const baseUrl = window.location.origin;
        let url = `${baseUrl}/api/v1/admin/signs?page=${page}&per_page=${perPage}`;
        
        if (categoryFilter) {
            url += `&category_id=${encodeURIComponent(categoryFilter)}`;
        }
        
        if (searchTerm) {
            url += `&search=${encodeURIComponent(searchTerm)}`;
        }
        
        const response = await apiRequest(url);
        if (!response) return;
        
        const data = await response.json();
        if (data.success) {
            allSigns = data.data.signs;
            currentPage = page;
            renderSigns();
            renderPagination(data.data.pagination);
        } else {
            showNotification(data.error?.message || 'Ошибка загрузки жестов', 'error');
        }
    } catch (error) {
        console.error('Ошибка загрузки жестов:', error);
        showNotification('Ошибка соединения с сервером', 'error');
    } finally {
        hideLoading();
    }
}

// Фильтрация жестов
function filterSigns() {
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }
    
    searchTimeout = setTimeout(() => {
        const searchTerm = document.getElementById('searchInput').value.trim();
        const categoryFilter = document.getElementById('categoryFilter').value;
        
        // Если есть поисковый запрос или фильтр по категории, делаем запрос к API
        if (searchTerm || categoryFilter) {
            loadSignsWithFilters(1, searchTerm, categoryFilter);
        } else {
            // Если нет фильтров, загружаем обычный список
            loadSigns(1);
        }
    }, 300);
}


// Рендеринг жестов
function renderSigns() {
    const tbody = document.getElementById('signsTableBody');
    
    if (!tbody) return;
    
    // Используем visibility вместо opacity для избежания пересчета layout
    tbody.style.visibility = 'hidden';
    tbody.style.transition = 'none'; // Убираем transition для мгновенного скрытия
    
    // Небольшая задержка для завершения текущего рендера
    requestAnimationFrame(() => {
        if (allSigns.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem;">Жесты не найдены</td></tr>';
        } else {
            tbody.innerHTML = allSigns.map(sign => {
                const category = allCategories.find(c => c.id === sign.category_id);
                return `
                    <tr>
                        <td>${sign.id}</td>
                        <td>${sign.word}</td>
                        <td>${category ? category.name : 'Не указана'}</td>
                        <td>${sign.videos_count || 0}</td>
                        <td>
                            <button class="btn btn-primary" style="padding: 0.25rem 0.5rem; font-size: 0.9rem;" onclick="openEditSignModal('${sign.id}')">Редактировать</button>
                            <button class="btn btn-danger" style="padding: 0.25rem 0.5rem; font-size: 0.9rem;" onclick="deleteSign('${sign.id}')">Удалить</button>
                        </td>
                    </tr>
                `;
            }).join('');
        }
        
        // Показываем содержимое после обновления
        requestAnimationFrame(() => {
            tbody.style.visibility = 'visible';
        });
    });
}

// Рендеринг пагинации
function renderPagination(pagination) {
    const paginationDiv = document.getElementById('pagination');
    if (pagination.pages <= 1) {
        paginationDiv.innerHTML = '';
        return;
    }
    
    const searchTerm = document.getElementById('searchInput').value.trim();
    const categoryFilter = document.getElementById('categoryFilter').value;
    
    // Экранирование для безопасной вставки в HTML
    const escapedSearchTerm = searchTerm.replace(/'/g, "\\'");
    const escapedCategoryFilter = categoryFilter.replace(/'/g, "\\'");
    
    let html = '';
    if (pagination.page > 1) {
        html += `<button onclick="loadSignsWithFilters(${pagination.page - 1}, '${escapedSearchTerm}', '${escapedCategoryFilter}')">Предыдущая</button>`;
    }
    
    for (let i = 1; i <= pagination.pages; i++) {
        if (i === pagination.page) {
            html += `<button class="active" disabled>${i}</button>`;
        } else if (i === 1 || i === pagination.pages || (i >= pagination.page - 2 && i <= pagination.page + 2)) {
            html += `<button onclick="loadSignsWithFilters(${i}, '${escapedSearchTerm}', '${escapedCategoryFilter}')">${i}</button>`;
        } else if (i === pagination.page - 3 || i === pagination.page + 3) {
            html += `<button disabled>...</button>`;
        }
    }
    
    if (pagination.page < pagination.pages) {
        html += `<button onclick="loadSignsWithFilters(${pagination.page + 1}, '${escapedSearchTerm}', '${escapedCategoryFilter}')">Следующая</button>`;
    }
    
    paginationDiv.innerHTML = html;
}

// Модальное окно создания жеста
function openCreateSignModal() {
    document.getElementById('signModalTitle').textContent = 'Создать жест';
    document.getElementById('signForm').reset();
    document.getElementById('signId').value = '';
    document.getElementById('signFormError').style.display = 'none';
    document.getElementById('videoFieldsContainer').innerHTML = '';
    addVideoField();
    document.getElementById('signModal').classList.add('show');
}

function addVideoField() {
    const container = document.getElementById('videoFieldsContainer');
    const existingFields = container.querySelectorAll('.video-field-item');
    const nextNumber = existingFields.length + 1;
    
    const videoField = document.createElement('div');
    videoField.className = 'video-field-item';
    videoField.style.cssText = 'border: 1px solid #ddd; border-radius: 4px; padding: 1rem; margin-bottom: 1rem; background: #f9f9f9;';
    videoField.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <strong>Видео ${nextNumber}</strong>
            <button type="button" class="btn btn-danger" onclick="removeVideoField(this)" style="padding: 0.25rem 0.5rem; font-size: 0.9rem;">Удалить</button>
        </div>
        <div class="form-group" style="margin-bottom: 0.5rem;">
            <label>Видео файл (MP4, макс. 50MB) <span class="required">*</span></label>
            <input type="file" class="video-file-input" accept="video/mp4" required>
        </div>
        <div class="form-group" style="margin-bottom: 0.5rem;">
            <label>Описание контекста <span class="required">*</span></label>
            <textarea class="video-context-input" required></textarea>
        </div>
        <div class="form-group">
            <label>Порядок</label>
            <input type="number" class="video-order-input" value="${nextNumber}" min="1">
        </div>
    `;
    container.appendChild(videoField);
    updateVideoNumbers();
}

function removeVideoField(button) {
    const container = document.getElementById('videoFieldsContainer');
    const fields = container.querySelectorAll('.video-field-item');
    
    if (fields.length <= 1) {
        showNotification('Хотя бы одно видео должно быть обязательно', 'error');
        return;
    }
    
    button.closest('.video-field-item').remove();
    updateVideoNumbers();
}

function updateVideoNumbers() {
    const container = document.getElementById('videoFieldsContainer');
    const fields = container.querySelectorAll('.video-field-item');
    fields.forEach((field, index) => {
        const title = field.querySelector('strong');
        const orderInput = field.querySelector('.video-order-input');
        if (title) {
            title.textContent = `Видео ${index + 1}`;
        }
        if (orderInput) {
            orderInput.value = index + 1;
        }
    });
}

function closeSignModal() {
    document.getElementById('signModal').classList.remove('show');
}

async function saveSign(event) {
    event.preventDefault();
    
    const isEdit = !!document.getElementById('signId').value;
    
    const formData = {
        id: isEdit ? document.getElementById('signId').value : generateSignId(),
        word: document.getElementById('signWord').value,
        description: document.getElementById('signDescription').value,
        category_id: document.getElementById('signCategory').value
    };
    
    if (!formData.word || !formData.category_id) {
        showError('signFormError', 'Заполните все обязательные поля');
        return;
    }
    
    const videoFields = document.querySelectorAll('.video-field-item');
    const videos = [];
    if (!isEdit) {
        if (videoFields.length === 0) {
            showError('signFormError', 'Необходимо добавить хотя бы одно видео');
            return;
        }
        for (const field of videoFields) {
            const fileInput = field.querySelector('.video-file-input');
            const contextInput = field.querySelector('.video-context-input');
            const orderInput = field.querySelector('.video-order-input');
            
            if (fileInput.files.length === 0 || !contextInput.value.trim()) {
                showError('signFormError', 'Заполните все поля для видео');
                return;
            }
            
            const file = fileInput.files[0];
            
            // Валидация файла
            if (!file.name.endsWith('.mp4')) {
                showError('signFormError', 'Только файлы MP4 разрешены');
                return;
            }
            
            if (file.size > 50 * 1024 * 1024) {
                showError('signFormError', 'Размер файла не должен превышать 50MB');
                return;
            }
            
            const orderValue = parseInt(orderInput.value) || 1;
            videos.push({
                file: file,
                context_description: contextInput.value.trim(),
                order: Math.max(0, orderValue - 1)  
            });
        }
    }
    
    const submitButton = document.getElementById('signFormSubmit');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="loading"></span> Сохранение...';
    
    try {
        const url = isEdit 
            ? `/api/v1/admin/signs/${formData.id}`
            : '/api/v1/admin/signs';
        const method = isEdit ? 'PUT' : 'POST';
        
        const response = await apiRequest(url, {
            method: method,
            body: JSON.stringify(formData)
        });
        
        if (!response) return;
        
        const data = await response.json();
        if (data.success) {
            const createdSignId = data.data.id || formData.id;
            
            if (!isEdit && videos.length > 0) {
                const videoResults = {
                    success: [],
                    failed: []
                };
                
                for (let i = 0; i < videos.length; i++) {
                    const video = videos[i];
                    try {
                        const formDataVideo = new FormData();
                        formDataVideo.append('file', video.file);
                        formDataVideo.append('context_description', video.context_description);
                        formDataVideo.append('order', video.order);
                        
                        const token = localStorage.getItem('authToken');
                        const videoResponse = await fetch(`${window.location.origin}/api/v1/admin/signs/${createdSignId}/videos`, {
                            method: 'POST',
                            headers: {
                                'Authorization': `Bearer ${token}`
                            },
                            body: formDataVideo
                        });
                        
                        if (!videoResponse.ok) {
                            const videoData = await videoResponse.json();
                            const errorMessage = videoData.error?.message || `Ошибка загрузки видео ${i + 1}`;
                            videoResults.failed.push({
                                index: i + 1,
                                fileName: video.file.name,
                                error: errorMessage
                            });
                            console.error('Ошибка загрузки видео:', videoData);
                        } else {
                            videoResults.success.push({
                                index: i + 1,
                                fileName: video.file.name
                            });
                        }
                    } catch (videoError) {
                        videoResults.failed.push({
                            index: i + 1,
                            fileName: video.file.name,
                            error: videoError.message || 'Ошибка соединения с сервером'
                        });
                        console.error('Ошибка загрузки видео:', videoError);
                    }
                }
                
                // Показываем результаты загрузки видео
                if (videoResults.failed.length === 0) {
                    // Все видео загружены успешно
                    showNotification('Жест создан', 'success');
                    closeSignModal();
                    loadSigns(currentPage);
                } else {
                    // Есть ошибки загрузки видео
                    const errorDetails = videoResults.failed.map(v => 
                        `Видео ${v.index} (${v.fileName}): ${v.error}`
                    ).join('; ');
                    
                    // Логируем детали в консоль
                    console.error('Детали ошибок загрузки видео:', errorDetails);
                    
                    if (videoResults.success.length === 0) {
                        // Ни одно видео не загрузилось - удаляем созданный жест
                        try {
                            await apiRequest(`/api/v1/admin/signs/${createdSignId}`, {
                                method: 'DELETE'
                            });
                        } catch (deleteError) {
                            console.error('Ошибка удаления жеста после неудачной загрузки видео:', deleteError);
                        }
                        
                        showError('signFormError', `Не удалось загрузить видео. Жест не создан. Ошибка: ${videoResults.failed[0].error}`);
                        return;
                    } else {
                        // Частичная загрузка - хотя бы одно видео загружено
                        showNotification(
                            `Жест создан. Загружено видео: ${videoResults.success.length}/${videos.length}. Не удалось загрузить: ${videoResults.failed.length}. Проверьте консоль для деталей.`,
                            'error'
                        );
                        closeSignModal();
                        loadSigns(currentPage);
                    }
                }
            } else {
                // Режим редактирования без загрузки новых видео
                showNotification('Жест обновлен', 'success');
                closeSignModal();
                loadSigns(currentPage);
            }
        } else {
            showError('signFormError', data.error?.message || 'Ошибка сохранения');
        }
    } catch (error) {
        console.error('Ошибка сохранения жеста:', error);
        showError('signFormError', 'Ошибка соединения с сервером');
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Сохранить';
    }
}

function generateSignId() {
    return 'sign_' + Date.now();
}

function showError(elementId, message) {
    const errorElement = document.getElementById(elementId);
    errorElement.textContent = message;
    errorElement.style.display = 'block';
}

// Модальное окно редактирования жеста
async function openEditSignModal(signId) {
    currentSignId = signId;
    
    // Показываем модальное окно сразу
    document.getElementById('editSignModal').classList.add('show');
    
    // Показываем индикатор загрузки в таблицах
    document.getElementById('videosTableBody').innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 1rem;"><div class="loading" style="margin: 0 auto; width: 20px; height: 20px;"></div> Загрузка...</td></tr>';
    document.getElementById('synonymsTableBody').innerHTML = '<tr><td colspan="2" style="text-align: center; padding: 1rem;"><div class="loading" style="margin: 0 auto; width: 20px; height: 20px;"></div> Загрузка...</td></tr>';
    
    try {
        const response = await apiRequest(`/api/v1/admin/signs/${signId}`);
        if (!response) {
            document.getElementById('editSignModal').classList.remove('show');
            return;
        }
        
        const data = await response.json();
        if (data.success) {
            const sign = data.data;
            document.getElementById('editSignId').value = sign.id;
            document.getElementById('editSignWord').value = sign.word || '';
            document.getElementById('editSignDescription').value = sign.description || '';
            document.getElementById('editSignCategory').value = sign.category_id;
            
            document.getElementById('editSignModalTitle').textContent = `Редактировать: ${sign.word}`;
            
            // Заполняем категории если еще не заполнены
            const categorySelect = document.getElementById('editSignCategory');
            if (categorySelect.options.length <= 1) {
                fillCategorySelects();
            }
            categorySelect.value = sign.category_id;
            
            loadVideos(signId);
            loadSynonyms(signId);
        } else {
            document.getElementById('editSignModal').classList.remove('show');
            showNotification(data.error?.message || 'Ошибка загрузки жеста', 'error');
        }
    } catch (error) {
        console.error('Ошибка загрузки жеста:', error);
        document.getElementById('editSignModal').classList.remove('show');
        showNotification('Ошибка соединения с сервером', 'error');
    }
}

function closeEditSignModal() {
    document.getElementById('editSignModal').classList.remove('show');
    currentSignId = null;
}

// Обновление жеста
async function updateSign(event) {
    event.preventDefault();
    
    // Проверяем наличие видео
    const videosRows = document.querySelectorAll('#videosTableBody tr:not(:has(td[colspan]))');
    if (videosRows.length === 0) {
        showError('editSignFormError', '⚠️ Жест должен иметь хотя бы одно видео. Пожалуйста, загрузите видео.');
        return;
    }
    
    const formData = {
        word: document.getElementById('editSignWord').value,
        description: document.getElementById('editSignDescription').value,
        category_id: document.getElementById('editSignCategory').value
    };
    
    const signId = document.getElementById('editSignId').value;
    
    try {
        const response = await apiRequest(`/api/v1/admin/signs/${signId}`, {
            method: 'PUT',
            body: JSON.stringify(formData)
        });
        
        if (!response) return;
        
        const data = await response.json();
        if (data.success) {
            showNotification('Жест обновлен', 'success');
            closeEditSignModal();
            loadSigns(currentPage);
        } else {
            showError('editSignFormError', data.error?.message || 'Ошибка обновления');
        }
    } catch (error) {
        console.error('Ошибка обновления жеста:', error);
        showError('editSignFormError', 'Ошибка соединения с сервером');
    }
}

// Удаление жеста
async function deleteSign(signId) {
    if (!confirm('Вы уверены, что хотите удалить этот жест? Все связанные видео и синонимы также будут удалены.')) {
        return;
    }
    
    try {
        const response = await apiRequest(`/api/v1/admin/signs/${signId}`, {
            method: 'DELETE'
        });
        
        if (!response) return;
        
        const data = await response.json();
        if (data.success) {
            showNotification('Жест удален', 'success');
            loadSigns(currentPage);
        } else {
            showNotification(data.error?.message || 'Ошибка удаления', 'error');
        }
    } catch (error) {
        console.error('Ошибка удаления жеста:', error);
        showNotification('Ошибка соединения с сервером', 'error');
    }
}

// Управление видео
async function loadVideos(signId) {
    try {
        const response = await apiRequest(`/api/v1/admin/signs/${signId}/videos`);
        if (!response) return;
        
        const data = await response.json();
        if (data.success) {
            renderVideos(data.data);
        }
    } catch (error) {
        console.error('Ошибка загрузки видео:', error);
    }
}

function renderVideos(videos) {
    const tbody = document.getElementById('videosTableBody');
    if (videos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 1rem; color: #dc3545;"><strong>⚠️ Видео не найдены. Необходимо загрузить хотя бы одно видео!</strong></td></tr>';
        updateEditSignSaveButton();
        return;
    }
    
    const sortedVideos = [...videos].sort((a, b) => (a.order || 0) - (b.order || 0));
    
    tbody.innerHTML = sortedVideos.map(video => `
        <tr>
            <td>${(video.order || 0) + 1}</td>
            <td>${video.context_description}</td>
            <td><a href="${video.url}" target="_blank">${video.url}</a></td>
            <td>
                <button class="btn btn-primary" style="padding: 0.25rem 0.5rem; font-size: 0.9rem;" onclick="viewVideo('${video.url}', '${video.context_description.replace(/'/g, "\\'")}')">Просмотреть</button>
                <button class="btn btn-danger" style="padding: 0.25rem 0.5rem; font-size: 0.9rem;" onclick="deleteVideo(${video.id})">Удалить</button>
            </td>
        </tr>
    `).join('');
    
    updateEditSignSaveButton();
}

// Обновление состояния кнопки сохранения в зависимости от наличия видео
function updateEditSignSaveButton() {
    const videosRows = document.querySelectorAll('#videosTableBody tr:not(:has(td[colspan]))');
    const saveButton = document.querySelector('#editSignForm button[type="submit"]');
    const errorElement = document.getElementById('editSignFormError');
    
    if (videosRows.length === 0) {
        if (saveButton) {
            saveButton.disabled = true;
            saveButton.title = 'Необходимо загрузить хотя бы одно видео';
        }
        if (errorElement) {
            errorElement.textContent = '⚠️ Жест должен иметь хотя бы одно видео. Пожалуйста, загрузите видео.';
            errorElement.style.display = 'block';
        }
    } else {
        if (saveButton) {
            saveButton.disabled = false;
            saveButton.title = '';
        }
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }
}

function openAddVideoModal() {
    document.getElementById('videoForm').reset();
    const existingVideos = document.querySelectorAll('#videosTableBody tr:not(:has(td[colspan]))');
    const nextOrder = existingVideos.length + 1;
    document.getElementById('videoOrder').value = nextOrder;
    document.getElementById('videoFormError').style.display = 'none';
    document.getElementById('videoModal').classList.add('show');
}

function closeVideoModal() {
    document.getElementById('videoModal').classList.remove('show');
}

async function uploadVideo(event) {
    event.preventDefault();
    
    const fileInput = document.getElementById('videoFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('videoFormError', 'Выберите файл');
        return;
    }
    
    // Валидация файла
    if (!file.name.endsWith('.mp4')) {
        showError('videoFormError', 'Только файлы MP4 разрешены');
        return;
    }
    
    if (file.size > 50 * 1024 * 1024) {
        showError('videoFormError', 'Размер файла не должен превышать 50MB');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('context_description', document.getElementById('videoContextDescription').value);
    const orderValue = parseInt(document.getElementById('videoOrder').value) || 1;
    formData.append('order', Math.max(0, orderValue - 1));
    
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="loading"></span> Загрузка...';
    
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch(`/api/v1/admin/signs/${currentSignId}/videos`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        
        if (response.status === 401) {
            window.location.href = '/admin/login';
            return;
        }
        
        const data = await response.json();
        if (data.success) {
            showNotification('Видео загружено', 'success');
            closeVideoModal();
            await loadVideos(currentSignId);
            updateEditSignSaveButton();
        } else {
            showError('videoFormError', data.error?.message || 'Ошибка загрузки видео');
        }
    } catch (error) {
        console.error('Ошибка загрузки видео:', error);
        showError('videoFormError', 'Ошибка соединения с сервером');
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Загрузить';
    }
}

function viewVideo(url, description) {
    document.getElementById('viewVideoPlayer').src = url;
    document.getElementById('viewVideoDescription').textContent = description;
    document.getElementById('viewVideoModal').classList.add('show');
}

function closeViewVideoModal() {
    document.getElementById('viewVideoModal').classList.remove('show');
    document.getElementById('viewVideoPlayer').src = '';
}

async function deleteVideo(videoId) {
    // Проверяем количество видео
    const videosRows = document.querySelectorAll('#videosTableBody tr:not(:has(td[colspan]))');
    const isLastVideo = videosRows.length <= 1;
    
    let confirmMessage = 'Вы уверены, что хотите удалить это видео?';
    if (isLastVideo) {
        confirmMessage = '⚠️ Это последнее видео для данного жеста!\n\nПосле удаления вам необходимо будет загрузить новое видео, иначе жест нельзя будет сохранить.\n\nПродолжить удаление?';
    }
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    try {
        const response = await apiRequest(`/api/v1/admin/videos/${videoId}`, {
            method: 'DELETE'
        });
        
        if (!response) return;
        
        const data = await response.json();
        if (data.success) {
            showNotification('Видео удалено', 'success');
            loadVideos(currentSignId);
            
            // Если удалили последнее видео, показываем предупреждение и открываем модальное окно добавления
            if (isLastVideo) {
                setTimeout(() => {
                    showNotification('⚠️ Необходимо загрузить новое видео для жеста', 'error');
                    openAddVideoModal();
                }, 500);
            }
            
            updateEditSignSaveButton();
        } else {
            showNotification(data.error?.message || 'Ошибка удаления', 'error');
        }
    } catch (error) {
        console.error('Ошибка удаления видео:', error);
        showNotification('Ошибка соединения с сервером', 'error');
    }
}

// Управление синонимами
async function loadSynonyms(signId) {
    try {
        const response = await apiRequest(`/api/v1/admin/signs/${signId}/synonyms`);
        if (!response) return;
        
        const data = await response.json();
        if (data.success) {
            renderSynonyms(data.data);
        }
    } catch (error) {
        console.error('Ошибка загрузки синонимов:', error);
    }
}

function renderSynonyms(synonyms) {
    const tbody = document.getElementById('synonymsTableBody');
    if (synonyms.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" style="text-align: center; padding: 1rem;">Синонимы не найдены</td></tr>';
        return;
    }
    
    tbody.innerHTML = synonyms.map(synonym => `
        <tr>
            <td>${synonym.word}</td>
            <td>
                <button class="btn btn-danger" style="padding: 0.25rem 0.5rem; font-size: 0.9rem;" onclick="deleteSynonym('${synonym.id}')">Удалить</button>
            </td>
        </tr>
    `).join('');
}

function openAddSynonymModal() {
    document.getElementById('synonymSearch').value = '';
    document.getElementById('synonymSearchResults').style.display = 'none';
    document.getElementById('synonymFormError').style.display = 'none';
    document.getElementById('synonymModal').classList.add('show');
}

function closeSynonymModal() {
    document.getElementById('synonymModal').classList.remove('show');
}

let synonymSearchTimeout = null;
async function searchSignsForSynonym(query) {
    if (synonymSearchTimeout) {
        clearTimeout(synonymSearchTimeout);
    }
    
    if (query.length < 2) {
        document.getElementById('synonymSearchResults').style.display = 'none';
        return;
    }
    
    synonymSearchTimeout = setTimeout(async () => {
        try {
            // Используем параметр search для поиска на сервере
            const encodedQuery = encodeURIComponent(query);
            const response = await apiRequest(`/api/v1/admin/signs?search=${encodedQuery}&per_page=50`);
            if (!response) return;
            
            const data = await response.json();
            if (data.success) {
                // Фильтруем только текущий жест, поиск уже выполнен на сервере
                const filtered = data.data.signs.filter(sign => 
                    sign.id !== currentSignId
                );
                
                renderSynonymSearchResults(filtered);
            }
        } catch (error) {
            console.error('Ошибка поиска жестов:', error);
        }
    }, 300);
}

function renderSynonymSearchResults(signs) {
    const resultsDiv = document.getElementById('synonymSearchResults');
    if (signs.length === 0) {
        resultsDiv.innerHTML = '<div class="search-result-item">Жесты не найдены</div>';
        resultsDiv.style.display = 'block';
        return;
    }
    
    resultsDiv.innerHTML = signs.map(sign => `
        <div class="search-result-item" onclick="addSynonym('${sign.id}', '${sign.word.replace(/'/g, "\\'")}')">
            <strong>${sign.word}</strong> (${sign.id})
        </div>
    `).join('');
    resultsDiv.style.display = 'block';
}

async function addSynonym(synonymId, synonymWord) {
    try {
        const response = await apiRequest(`/api/v1/admin/signs/${currentSignId}/synonyms`, {
            method: 'POST',
            body: JSON.stringify({ synonym_sign_id: synonymId })
        });
        
        if (!response) return;
        
        const data = await response.json();
        if (data.success) {
            showNotification(`Синоним "${synonymWord}" добавлен`, 'success');
            closeSynonymModal();
            loadSynonyms(currentSignId);
        } else {
            showError('synonymFormError', data.error?.message || 'Ошибка добавления синонима');
        }
    } catch (error) {
        console.error('Ошибка добавления синонима:', error);
        showError('synonymFormError', 'Ошибка соединения с сервером');
    }
}

async function deleteSynonym(synonymId) {
    if (!confirm('Вы уверены, что хотите удалить этот синоним?')) {
        return;
    }
    
    try {
        // Сначала нужно найти ID связи синонимов
        const response = await apiRequest(`/api/v1/admin/signs/${currentSignId}/synonyms`);
        if (!response) return;
        
        const data = await response.json();
        if (data.success) {
            // Найти связь, которая содержит этот синоним
            // Для упрощения используем endpoint удаления по sign_id и synonym_id
            const deleteResponse = await apiRequest(`/api/v1/admin/signs/${currentSignId}/synonyms/${synonymId}`, {
                method: 'DELETE'
            });
            
            if (!deleteResponse) return;
            
            const deleteData = await deleteResponse.json();
            if (deleteData.success) {
                showNotification('Синоним удален', 'success');
                loadSynonyms(currentSignId);
            } else {
                showNotification(deleteData.error?.message || 'Ошибка удаления', 'error');
            }
        }
    } catch (error) {
        console.error('Ошибка удаления синонима:', error);
        showNotification('Ошибка соединения с сервером', 'error');
    }
}

// Закрытие модальных окон при клике вне их
window.addEventListener('click', (event) => {
    const modals = ['signModal', 'editSignModal', 'videoModal', 'synonymModal', 'viewVideoModal'];
    modals.forEach(modalId => {
        const modal = document.getElementById(modalId);
        if (event.target === modal) {
            modal.classList.remove('show');
        }
    });
});

