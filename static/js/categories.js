// Глобальные переменные
let allCategories = [];
let categorySignsCounts = {};
let currentDeleteCategoryId = null;
let currentDeleteCategorySigns = [];

// Проверка авторизации при загрузке
window.addEventListener('load', () => {
    if (!checkAuth()) return;
    loadCategories();
});

// Загрузка категорий
async function loadCategories() {
    try {
        const response = await apiRequest('/api/v1/admin/categories');
        if (!response) return;
        
        const data = await response.json();
        if (data.success) {
            allCategories = data.data;
            await loadSignsCounts();
            renderCategories();
        } else {
            showNotification(data.error?.message || 'Ошибка загрузки категорий', 'error');
        }
    } catch (error) {
        console.error('Ошибка загрузки категорий:', error);
        showNotification('Ошибка соединения с сервером', 'error');
    }
}

// Загрузка количества жестов для каждой категории
async function loadSignsCounts() {
    try {
        for (const category of allCategories) {
            const response = await apiRequest(`/api/v1/admin/categories/${category.id}/signs`);
            if (response) {
                const data = await response.json();
                if (data.success) {
                    categorySignsCounts[category.id] = data.data.length;
                }
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки количества жестов:', error);
    }
}

// Рендеринг категорий
function renderCategories() {
    const tbody = document.getElementById('categoriesTableBody');
    if (allCategories.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem;">Категории не найдены</td></tr>';
        return;
    }
    
    // Сортировка по порядку
    const sorted = [...allCategories].sort((a, b) => a.order - b.order);
    
    tbody.innerHTML = sorted.map(category => {
        const signsCount = categorySignsCounts[category.id] || 0;
        return `
            <tr>
                <td>${category.id}</td>
                <td>${category.name}</td>
                <td>${category.order}</td>
                <td>${signsCount}</td>
                <td style="white-space: nowrap;">
                    <button class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 1rem; display: inline-block;" onclick="openEditCategoryModal('${category.id}')">Редактировать</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Модальное окно создания категории
function openCreateCategoryModal() {
    document.getElementById('categoryModalTitle').textContent = 'Создать категорию';
    document.getElementById('categoryForm').reset();
    document.getElementById('categoryId').value = '';
    document.getElementById('categoryFormError').style.display = 'none';
    document.getElementById('categoryDeleteButton').style.display = 'none'; // Скрываем кнопку удаления при создании
    document.getElementById('categoryModal').classList.add('show');
}

// Модальное окно редактирования категории
async function openEditCategoryModal(categoryId) {
    const category = allCategories.find(c => c.id === categoryId);
    if (!category) {
        showNotification('Категория не найдена', 'error');
        return;
    }
    
    document.getElementById('categoryModalTitle').textContent = 'Редактировать категорию';
    document.getElementById('categoryId').value = category.id;
    document.getElementById('categoryName').value = category.name;
    document.getElementById('categoryOrder').value = category.order;
    document.getElementById('categoryFormError').style.display = 'none';
    document.getElementById('categoryDeleteButton').style.display = 'inline-block'; // Показываем кнопку удаления при редактировании
    document.getElementById('categoryModal').classList.add('show');
    
    // Сохраняем название категории для подтверждения удаления
    window.currentCategoryName = category.name;
}

function closeCategoryModal() {
    document.getElementById('categoryModal').classList.remove('show');
}

// Сохранение категории
async function saveCategory(event) {
    event.preventDefault();
    
    const formData = {
        name: document.getElementById('categoryName').value,
        order: parseInt(document.getElementById('categoryOrder').value)
    };
    
    if (!formData.name || formData.order === undefined) {
        showError('categoryFormError', 'Заполните все поля');
        return;
    }
    
    const categoryId = document.getElementById('categoryId').value;
    const isEdit = !!categoryId;
    const url = isEdit 
        ? `/api/v1/admin/categories/${categoryId}`
        : '/api/v1/admin/categories';
    const method = isEdit ? 'PUT' : 'POST';
    
    // Для создания нужно добавить ID
    if (!isEdit) {
        formData.id = generateCategoryId();
    }
    
    const submitButton = document.getElementById('categoryFormSubmit');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="loading"></span> Сохранение...';
    
    try {
        const response = await apiRequest(url, {
            method: method,
            body: JSON.stringify(formData)
        });
        
        if (!response) return;
        
        const data = await response.json();
        if (data.success) {
            showNotification(isEdit ? 'Категория обновлена' : 'Категория создана', 'success');
            closeCategoryModal();
            loadCategories();
        } else {
            showError('categoryFormError', data.error?.message || 'Ошибка сохранения');
        }
    } catch (error) {
        console.error('Ошибка сохранения категории:', error);
        showError('categoryFormError', 'Ошибка соединения с сервером');
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Сохранить';
    }
}

function generateCategoryId() {
    const name = document.getElementById('categoryName').value;
    return name.toLowerCase()
        .replace(/[^a-zа-яё0-9]/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_|_$/g, '');
}

// Функция showError теперь в common.js

// Удаление категории
async function deleteCategory(categoryId) {
    // Проверить наличие жестов
    try {
        const response = await apiRequest(`/api/v1/admin/categories/${categoryId}/signs`);
        if (!response) return;
        
        const data = await response.json();
        if (data.success && data.data.length > 0) {
            // Показать предупреждение
            currentDeleteCategoryId = categoryId;
            currentDeleteCategorySigns = data.data;
            showDeleteCategoryWarning(categoryId, data.data);
        } else {
            // Нет жестов, можно удалять сразу
            confirmDeleteCategory(categoryId);
        }
    } catch (error) {
        console.error('Ошибка проверки жестов:', error);
        showNotification('Ошибка соединения с сервером', 'error');
    }
}

function showDeleteCategoryWarning(categoryId, signs) {
    document.getElementById('deleteCategorySignsCount').textContent = signs.length;
    
    // Заполнить список жестов
    const signsList = document.getElementById('deleteCategorySignsList');
    signsList.innerHTML = signs.map(sign => `
        <div class="sign-item">
            <span>${sign.word} (${sign.id})</span>
            <a href="/admin/signs" class="btn btn-primary" style="padding: 0.25rem 0.5rem; font-size: 0.9rem; text-decoration: none;" target="_blank">Редактировать</a>
        </div>
    `).join('');
    
    // Заполнить список категорий для переноса
    const moveSelect = document.getElementById('moveToExistingCategory');
    moveSelect.innerHTML = '<option value="">Выберите категорию</option>';
    allCategories
        .filter(c => c.id !== categoryId)
        .sort((a, b) => a.order - b.order)
        .forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id;
            option.textContent = `${cat.name} (${cat.id})`;
            moveSelect.appendChild(option);
        });
    
    // Сбросить состояние
    document.getElementById('deleteCategoryButton').disabled = true;
    document.getElementById('deleteCategoryError').style.display = 'none';
    document.getElementById('deleteCategoryModal').classList.add('show');
}

function closeDeleteCategoryModal() {
    document.getElementById('deleteCategoryModal').classList.remove('show');
    currentDeleteCategoryId = null;
    currentDeleteCategorySigns = [];
}

// Перенос всех жестов в существующую категорию
async function moveAllToExistingCategory() {
    const targetCategoryId = document.getElementById('moveToExistingCategory').value;
    if (!targetCategoryId) {
        showError('deleteCategoryError', 'Выберите категорию');
        return;
    }
    
    if (!confirm(`Перенести все жесты в категорию "${allCategories.find(c => c.id === targetCategoryId)?.name}"?`)) {
        return;
    }
    
    try {
        let successCount = 0;
        let errorCount = 0;
        
        for (const sign of currentDeleteCategorySigns) {
            try {
                const response = await apiRequest(`/api/v1/admin/signs/${sign.id}`, {
                    method: 'PUT',
                    body: JSON.stringify({
                        word: sign.word,
                        description: sign.description || '',
                        category_id: targetCategoryId
                    })
                });
                
                if (response) {
                    const data = await response.json();
                    if (data.success) {
                        successCount++;
                    } else {
                        errorCount++;
                    }
                }
            } catch (error) {
                errorCount++;
            }
        }
        
        if (successCount === currentDeleteCategorySigns.length) {
            showNotification(`Все жесты перенесены (${successCount})`, 'success');
            // Обновить список жестов
            const response = await apiRequest(`/api/v1/admin/categories/${currentDeleteCategoryId}/signs`);
            if (response) {
                const data = await response.json();
                if (data.success && data.data.length === 0) {
                    // Все жесты перенесены, можно удалять
                    document.getElementById('deleteCategoryButton').disabled = false;
                    showNotification('Все жесты перенесены. Теперь можно удалить категорию.', 'success');
                } else {
                    currentDeleteCategorySigns = data.data;
                    showDeleteCategoryWarning(currentDeleteCategoryId, data.data);
                }
            }
        } else {
            showError('deleteCategoryError', `Перенесено: ${successCount}, ошибок: ${errorCount}`);
        }
    } catch (error) {
        console.error('Ошибка переноса жестов:', error);
        showError('deleteCategoryError', 'Ошибка соединения с сервером');
    }
}

// Создание новой категории и перенос всех жестов
async function moveAllToNewCategory() {
    const newCategoryName = document.getElementById('newCategoryName').value;
    const newCategoryOrder = parseInt(document.getElementById('newCategoryOrder').value);
    
    if (!newCategoryName || isNaN(newCategoryOrder)) {
        showError('deleteCategoryError', 'Заполните название и порядок новой категории');
        return;
    }
    
    if (!confirm(`Создать новую категорию "${newCategoryName}" и перенести все жесты?`)) {
        return;
    }
    
    try {
        // Создать новую категорию
        const newCategoryId = newCategoryName.toLowerCase()
            .replace(/[^a-zа-яё0-9]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '');
        
        const createResponse = await apiRequest('/api/v1/admin/categories', {
            method: 'POST',
            body: JSON.stringify({
                id: newCategoryId,
                name: newCategoryName,
                order: newCategoryOrder
            })
        });
        
        if (!createResponse) return;
        
        const createData = await createResponse.json();
        if (!createData.success) {
            showError('deleteCategoryError', createData.error?.message || 'Ошибка создания категории');
            return;
        }
        
        // Перенести все жесты
        let successCount = 0;
        let errorCount = 0;
        
        for (const sign of currentDeleteCategorySigns) {
            try {
                const response = await apiRequest(`/api/v1/admin/signs/${sign.id}`, {
                    method: 'PUT',
                    body: JSON.stringify({
                        word: sign.word,
                        description: sign.description || '',
                        category_id: newCategoryId
                    })
                });
                
                if (response) {
                    const data = await response.json();
                    if (data.success) {
                        successCount++;
                    } else {
                        errorCount++;
                    }
                }
            } catch (error) {
                errorCount++;
            }
        }
        
        if (successCount === currentDeleteCategorySigns.length) {
            showNotification(`Категория создана и все жесты перенесены (${successCount})`, 'success');
            // Обновить список категорий и жестов
            await loadCategories();
            const response = await apiRequest(`/api/v1/admin/categories/${currentDeleteCategoryId}/signs`);
            if (response) {
                const data = await response.json();
                if (data.success && data.data.length === 0) {
                    document.getElementById('deleteCategoryButton').disabled = false;
                    showNotification('Все жесты перенесены. Теперь можно удалить категорию.', 'success');
                } else {
                    currentDeleteCategorySigns = data.data;
                    showDeleteCategoryWarning(currentDeleteCategoryId, data.data);
                }
            }
        } else {
            showError('deleteCategoryError', `Перенесено: ${successCount}, ошибок: ${errorCount}`);
        }
    } catch (error) {
        console.error('Ошибка создания категории и переноса жестов:', error);
        showError('deleteCategoryError', 'Ошибка соединения с сервером');
    }
}

// Подтверждение удаления категории
async function confirmDeleteCategory() {
    if (!currentDeleteCategoryId) return;
    
    // Еще раз проверить, что жестов нет
    const response = await apiRequest(`/api/v1/admin/categories/${currentDeleteCategoryId}/signs`);
    if (!response) return;
    
    const data = await response.json();
    if (data.success && data.data.length > 0) {
        showError('deleteCategoryError', 'В категории еще остались жесты. Перенесите их перед удалением.');
        currentDeleteCategorySigns = data.data;
        showDeleteCategoryWarning(currentDeleteCategoryId, data.data);
        return;
    }
    
    if (!confirm('Вы уверены, что хотите удалить эту категорию?')) {
        return;
    }
    
    try {
        const deleteResponse = await apiRequest(`/api/v1/admin/categories/${currentDeleteCategoryId}`, {
            method: 'DELETE'
        });
        
        if (!deleteResponse) return;
        
        const deleteData = await deleteResponse.json();
        if (deleteData.success) {
            showNotification('Категория удалена', 'success');
            closeDeleteCategoryModal();
            loadCategories();
        } else {
            showError('deleteCategoryError', deleteData.error?.message || 'Ошибка удаления');
        }
    } catch (error) {
        console.error('Ошибка удаления категории:', error);
        showError('deleteCategoryError', 'Ошибка соединения с сервером');
    }
}

// Показать модальное окно подтверждения удаления
function showDeleteCategoryConfirmation() {
    if (!window.currentCategoryName) {
        showNotification('Ошибка: название категории не найдено', 'error');
        return;
    }
    
    const categoryId = document.getElementById('categoryId').value;
    if (!categoryId) {
        showNotification('Ошибка: ID категории не найден', 'error');
        return;
    }
    
    document.getElementById('deleteCategoryNameDisplay').textContent = window.currentCategoryName;
    document.getElementById('deleteCategoryConfirmInput').value = '';
    document.getElementById('deleteCategoryConfirmError').style.display = 'none';
    document.getElementById('confirmDeleteCategoryButton').disabled = true;
    document.getElementById('deleteCategoryConfirmModal').classList.add('show');
    
    // Сохраняем ID категории для удаления
    window.categoryToDeleteId = categoryId;
    
    // Добавляем обработчик для проверки ввода
    const confirmInput = document.getElementById('deleteCategoryConfirmInput');
    confirmInput.addEventListener('input', function() {
        const confirmButton = document.getElementById('confirmDeleteCategoryButton');
        confirmButton.disabled = this.value.trim() !== window.currentCategoryName;
    });
}

// Закрытие модального окна подтверждения удаления
function closeDeleteCategoryConfirmModal() {
    document.getElementById('deleteCategoryConfirmModal').classList.remove('show');
    document.getElementById('deleteCategoryConfirmInput').value = '';
    document.getElementById('deleteCategoryConfirmError').style.display = 'none';
}

// Подтверждение удаления категории (финальное)
async function confirmDeleteCategoryFinal() {
    const inputValue = document.getElementById('deleteCategoryConfirmInput').value.trim();
    const categoryName = window.currentCategoryName;
    const categoryId = window.categoryToDeleteId;
    
    if (inputValue !== categoryName) {
        showError('deleteCategoryConfirmError', 'Название не совпадает. Введите точное название категории.');
        return;
    }
    
    if (!categoryId) {
        showError('deleteCategoryConfirmError', 'Ошибка: ID категории не найден');
        return;
    }
    
    // Проверяем наличие жестов в категории
    const response = await apiRequest(`/api/v1/admin/categories/${categoryId}/signs`);
    if (!response) {
        showError('deleteCategoryConfirmError', 'Ошибка проверки категории');
        return;
    }
    
    const data = await response.json();
    if (data.success && data.data.length > 0) {
        closeDeleteCategoryConfirmModal();
        closeCategoryModal();
        // Показываем модальное окно с предупреждением о жестах
        currentDeleteCategoryId = categoryId;
        currentDeleteCategorySigns = data.data;
        showDeleteCategoryWarning(categoryId, data.data);
        return;
    }
    
    const confirmButton = document.getElementById('confirmDeleteCategoryButton');
    confirmButton.disabled = true;
    confirmButton.textContent = 'Удаление...';
    
    try {
        const deleteResponse = await apiRequest(`/api/v1/admin/categories/${categoryId}`, {
            method: 'DELETE'
        });
        
        if (!deleteResponse) {
            confirmButton.disabled = false;
            confirmButton.textContent = 'Удалить';
            return;
        }
        
        const deleteData = await deleteResponse.json();
        if (deleteData.success) {
            showNotification('Категория удалена', 'success');
            closeDeleteCategoryConfirmModal();
            closeCategoryModal();
            loadCategories();
        } else {
            showError('deleteCategoryConfirmError', deleteData.error?.message || 'Ошибка удаления');
            confirmButton.disabled = false;
            confirmButton.textContent = 'Удалить';
        }
    } catch (error) {
        console.error('Ошибка удаления категории:', error);
        showError('deleteCategoryConfirmError', 'Ошибка соединения с сервером');
        confirmButton.disabled = false;
        confirmButton.textContent = 'Удалить';
    }
}

// Закрытие модальных окон при клике вне их
window.addEventListener('click', (event) => {
    const modals = ['categoryModal', 'deleteCategoryModal', 'deleteCategoryConfirmModal'];
    modals.forEach(modalId => {
        const modal = document.getElementById(modalId);
        if (event.target === modal) {
            modal.classList.remove('show');
        }
    });
});

