document.addEventListener('DOMContentLoaded', () => {
    fetchHomeLibrary();
    fetchTrendingManga();
    setupNavigation();
    setupNotifications();
});

// Navigation State
const views = {
    'home': document.getElementById('home-view'),
    'library': document.getElementById('library-view'),
    'history': document.getElementById('history-view'),
    'browse': document.getElementById('browse-view'),
    'settings': document.getElementById('settings-view'),
    'detail': document.getElementById('detail-view'),
    'reader': document.getElementById('reader-view')
};

function navigateTo(viewName) {
    // Hide all views
    Object.values(views).forEach(el => el && el.classList.add('hidden'));

    // Show target view
    if (views[viewName]) {
        views[viewName].classList.remove('hidden');
    }

    // Refresh data if needed
    if (viewName === 'home') {
        const grid = document.getElementById('trending-grid');
        // Refresh home data
        fetchHomeLibrary();
        if (grid && grid.children.length === 0) {
            fetchTrendingManga(1);
        }
    }
    if (viewName === 'library') fetchLibrary();
    if (viewName === 'history') fetchHistory();
    if (viewName === 'browse') fetchExtensions();

    // Update Sidebar Active State
    document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));

    // Simple mapping for sidebar highlighting
    if (viewName === 'home') document.querySelector('.nav-links li:nth-child(1)').classList.add('active');
    if (viewName === 'browse') document.querySelector('.nav-links li:nth-child(2)').classList.add('active');
    if (viewName === 'library') document.querySelector('.nav-links li:nth-child(3)').classList.add('active');
    if (viewName === 'history') document.querySelector('.nav-links li:nth-child(4)').classList.add('active');
    if (viewName === 'settings') document.querySelector('.nav-links li:nth-child(5)').classList.add('active');
}

function setupNavigation() {
    // Sidebar clicks
    document.querySelector('.nav-links li:nth-child(1) a').onclick = (e) => { e.preventDefault(); navigateTo('home'); };
    document.querySelector('.nav-links li:nth-child(2) a').onclick = (e) => { e.preventDefault(); navigateTo('browse'); };
    document.querySelector('.nav-links li:nth-child(3) a').onclick = (e) => { e.preventDefault(); navigateTo('library'); };
    document.querySelector('.nav-links li:nth-child(4) a').onclick = (e) => { e.preventDefault(); navigateTo('history'); };
    document.querySelector('.nav-links li:nth-child(5) a').onclick = (e) => { e.preventDefault(); navigateTo('settings'); };

    // Theme Toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('change', (e) => {
            if (!e.target.checked) {
                // Light Mode (Simulated)
                document.documentElement.style.setProperty('--bg-dark', '#f8fafc');
                document.documentElement.style.setProperty('--bg-secondary', '#ffffff');
                document.documentElement.style.setProperty('--card-bg', '#ffffff');
                document.documentElement.style.setProperty('--text-primary', '#0f172a');
                document.documentElement.style.setProperty('--text-secondary', '#64748b');
            } else {
                // Dark Mode Reset
                document.documentElement.style.removeProperty('--bg-dark');
                document.documentElement.style.removeProperty('--bg-secondary');
                document.documentElement.style.removeProperty('--card-bg');
                document.documentElement.style.removeProperty('--text-primary');
                document.documentElement.style.removeProperty('--text-secondary');
            }
        });
    }
}

function setAccent(color, el) {
    document.documentElement.style.setProperty('--accent', color);
    document.documentElement.style.setProperty('--accent-hover', color);

    document.querySelectorAll('.color-dot').forEach(dot => dot.classList.remove('active'));
    el.classList.add('active');
}

// --- Trending / Home ---

// --- Trending / Home ---

// --- Trending / Home ---

// --- Trending / Home ---

let currentPage = 1;

function timeSince(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + " năm trước";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + " tháng trước";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " ngày trước";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " giờ trước";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " phút trước";
    return "Vừa xong";
}

async function fetchTrendingManga(page = 1) {
    const grid = document.getElementById('trending-grid');
    const newMangaGrid = document.getElementById('new-manga-grid');
    const newMangaSection = document.getElementById('new-manga-section');

    // Keep reference to pagination container or create if not exists
    let pagination = document.getElementById('pagination-controls');
    if (!pagination) {
        pagination = document.createElement('div');
        pagination.id = 'pagination-controls';
        pagination.className = 'pagination';
        document.getElementById('home-view').appendChild(pagination);
    }

    // Only show loading in trending grid
    grid.innerHTML = `<div class="loading-skeleton"></div><div class="loading-skeleton"></div><div class="loading-skeleton"></div>`;

    try {
        const response = await fetch(`/api/trending?page=${page}`);
        if (!response.ok) throw new Error('Failed to fetch');
        const data = await response.json();

        currentPage = page;

        grid.innerHTML = '';

        // Handle new structured response: { active_manga: [], new_manga: [] }
        const activeManga = data.active_manga || [];
        const newManga = data.new_manga || [];

        if (activeManga.length === 0 && newManga.length === 0) {
            grid.innerHTML = '<p>Không có dữ liệu.</p>';
            return;
        }

        // 1. Render Active Manga (always update on page change)
        // Limit to 18 items for clean 3-row display (6 per row)
        const displayLimit = 18;
        const displayManga = activeManga.slice(0, displayLimit);

        displayManga.forEach(manga => {
            grid.appendChild(createMangaCard(manga));
        });

        // 2. Render New Manga ONLY on first load (when section is empty)
        // This keeps newMangaGrid stable during pagination
        if (newMangaSection && newMangaGrid) {
            const isFirstLoad = newMangaGrid.children.length === 0;

            if (isFirstLoad && newManga.length > 0) {
                newMangaSection.classList.remove('hidden');
                newManga.forEach(manga => {
                    newMangaGrid.appendChild(createMangaCard(manga));
                });
            } else if (isFirstLoad && newManga.length === 0) {
                newMangaSection.classList.add('hidden');
            }
            // If not first load, do nothing to newMangaGrid - keep it as is
        }

        // Update Pagination Controls
        updatePagination(pagination, page, activeManga.length > 0);

    } catch (error) {
        console.error('Error:', error);
        grid.innerHTML = '<p class="error-msg">Không thể tải truyện.</p>';
    }
}

function updatePagination(container, page, hasData) {
    // Generate page options (show up to 20 pages for selection)
    const maxPages = 20;
    let pageOptions = '';
    for (let i = 1; i <= maxPages; i++) {
        pageOptions += `<option value="${i}" ${i === page ? 'selected' : ''}>Trang ${i}</option>`;
    }

    container.innerHTML = `
        <button class="pagination-btn" ${page <= 1 ? 'disabled' : ''} onclick="changePage(${page - 1})">
            <i class="fa-solid fa-chevron-left"></i>
            <span>Trước</span>
        </button>
        
        <div class="page-selector">
            <select class="page-select" onchange="changePage(parseInt(this.value))">
                ${pageOptions}
            </select>
        </div>
        
        <button class="pagination-btn" ${!hasData ? 'disabled' : ''} onclick="changePage(${page + 1})">
            <span>Sau</span>
            <i class="fa-solid fa-chevron-right"></i>
        </button>
    `;
}

function changePage(newPage) {
    if (newPage < 1) return;
    fetchTrendingManga(newPage);
    // Scroll to top of grid
    document.querySelector('.content-section').scrollIntoView({ behavior: 'smooth' });
}

// Helper to use proxy
const getImgUrl = (url) => url ? `/api/proxy?url=${encodeURIComponent(url)}` : 'https://via.placeholder.com/200x300?text=No+Cover';

function createMangaCard(manga) {
    const div = document.createElement('div');
    div.classList.add('manga-card');
    div.onclick = () => showMangaDetails(manga.id);

    // Display Logic: Home vs Library
    let metaHtml = '';

    // Check if we have library-specific fields
    if (manga.latest_chapter_string) {
        // It's a library item
        metaHtml = `
            <div class="card-meta-row" style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 4px;">
                <i class="fa-regular fa-clock"></i> Mới: ${manga.latest_chapter_string.split(' - ')[0]}
            </div>
             <div class="card-meta-row" style="font-size: 0.8rem; color: var(--accent);">
                <i class="fa-solid fa-book-open"></i> ${manga.current_chapter_string || 'Bắt đầu'}
            </div>
        `;
    } else {
        // Trending/Home Mode

        let updateTimeHtml = '';
        if (manga.updated_at) {
            const timeStr = timeSince(manga.updated_at);
            updateTimeHtml = `<span style="font-size: 0.7rem; color: var(--text-secondary); margin-left: auto;">${timeStr}</span>`;
        }

        const chapterText = (manga.latest_chapter && manga.latest_chapter !== 'N/A') ? manga.latest_chapter : 'Sắp có';
        const icon = (manga.latest_chapter && manga.latest_chapter !== 'N/A') ? 'fa-list-ol' : 'fa-clock';

        metaHtml = `
             <div class="card-meta" style="align-items: center; display: flex;">
                <span class="rating" style="font-size: 0.8rem; color: var(--text-primary); display: flex; align-items: center; gap: 4px;">
                    <i class="fa-solid ${icon}"></i> ${chapterText}
                </span>
                ${updateTimeHtml}
            </div>
        `;
    }

    // Source badge for multi-source view
    const sourceBadge = manga.source_name ?
        `<div class="source-badge">${manga.source_name}</div>` : '';

    div.innerHTML = `
        ${sourceBadge}
        <img src="${getImgUrl(manga.cover)}" alt="${manga.title}" class="card-image" loading="lazy">
        <div class="card-info">
            <div class="card-title">${manga.title}</div>
            ${metaHtml}
        </div>
    `;
    // Store source for detail view
    div.dataset.source = manga.source || '';
    div.onclick = () => showMangaDetails(manga.id, manga.source);
    return div;
}


// --- Manga Details ---

function formatDescription(text) {
    if (!text) return 'Chưa có mô tả.';
    // Remove links [Show Name](url) -> Show Name
    let clean = text.replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1');
    // Remove **bold** -> bold
    clean = clean.replace(/\*\*([^\*]+)\*\*/g, '$1');
    return clean;
}

// Global state for current viewed manga (to save progress)
window.currentMangaId = null;
window.currentMangaSource = null;

async function showMangaDetails(id, source = null) {
    window.currentMangaId = id;
    window.currentMangaSource = source;
    try {
        // Include source in API call if available
        const url = source ? `/api/manga/${id}?source=${source}` : `/api/manga/${id}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch details');
        const manga = await response.json();


        // Populate Details
        document.getElementById('detail-cover').src = getImgUrl(manga.cover);
        document.getElementById('detail-title').textContent = manga.title;
        document.getElementById('detail-author').textContent = manga.author || 'Chưa rõ';
        document.getElementById('detail-rating').innerHTML = `<i class="fa-solid fa-star"></i> ${manga.rating || 'N/A'}`;

        // Use formatted description
        document.getElementById('detail-description').innerText = formatDescription(manga.description);

        // Populate Chapters
        const chapterList = document.getElementById('chapter-list-ui');
        chapterList.innerHTML = '';

        let firstChapter = null;
        if (manga.chapters && manga.chapters.length > 0) {
            // Assume the last chapter in the list is the first chapter (oldest)
            firstChapter = manga.chapters[manga.chapters.length - 1];

            manga.chapters.forEach(chap => {
                const li = document.createElement('li');
                li.classList.add('chapter-item');
                // Pass chapter ojbect directly
                li.onclick = () => openReader(chap);
                li.innerHTML = `
                    <span class="chapter-title">${chap.title}</span>
                    <span class="chapter-date">${chap.date}</span>
                `;
                chapterList.appendChild(li);
            });
        } else {
            chapterList.innerHTML = '<p style="color:var(--text-secondary)">Chưa có chương nào.</p>';
        }

        // Update Buttons
        const actionBtns = document.querySelector('.action-buttons');
        const uniqueBtnId = `btn-start-${manga.id}`;

        actionBtns.innerHTML = `
            <button class="btn-primary" onclick="addToLibrary('${manga.id}')">Thêm vào Thư Viện</button>
            <button class="btn-secondary" id="${uniqueBtnId}" ${!firstChapter ? 'disabled' : ''}>Đọc Ngay</button>
        `;

        if (firstChapter) {
            document.getElementById(uniqueBtnId).onclick = () => openReader(firstChapter);
        }

        navigateTo('detail');

    } catch (error) {
        console.error('Error fetching details:', error);
    }
}

// --- Reader ---

async function openReader(chapter) {
    document.getElementById('reader-title').textContent = chapter.title;
    const pagesContainer = document.getElementById('reader-pages');
    pagesContainer.innerHTML = '<div class="loading-spinner">Đang tải trang...</div>';

    navigateTo('reader');

    try {
        const response = await fetch(`/api/chapter/${chapter.id}`);
        if (!response.ok) throw new Error('Failed to load chapter');
        const data = await response.json();

        pagesContainer.innerHTML = '';
        data.pages.forEach(url => {
            const img = document.createElement('img');
            // Use proxy for reader images too if they are from mangadex
            img.src = getImgUrl(url);
            img.loading = 'lazy';
            pagesContainer.appendChild(img);
        });

        // Save Progress
        if (window.currentMangaId) {
            fetch(`/api/progress/${window.currentMangaId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chapter_id: chapter.id,
                    chapter_title: chapter.title
                })
            }).catch(e => console.error("Save progress failed", e));
        }

    } catch (error) {
        console.error('Reader error:', error);
        pagesContainer.innerHTML = '<p class="error-msg">Không thể tải trang truyện.</p>';
    }
}

function exitReader() {
    navigateTo('detail');
}

// --- Library ---

async function fetchLibrary() {
    const grid = document.getElementById('library-grid');
    grid.innerHTML = '<div class="loading-spinner">Loading...</div>';

    try {
        const response = await fetch('/api/library');
        if (!response.ok) throw new Error('Failed to fetch library');
        const data = await response.json();

        grid.innerHTML = '';
        if (data.length === 0) {
            grid.innerHTML = '<p class="empty-state">Your library is empty. Start adding some manga!</p>';
            return;
        }

        data.forEach(manga => {
            const card = createMangaCard(manga);
            grid.appendChild(card);
        });

    } catch (error) {
        console.error('Error:', error);
        grid.innerHTML = '<p class="error-msg">Could not load library. Is Backend Running?</p>';
    }
}

async function addToLibrary(id) {
    try {
        const response = await fetch(`/api/library/${id}`, { method: 'POST' });
        if (response.ok) {
            alert('Đã thêm vào Thư Viện!');
            fetchHomeLibrary(); // Refresh home view
        }
    } catch (error) {
        console.error('Error adding to library:', error);
    }
}

async function fetchHomeLibrary() {
    const homeLibraryGrid = document.getElementById('home-library-grid');
    const homeLibrarySection = document.getElementById('home-library-section');
    if (!homeLibraryGrid) return;

    try {
        const response = await fetch('/api/library');
        if (!response.ok) throw new Error('Failed to fetch library');
        const data = await response.json();

        if (data.length === 0) {
            homeLibrarySection.classList.add('hidden');
            return;
        }

        homeLibrarySection.classList.remove('hidden');
        homeLibraryGrid.innerHTML = '';

        // Take last 10 added/updated items for home scroll row
        const items = data.slice(0, 10);
        items.forEach(manga => {
            const card = createMangaCard(manga);
            homeLibraryGrid.appendChild(card);
        });
    } catch (error) {
        console.error('Error fetching home library:', error);
        if (homeLibrarySection) homeLibrarySection.classList.add('hidden');
    }
}

// --- Extensions ---

async function fetchExtensions() {
    const list = document.getElementById('extensions-list');
    list.innerHTML = '<div class="loading-spinner">Đang tải nguồn truyện...</div>';

    try {
        const response = await fetch('/api/extensions');
        const data = await response.json();

        list.innerHTML = '';
        data.forEach(ext => {
            const item = document.createElement('div');
            item.classList.add('extension-item');
            if (ext.active) item.classList.add('active-source');

            // Use proxy for icons to avoid broken images
            const iconUrl = ext.icon ? getImgUrl(ext.icon) : 'https://via.placeholder.com/40';

            item.innerHTML = `
                <div class="ext-info">
                    <img src="${iconUrl}" alt="" class="ext-icon" onerror="this.src='https://via.placeholder.com/40'">
                    <div>
                        <div class="ext-name">${ext.name}</div>
                        <div class="ext-lang">${ext.language || 'N/A'}</div>
                    </div>
                </div>
                <div>
                     ${ext.active
                    ? '<button class="btn-small btn-settings" disabled>Đang dùng</button>'
                    : `<button class="btn-small btn-install" onclick="selectSource('${ext.id}')">Sử dụng</button>`}
                </div>
            `;
            list.appendChild(item);
        });
    } catch (error) {
        console.error('Error:', error);
        list.innerHTML = '<p class="error-msg">Không thể tải danh sách nguồn.</p>';
    }
}

async function selectSource(id) {
    try {
        const response = await fetch(`/api/sources/select/${id}`, { method: 'POST' });
        const result = await response.json();
        if (result.status === 'success') {
            // Source changed, FORCE CLEAR EVERYTHING
            const trendingGrid = document.getElementById('trending-grid');
            const newMangaGrid = document.getElementById('new-manga-grid');
            const newMangaSection = document.getElementById('new-manga-section');

            if (trendingGrid) trendingGrid.innerHTML = '';
            if (newMangaGrid) newMangaGrid.innerHTML = '';
            if (newMangaSection) newMangaSection.classList.add('hidden');

            // Refresh extension list view
            fetchExtensions();

            // If currently on home, reload immediately
            if (currentView === 'home') {
                fetchTrendingManga(1);
            } else {
                // If not on home, the next time user clicks home it will be empty and trigger fetch
            }

            alert('Đã chuyển sang nguồn: ' + id.toUpperCase());
            navigateTo('home');
        } else {
            alert('Lỗi: ' + result.message);
        }
    } catch (error) {
        console.error('Error selecting source:', error);
    }
}

// --- History ---

async function fetchHistory() {
    const grid = document.getElementById('history-grid');
    grid.innerHTML = '<div class="loading-skeleton"></div><div class="loading-skeleton"></div>';

    try {
        const response = await fetch('/api/history');
        if (!response.ok) throw new Error('Failed to fetch history');
        const data = await response.json();

        grid.innerHTML = '';
        if (data.length === 0) {
            grid.innerHTML = '<p class="empty-state">Chưa có lịch sử đọc truyện.</p>';
            return;
        }

        data.forEach(manga => {
            const card = createMangaCard(manga);
            grid.appendChild(card);
        });

    } catch (error) {
        console.error('Error:', error);
        grid.innerHTML = '<p class="error-msg">Không thể tải lịch sử.</p>';
    }
}