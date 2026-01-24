// Текущий редактируемый урок
let currentLessonId = null;

// Получение максимального порядка для автоматического определения
async function getMaxLessonOrder() {
    try {
        const response = await apiRequest(`${API_BASE}/lessons`);
        if (!response) return 0;
        
        const data = await response.json();
        if (data.success && data.data && data.data.length > 0) {
            const maxOrder = Math.max(...data.data.map(lesson => lesson.order || 0));
            return maxOrder;
        }
        return 0;
    } catch (error) {
        console.error('Ошибка получения максимального порядка:', error);
        return 0;
    }
}

// Проверка авторизации при загрузке
window.addEventListener('load', () => {
    if (!checkAuth()) return;
    loadLessons();
});

// Загрузка списка уроков
async function loadLessons() {
    try {
        const tbody = document.getElementById('lessonsTableBody');
        if (!tbody) {
            console.error('Элемент lessonsTableBody не найден');
            return;
        }
        
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem;"><div class="loading"></div> Загрузка...</td></tr>';
        
        const response = await apiRequest(`${API_BASE}/lessons`);
        if (!response) return;
        
        const data = await response.json();
        if (!data.success) {
            showNotification(data.error?.message || 'Ошибка при загрузке уроков', 'error');
            return;
        }
        
        const lessons = data.data || [];
        
        tbody.innerHTML = '';
        
        if (lessons.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem;">Уроки не найдены</td></tr>';
            return;
        }
        
        // Сортировка по порядку
        const sorted = [...lessons].sort((a, b) => a.order - b.order);
        
        // Рендеринг уроков
        tbody.innerHTML = sorted.map(lesson => {
            const safeId = lesson.id.replace(/'/g, "\\'").replace(/"/g, '&quot;');
            const safeTitle = lesson.title.replace(/'/g, "\\'").replace(/"/g, '&quot;');
            return `
                <tr>
                    <td>${escapeHtml(lesson.id)}</td>
                    <td>${escapeHtml(lesson.title)}</td>
                    <td>${lesson.order}</td>
                    <td style="white-space: nowrap;"><code style="font-size: 0.85rem;">${escapeHtml(lesson.video_url)}</code></td>
                    <td style="white-space: nowrap;">
                        <button class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 1rem; display: inline-block;" onclick="editLesson('${safeId}')">Редактировать</button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Ошибка в loadLessons:', error);
        const tbody = document.getElementById('lessonsTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem; color: red;">Ошибка: ' + error.message + '</td></tr>';
        }
        showNotification('Ошибка при загрузке уроков: ' + error.message, 'error');
    }
}

// Открытие модального окна для создания урока
async function openCreateLessonModal() {
    currentLessonId = null;
    document.getElementById('lessonModalTitle').textContent = 'Создать урок';
    document.getElementById('lessonForm').reset();
    document.getElementById('lessonId').value = '';
    document.getElementById('lessonFormError').style.display = 'none';
    document.getElementById('lessonVideoPreviewGroup').style.display = 'none';
    document.getElementById('lessonDeleteButton').style.display = 'none'; // Скрываем кнопку удаления при создании
    document.getElementById('lessonDeleteVideoButton').style.display = 'none'; // Скрываем кнопку удаления видео при создании
    
    // Сбрасываем флаги
    window.currentLessonVideoUrl = null;
    window.videoWasDeleted = false;
    
    // Показываем обязательное поле для видео при создании
    document.getElementById('lessonVideoRequired').style.display = 'inline';
    
    // Автоматически определяем порядок
    const maxOrder = await getMaxLessonOrder();
    document.getElementById('lessonOrder').value = maxOrder + 1;
    
    // Очищаем поле загрузки файла
    const videoFileInput = document.getElementById('lessonVideoFile');
    if (videoFileInput) {
        videoFileInput.value = '';
        document.getElementById('lessonVideoUploadButton').style.display = 'none';
    }
    
    // Добавляем обработчик выбора файла для загрузки, если еще не добавлен
    if (videoFileInput && !videoFileInput.hasAttribute('data-upload-handler')) {
        videoFileInput.addEventListener('change', function() {
            const uploadButton = document.getElementById('lessonVideoUploadButton');
            uploadButton.style.display = this.files.length > 0 ? 'inline-block' : 'none';
        });
        videoFileInput.setAttribute('data-upload-handler', 'true');
    }
    
    document.getElementById('lessonModal').classList.add('show');
}

// Обновление превью видео при изменении URL
function updateLessonVideoPreview(videoUrl) {
    const previewGroup = document.getElementById('lessonVideoPreviewGroup');
    const videoLink = document.getElementById('lessonVideoLink');
    
    if (videoUrl && videoUrl.trim()) {
        const fullUrl = getFullVideoUrl(videoUrl);
        videoLink.href = fullUrl;
        previewGroup.style.display = 'block';
    } else {
        previewGroup.style.display = 'none';
    }
}

// Открытие модального окна для редактирования урока
async function editLesson(lessonId) {
    const response = await apiRequest(`${API_BASE}/lessons/${lessonId}`);
    if (!response) return;
    
    if (!response.ok) {
        showNotification('Ошибка при загрузке урока', 'error');
        return;
    }
    
    const data = await response.json();
    const lesson = data.data;
    
    currentLessonId = lessonId;
    document.getElementById('lessonModalTitle').textContent = 'Редактировать урок';
    document.getElementById('lessonId').value = lesson.id;
    document.getElementById('lessonTitle').value = lesson.title;
    document.getElementById('lessonDescription').value = lesson.description;
    document.getElementById('lessonOrder').value = lesson.order;
    document.getElementById('lessonFormError').style.display = 'none';
    document.getElementById('lessonDeleteButton').style.display = 'inline-block'; // Показываем кнопку удаления при редактировании
    
    // Сохраняем название урока и video_url для подтверждения удаления и превью
    window.currentLessonTitle = lesson.title;
    window.currentLessonVideoUrl = lesson.video_url;
    window.videoWasDeleted = false; // Сбрасываем флаг удаления видео
    
    // Скрываем обязательное поле для видео при редактировании (если видео есть)
    if (lesson.video_url && lesson.video_url.trim()) {
        document.getElementById('lessonVideoRequired').style.display = 'none';
    } else {
        // Если видео нет, показываем обязательное поле
        document.getElementById('lessonVideoRequired').style.display = 'inline';
    }
    
    // Обновляем ссылку на видео и показываем превью
    updateLessonVideoPreview(lesson.video_url);
    
    // Показываем/скрываем кнопку удаления видео в зависимости от наличия видео
    const deleteVideoButton = document.getElementById('lessonDeleteVideoButton');
    if (lesson.video_url && lesson.video_url.trim()) {
        deleteVideoButton.style.display = 'inline-block';
    } else {
        deleteVideoButton.style.display = 'none';
    }
    
    document.getElementById('lessonModal').classList.add('show');
}

// Закрытие модального окна
function closeLessonModal() {
    document.getElementById('lessonModal').classList.remove('show');
    currentLessonId = null;
}

// Сохранение урока
async function saveLesson(event) {
    event.preventDefault();
    
    const formData = {
        title: document.getElementById('lessonTitle').value.trim(),
        description: document.getElementById('lessonDescription').value.trim(),
        order: parseInt(document.getElementById('lessonOrder').value)
    };
    
    // При создании ID опционален (будет автогенерирован)
    const lessonId = document.getElementById('lessonId').value.trim();
    if (lessonId) {
        // Редактирование существующего урока
        formData.id = lessonId;
        // При редактировании video_url берем из сохраненного значения
        if (window.currentLessonVideoUrl) {
            formData.video_url = window.currentLessonVideoUrl;
        } else if (window.videoWasDeleted) {
            // Если видео было удалено, проверяем, что новое видео загружено
            if (!window.currentLessonVideoUrl || !window.currentLessonVideoUrl.trim()) {
                const fileInput = document.getElementById('lessonVideoFile');
                if (!fileInput.files || fileInput.files.length === 0) {
                    showError('lessonFormError', 'Видео обязательно. Пожалуйста, выберите и загрузите новое видео перед сохранением урока.');
                    return;
                } else {
                    // Файл выбран, но еще не загружен - нужно сначала загрузить
                    showError('lessonFormError', 'Пожалуйста, нажмите "Загрузить видео" перед сохранением урока.');
                    return;
                }
            }
            // Если видео загружено, используем его
            formData.video_url = window.currentLessonVideoUrl;
        } else {
            // Если видео не было удалено, но video_url пустой - это ошибка
            showError('lessonFormError', 'Видео обязательно. Пожалуйста, загрузите видео перед сохранением.');
            return;
        }
    } else {
        // Создание нового урока - видео обязательно
        if (!window.currentLessonVideoUrl) {
            showError('lessonFormError', 'Видео обязательно при создании урока. Пожалуйста, загрузите видео перед сохранением.');
            return;
        }
        formData.video_url = window.currentLessonVideoUrl;
    }
    
    const errorDiv = document.getElementById('lessonFormError');
    errorDiv.style.display = 'none';
    
    const submitButton = document.getElementById('lessonFormSubmit');
    submitButton.disabled = true;
    submitButton.textContent = 'Сохранение...';
    
    try {
        let response;
        if (currentLessonId) {
            // Обновление
            response = await apiRequest(`${API_BASE}/lessons/${currentLessonId}`, {
                method: 'PUT',
                body: JSON.stringify(formData)
            });
        } else {
            // Создание
            response = await apiRequest(`${API_BASE}/lessons`, {
                method: 'POST',
                body: JSON.stringify(formData)
            });
        }
        
        if (!response) {
            submitButton.disabled = false;
            submitButton.textContent = 'Сохранить';
            return;
        }
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            const errorMsg = data.error?.message || data.message || 'Ошибка при сохранении урока';
            showError('lessonFormError', errorMsg);
            submitButton.disabled = false;
            submitButton.textContent = 'Сохранить';
            return;
        }
        
        showNotification(currentLessonId ? 'Урок обновлен' : 'Урок создан', 'success');
        closeLessonModal();
        loadLessons();
        
    } catch (error) {
        showError('lessonFormError', 'Ошибка при сохранении: ' + error.message);
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Сохранить';
    }
}

// Показать модальное окно подтверждения удаления
function showDeleteLessonConfirmation() {
    if (!window.currentLessonTitle) {
        showNotification('Ошибка: название урока не найдено', 'error');
        return;
    }
    
    document.getElementById('deleteLessonTitleDisplay').textContent = window.currentLessonTitle;
    document.getElementById('deleteLessonConfirmInput').value = '';
    document.getElementById('deleteLessonError').style.display = 'none';
    document.getElementById('confirmDeleteLessonButton').disabled = true;
    document.getElementById('deleteLessonModal').classList.add('show');
    
    // Добавляем обработчик для проверки ввода
    const confirmInput = document.getElementById('deleteLessonConfirmInput');
    const oldHandler = confirmInput.oninput;
    confirmInput.oninput = null; // Удаляем старый обработчик
    confirmInput.addEventListener('input', function() {
        const confirmButton = document.getElementById('confirmDeleteLessonButton');
        confirmButton.disabled = this.value.trim() !== window.currentLessonTitle;
    });
}

// Закрытие модального окна подтверждения удаления
function closeDeleteLessonModal() {
    document.getElementById('deleteLessonModal').classList.remove('show');
    document.getElementById('deleteLessonConfirmInput').value = '';
    document.getElementById('deleteLessonError').style.display = 'none';
}

// Подтверждение удаления урока
async function confirmDeleteLesson() {
    const inputValue = document.getElementById('deleteLessonConfirmInput').value.trim();
    const lessonTitle = window.currentLessonTitle;
    
    if (inputValue !== lessonTitle) {
        showError('deleteLessonError', 'Название не совпадает. Введите точное название урока.');
        return;
    }
    
    if (!currentLessonId) {
        showError('deleteLessonError', 'Ошибка: ID урока не найден');
        return;
    }
    
    const confirmButton = document.getElementById('confirmDeleteLessonButton');
    confirmButton.disabled = true;
    confirmButton.textContent = 'Удаление...';
    
    try {
        const response = await apiRequest(`${API_BASE}/lessons/${currentLessonId}`, {
            method: 'DELETE'
        });
        
        if (!response) {
            confirmButton.disabled = false;
            confirmButton.textContent = 'Удалить';
            return;
        }
        
        if (!response.ok) {
            const data = await response.json();
            showError('deleteLessonError', data.error?.message || 'Ошибка при удалении урока');
            confirmButton.disabled = false;
            confirmButton.textContent = 'Удалить';
            return;
        }
        
        showNotification('Урок удален', 'success');
        closeDeleteLessonModal();
        closeLessonModal();
        loadLessons();
    } catch (error) {
        showError('deleteLessonError', 'Ошибка соединения с сервером');
        confirmButton.disabled = false;
        confirmButton.textContent = 'Удалить';
    }
}

// Закрытие модальных окон при клике вне их
document.addEventListener('click', function(event) {
    const lessonModal = document.getElementById('lessonModal');
    const viewVideoModal = document.getElementById('viewLessonVideoModal');
    const deleteLessonModal = document.getElementById('deleteLessonModal');
    
    if (event.target === lessonModal) {
        closeLessonModal();
    }
    if (event.target === viewVideoModal) {
        closeViewLessonVideoModal();
    }
    if (event.target === deleteLessonModal) {
        closeDeleteLessonModal();
    }
});

// Получение полного URL для видео из Supabase
function getFullVideoUrl(videoUrl) {
    if (!videoUrl) return '';
    
    // Если уже полный URL (начинается с http), возвращаем как есть
    if (videoUrl.startsWith('http://') || videoUrl.startsWith('https://')) {
        return videoUrl;
    }
    
    // Если относительный путь (для обратной совместимости со старыми данными)
    // Формируем полный URL для Supabase
    const supabaseBaseUrl = 'https://lesulvngqpvgepijazin.supabase.co/storage/v1/object/public';
    return `${supabaseBaseUrl}/${videoUrl}`;
}

// Просмотр видео урока
function viewLessonVideo(videoUrl, lessonTitle) {
    const fullVideoUrl = getFullVideoUrl(videoUrl);
    document.getElementById('viewLessonVideoPlayer').src = fullVideoUrl;
    document.getElementById('viewLessonVideoDescription').textContent = lessonTitle;
    document.getElementById('viewLessonVideoModal').classList.add('show');
}

// Предпросмотр видео из формы редактирования
function previewLessonVideo() {
    const videoUrl = window.currentLessonVideoUrl || '';
    const lessonTitle = document.getElementById('lessonTitle').value.trim() || 'Урок';
    
    if (!videoUrl) {
        showNotification('Видео не загружено для этого урока', 'error');
        return;
    }
    
    viewLessonVideo(videoUrl, lessonTitle);
}

// Закрытие модального окна просмотра видео
function closeViewLessonVideoModal() {
    document.getElementById('viewLessonVideoModal').classList.remove('show');
    const player = document.getElementById('viewLessonVideoPlayer');
    player.pause();
    player.src = '';
}

// Загрузка видео для урока
async function uploadLessonVideo() {
    const fileInput = document.getElementById('lessonVideoFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('lessonVideoUploadError', 'Выберите файл');
        return;
    }
    
    // Валидация файла
    if (!file.name.toLowerCase().endsWith('.mp4')) {
        showError('lessonVideoUploadError', 'Только файлы MP4 разрешены');
        return;
    }
    
    if (file.size > 50 * 1024 * 1024) {
        showError('lessonVideoUploadError', 'Размер файла не должен превышать 50MB');
        return;
    }
    
    // Если урок еще не создан, создаем временный урок для загрузки видео
    let tempLessonId = currentLessonId;
    if (!tempLessonId) {
        // Проверяем, что все обязательные поля заполнены
        const title = document.getElementById('lessonTitle').value.trim();
        const description = document.getElementById('lessonDescription').value.trim();
        const order = document.getElementById('lessonOrder').value;
        
        if (!title || !description || !order) {
            showError('lessonVideoUploadError', 'Сначала заполните все обязательные поля');
            return;
        }
        
        // Создаем временный урок с placeholder video_url
        const tempFormData = {
            title: title,
            description: description,
            video_url: 'lessons/placeholder.mp4', // Временный URL, будет обновлен после загрузки
            order: parseInt(order)
        };
        
        const createResponse = await apiRequest(`${API_BASE}/lessons`, {
            method: 'POST',
            body: JSON.stringify(tempFormData)
        });
        
        if (!createResponse || !createResponse.ok) {
            const createData = await createResponse.json();
            showError('lessonVideoUploadError', createData.error?.message || 'Ошибка создания урока');
            return;
        }
        
        const createResult = await createResponse.json();
        tempLessonId = createResult.data.id;
        currentLessonId = tempLessonId;
        document.getElementById('lessonId').value = tempLessonId;
        window.currentLessonTitle = title;
    }
    
    // Если у урока уже есть видео, удаляем старое перед загрузкой нового
    if (window.currentLessonVideoUrl && window.currentLessonVideoUrl.trim()) {
        try {
            await apiRequest(`${API_BASE}/lessons/${tempLessonId}/video`, {
                method: 'DELETE'
            });
            // Игнорируем ошибки удаления (файл может не существовать)
        } catch (error) {
            console.warn('Не удалось удалить старое видео:', error);
        }
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    const uploadButton = document.getElementById('lessonVideoUploadButton');
    const progressDiv = document.getElementById('lessonVideoUploadProgress');
    const errorDiv = document.getElementById('lessonVideoUploadError');
    
    uploadButton.disabled = true;
    uploadButton.textContent = 'Загрузка...';
    progressDiv.style.display = 'block';
    errorDiv.style.display = 'none';
    
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch(`${API_BASE}/lessons/${tempLessonId}/video`, {
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
            showNotification('Видео загружено успешно', 'success');
            // Обновляем video_url и показываем превью
            window.currentLessonVideoUrl = data.data.video_url;
            window.videoWasDeleted = false; // Сбрасываем флаг удаления видео
            updateLessonVideoPreview(data.data.video_url);
            // Показываем кнопку удаления видео
            document.getElementById('lessonDeleteVideoButton').style.display = 'inline-block';
            // Скрываем обязательное поле для видео (видео уже загружено)
            document.getElementById('lessonVideoRequired').style.display = 'none';
            // Очищаем поле файла
            fileInput.value = '';
            uploadButton.style.display = 'none';
        } else {
            showError('lessonVideoUploadError', data.error?.message || 'Ошибка загрузки видео');
        }
    } catch (error) {
        console.error('Ошибка загрузки видео:', error);
        showError('lessonVideoUploadError', 'Ошибка соединения с сервером');
    } finally {
        uploadButton.disabled = false;
        uploadButton.textContent = 'Загрузить видео';
        progressDiv.style.display = 'none';
    }
}

// Показать модальное окно подтверждения удаления видео
function showDeleteVideoConfirmation() {
    // Показываем модальное окно
    document.getElementById('deleteVideoLessonTitleDisplay').textContent = window.currentLessonTitle || 'Урок';
    document.getElementById('deleteVideoConfirmInput').value = '';
    document.getElementById('deleteVideoError').style.display = 'none';
    document.getElementById('confirmDeleteVideoButton').disabled = true;
    document.getElementById('deleteVideoModal').classList.add('show');
    
    // Добавляем обработчик ввода для активации кнопки удаления
    const confirmInput = document.getElementById('deleteVideoConfirmInput');
    const confirmButton = document.getElementById('confirmDeleteVideoButton');
    
    confirmInput.addEventListener('input', function() {
        const inputValue = this.value.trim();
        const lessonTitle = window.currentLessonTitle || '';
        confirmButton.disabled = inputValue !== lessonTitle;
    });
}

// Закрытие модального окна подтверждения удаления видео
function closeDeleteVideoModal() {
    document.getElementById('deleteVideoModal').classList.remove('show');
    document.getElementById('deleteVideoConfirmInput').value = '';
    document.getElementById('deleteVideoError').style.display = 'none';
}

// Подтверждение удаления видео
async function confirmDeleteVideo() {
    const confirmInput = document.getElementById('deleteVideoConfirmInput');
    const lessonTitle = window.currentLessonTitle || '';
    
    if (confirmInput.value.trim() !== lessonTitle) {
        showError('deleteVideoError', 'Название урока не совпадает');
        return;
    }
    
    if (!currentLessonId) {
        showError('deleteVideoError', 'Урок не найден');
        return;
    }
    
    const confirmButton = document.getElementById('confirmDeleteVideoButton');
    confirmButton.disabled = true;
    confirmButton.textContent = 'Удаление...';
    
    try {
        const response = await apiRequest(`${API_BASE}/lessons/${currentLessonId}/video`, {
            method: 'DELETE'
        });
        
        if (!response) {
            showError('deleteVideoError', 'Ошибка соединения с сервером');
            return;
        }
        
        if (!response.ok) {
            const data = await response.json();
            showError('deleteVideoError', data.error?.message || 'Ошибка удаления видео');
            return;
        }
        
        const data = await response.json();
        if (data.success) {
            showNotification('Видео удалено. Пожалуйста, загрузите новое видео перед сохранением урока.', 'warning');
            closeDeleteVideoModal();
            
            // Очищаем video_url и помечаем, что видео было удалено
            window.currentLessonVideoUrl = '';
            window.videoWasDeleted = true; // Флаг, что видео было удалено
            updateLessonVideoPreview('');
            document.getElementById('lessonDeleteVideoButton').style.display = 'none';
            
            // Показываем поле загрузки видео и делаем его обязательным
            document.getElementById('lessonVideoUploadGroup').style.display = 'block';
            document.getElementById('lessonVideoRequired').style.display = 'inline';
            
            // Фокусируемся на поле загрузки файла
            document.getElementById('lessonVideoFile').focus();
        } else {
            showError('deleteVideoError', data.error?.message || 'Ошибка удаления видео');
        }
    } catch (error) {
        console.error('Ошибка удаления видео:', error);
        showError('deleteVideoError', 'Ошибка соединения с сервером');
    } finally {
        confirmButton.disabled = false;
        confirmButton.textContent = 'Удалить видео';
    }
}

// Загрузка уже происходит в window.addEventListener('load') выше

// Функции showError и escapeHtml теперь в common.js
