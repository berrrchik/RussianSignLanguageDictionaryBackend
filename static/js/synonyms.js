// Глобальные переменные
let currentPage = 1;
let perPage = 50;
let lastSearchTerm = '';
let currentDeleteSynonymId = null;
let currentDeleteSynonymPair = null;

// Проверка авторизации при загрузке
window.addEventListener('load', async () => {
    if (!checkAuth()) return;
    loadSynonyms(1, '');
});

async function loadSynonyms(page = 1, searchTerm = '') {
    try {
        const tbody = document.getElementById('synonymsTableBody');
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem;"><div class="loading"></div> Загрузка...</td></tr>';

        let url = `${API_BASE}/synonyms?page=${page}&per_page=${perPage}`;
        if (searchTerm && searchTerm.trim()) {
            url += `&search=${encodeURIComponent(searchTerm.trim())}`;
        }

        const response = await apiRequest(url);
        if (!response) return;

        const data = await response.json();
        if (!data.success) {
            showNotification(data.error?.message || 'Ошибка загрузки синонимов', 'error');
            return;
        }

        const items = data.data?.synonyms || [];
        const pagination = data.data?.pagination;

        currentPage = page;
        lastSearchTerm = searchTerm;

        renderSynonyms(items);
        renderPagination(pagination);
    } catch (error) {
        console.error('Ошибка загрузки синонимов:', error);
        showNotification('Ошибка соединения с сервером', 'error');
    }
}

function renderSynonyms(items) {
    const tbody = document.getElementById('synonymsTableBody');
    if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem;">Связи синонимов не найдены</td></tr>';
        return;
    }

    tbody.innerHTML = items.map(item => {
        const sign1 = `${item.sign_1_word || ''} (${item.sign_1_id || ''})`;
        const sign2 = `${item.sign_2_word || ''} (${item.sign_2_id || ''})`;
        const pairDisplay = `${sign1} ↔ ${sign2}`;
        const safePair = pairDisplay.replace(/'/g, "\\'").replace(/"/g, '&quot;');

        return `
            <tr>
                <td><code>${escapeHtml(String(item.id))}</code></td>
                <td>${escapeHtml(sign1)}</td>
                <td>${escapeHtml(sign2)}</td>
                <td>${escapeHtml(item.created_at || '')}</td>
                <td style="white-space: nowrap;">
                    <button class="btn btn-danger" style="padding: 0.25rem 0.5rem; font-size: 0.9rem;" onclick="showDeleteSynonymModal(${item.id}, '${safePair}')">Удалить</button>
                </td>
            </tr>
        `;
    }).join('');
}

function renderPagination(pagination) {
    const paginationDiv = document.getElementById('pagination');
    if (!pagination || pagination.pages <= 1) {
        paginationDiv.innerHTML = '';
        return;
    }

    const escapedSearch = (lastSearchTerm || '').replace(/'/g, "\\'");

    let html = '';
    if (pagination.page > 1) {
        html += `<button onclick="loadSynonyms(${pagination.page - 1}, '${escapedSearch}')">Предыдущая</button>`;
    }

    for (let i = 1; i <= pagination.pages; i++) {
        if (i === pagination.page) {
            html += `<button class="active" disabled>${i}</button>`;
        } else if (i === 1 || i === pagination.pages || (i >= pagination.page - 2 && i <= pagination.page + 2)) {
            html += `<button onclick="loadSynonyms(${i}, '${escapedSearch}')">${i}</button>`;
        } else if (i === pagination.page - 3 || i === pagination.page + 3) {
            html += `<button disabled>...</button>`;
        }
    }

    if (pagination.page < pagination.pages) {
        html += `<button onclick="loadSynonyms(${pagination.page + 1}, '${escapedSearch}')">Следующая</button>`;
    }

    paginationDiv.innerHTML = html;
}

let searchTimeout = null;
function filterSynonyms() {
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        const searchTerm = document.getElementById('searchInput').value || '';
        loadSynonyms(1, searchTerm);
    }, 300);
}

function showDeleteSynonymModal(synonymId, pairDisplay) {
    currentDeleteSynonymId = synonymId;
    currentDeleteSynonymPair = pairDisplay;
    hideError('deleteSynonymError');
    document.getElementById('deleteSynonymPairDisplay').textContent = pairDisplay;
    document.getElementById('confirmDeleteSynonymButton').disabled = false;
    document.getElementById('deleteSynonymModal').classList.add('show');
}

function closeDeleteSynonymModal() {
    document.getElementById('deleteSynonymModal').classList.remove('show');
    currentDeleteSynonymId = null;
    currentDeleteSynonymPair = null;
    hideError('deleteSynonymError');
}

async function confirmDeleteSynonym() {
    if (!currentDeleteSynonymId) return;
    const btn = document.getElementById('confirmDeleteSynonymButton');
    btn.disabled = true;
    btn.textContent = 'Удаление...';

    try {
        const response = await apiRequest(`${API_BASE}/synonyms/${currentDeleteSynonymId}`, {
            method: 'DELETE'
        });

        if (!response) return;

        const data = await response.json();
        if (data.success) {
            showNotification('Связь синонимов удалена', 'success');
            closeDeleteSynonymModal();
            loadSynonyms(currentPage, lastSearchTerm);
        } else {
            showError('deleteSynonymError', data.error?.message || 'Ошибка удаления');
        }
    } catch (error) {
        console.error('Ошибка удаления связи синонимов:', error);
        showError('deleteSynonymError', 'Ошибка соединения с сервером');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Удалить';
    }
}

// Закрытие модальных окон при клике вне их
window.addEventListener('click', (event) => {
    const modal = document.getElementById('deleteSynonymModal');
    if (event.target === modal) {
        closeDeleteSynonymModal();
    }
});

