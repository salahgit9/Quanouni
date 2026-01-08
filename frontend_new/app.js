// التكوين - Smart API URL
// On localhost (dev), use port 8000. On cloud, use relative path.
const API_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api'
    : '/api';

// الحالة التطبيق
const state = {
    currentTab: 'welcome',
    isUploading: false,
    isSearching: false,
    cases: [],
    currentUser: null,
    token: null
};

// التهيئة
document.addEventListener('DOMContentLoaded', () => {
    // التحقق من تسجيل الدخول
    checkAuth();

    setupNavigation();
    setupTheme();
    setupMobileMenu(); // Mobile Menu Logic
    setupUpload();
    setupSearch();
    setupCases();
    setupPleading();
    setupJurisprudence();
    setupConsultant();
    loadDocuments();

    // Force UI update to match initial state (welcome)
    switchTab(state.currentTab);
});

// --- القائمة الجانبية (موبايل + سطح المكتب) ---
function setupMobileMenu() {
    const mobileBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (mobileBtn && sidebar && overlay) {
        mobileBtn.addEventListener('click', () => {
            if (window.innerWidth > 768) {
                // Desktop: Toggle Collapse
                sidebar.classList.toggle('collapsed');
            } else {
                // Mobile: Toggle Active/Overlay
                sidebar.classList.toggle('active');
                overlay.classList.toggle('active');
            }
        });

        overlay.addEventListener('click', () => {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
        });

        // Close on nav item click (mobile only)
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('active');
                    overlay.classList.remove('active');
                }
            });
        });
    }
}

// --- المصادقة ---

function checkAuth() {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');

    if (!token || !userStr) {
        // لم يسجل دخول - تحويل لصفحة الدخول
        window.location.href = 'login.html';
        return;
    }

    try {
        const user = JSON.parse(userStr);
        state.currentUser = user;
        state.token = token;

        // عرض معلومات المستخدم
        displayUserInfo(user);

        // تطبيق الصلاحيات
        applyPermissions(user.role);
    } catch (e) {
        console.error('Error parsing user data:', e);
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    }
}

function displayUserInfo(user) {
    const userInfoDiv = document.getElementById('user-info');
    const userNameEl = document.getElementById('user-name');
    const userRoleEl = document.getElementById('user-role');

    if (userInfoDiv && userNameEl && userRoleEl) {
        userNameEl.textContent = user.full_name || user.username;
        userRoleEl.textContent = user.role === 'premium' ? 'مستخدم مميز' : 'مستخدم عادي';
        userRoleEl.className = `user-role ${user.role}`;
        userInfoDiv.style.display = 'flex';
    }
}

function applyPermissions(role) {
    // 1. Admin Logic: Show everything
    if (role === 'admin') {
        return;
    }

    // 2. Hide Admin-Only Items for non-admins
    const adminItems = document.querySelectorAll('[data-role="admin"]');
    adminItems.forEach(item => {
        item.style.display = 'none';
    });

    if (role === 'premium') {
        // Premium has access to everything EXCEPT admin items (hidden above)
        return;
    }

    // 3. Normal user - Hide Premium Features
    const premiumItems = document.querySelectorAll('[data-premium="true"]');
    premiumItems.forEach(item => {
        item.classList.add('restricted');
        item.style.opacity = '0.5';
        item.style.pointerEvents = 'none';
        item.title = 'هذه الميزة متاحة فقط للمستخدمين المميزين';
    });

    // Redirect if current tab is restricted
    const currentTab = state.currentTab;
    const currentTabEl = document.querySelector(`[data-tab="${currentTab}"]`);
    if (currentTabEl && (currentTabEl.dataset.premium === 'true' || currentTabEl.dataset.role === 'admin')) {
        switchTab('search');
    }
}

function handleLogout() {
    if (confirm('هل تريد تسجيل الخروج؟')) {
        // حذف البيانات من localStorage
        localStorage.removeItem('token');
        localStorage.removeItem('user');

        // التحويل لصفحة الدخول
        window.location.href = 'login.html';
    }
}

// تحديث fetch لإرسال token
const originalFetch = window.fetch;
window.fetch = function (...args) {
    const [url, config = {}] = args;

    // إذا كان API request
    if (url.includes('/api/')) {
        config.headers = config.headers || {};
        const token = localStorage.getItem('token');
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
    }

    return originalFetch(url, config)
        .then(response => {
            // إذا 401 - تسجيل خروج تلقائي
            if (response.status === 401) {
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                window.location.href = 'login.html';
            }
            return response;
        });
};


// --- إدارة السمة ---
function setupTheme() {
    const themeBtn = document.getElementById('theme-toggle');
    const body = document.body;
    const icon = themeBtn.querySelector('i');
    const text = themeBtn.querySelector('span');

    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        body.classList.add('light-mode');
        updateThemeUI(true);
    }

    themeBtn.addEventListener('click', () => {
        body.classList.toggle('light-mode');
        const isLight = body.classList.contains('light-mode');
        localStorage.setItem('theme', isLight ? 'light' : 'dark');
        updateThemeUI(isLight);
    });

    function updateThemeUI(isLight) {
        if (isLight) {
            icon.className = 'fa-solid fa-sun';
            text.textContent = 'الوضع النهاري';
        } else {
            icon.className = 'fa-solid fa-moon';
            text.textContent = 'الوضع الليلي';
        }
    }
}

// --- التنقل ---
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.dataset.tab;
            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.module-section');

    navItems.forEach(item => {
        item.classList.toggle('active', item.dataset.tab === tabId);
    });

    sections.forEach(section => {
        section.classList.remove('active');
        if (section.id === `${tabId}-section`) {
            section.classList.add('active');
        }
    });

    state.currentTab = tabId;
}

// --- رفع الملفات ---
function setupUpload() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) handleFiles(e.target.files);
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
    });
}

async function handleFiles(files) {
    const validFiles = Array.from(files).filter(file =>
        file.name.endsWith('.txt') ||
        file.name.endsWith('.docx') ||
        file.name.endsWith('.xlsx')
    );

    if (validFiles.length === 0) {
        alert('لم يتم اختيار ملفات صالحة. الصيغ المدعومة: .txt, .docx, .xlsx');
        return;
    }

    uploadFiles(validFiles);
}

async function uploadFiles(files) {
    const uploadStatus = document.getElementById('upload-status');
    const progressFill = document.getElementById('progress-fill');
    const statusText = document.getElementById('status-text');

    state.isUploading = true;
    uploadStatus.style.display = 'block';
    progressFill.style.width = '0%';
    statusText.textContent = `جاري تجهيز ${files.length} ملف...`;

    const formData = new FormData();
    files.forEach(file => {
        formData.append('files', file);
    });

    // إضافة نوع الوثيقة
    const docType = document.getElementById('doc-type').value;
    formData.append('doc_type', docType);

    try {
        progressFill.style.width = '30%';
        statusText.textContent = `جاري رفع ${files.length} ملف...`;

        const response = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `خطأ في الرفع (${response.status})`);
        }

        const result = await response.json();

        progressFill.style.width = '100%';
        statusText.textContent = `تم! معالجة ${result.data.length} ملف.`;
        statusText.style.color = 'var(--success-color)';

        const errors = result.data.filter(r => r.status === 'خطأ' || r.status === 'error');
        if (errors.length > 0) {
            statusText.textContent += ` (${errors.length} أخطاء)`;
            statusText.style.color = 'var(--warning-color)';
        }

        setTimeout(() => {
            uploadStatus.style.display = 'none';
            statusText.style.color = 'var(--text-secondary)';
            loadDocuments();
        }, 3000);

    } catch (error) {
        console.error(error);
        statusText.textContent = `خطأ: ${error.message}`;
        statusText.style.color = 'var(--danger-color)';
    } finally {
        state.isUploading = false;
    }
}

async function loadDocuments() {
    try {
        const response = await fetch(`${API_URL}/documents`);
        const data = await response.json();

        const list = document.getElementById('documents-list');
        list.innerHTML = '';

        if (data.documents && data.documents.length > 0) {
            data.documents.forEach(doc => {
                const card = document.createElement('div');
                card.className = 'doc-card';
                card.innerHTML = `
                    <div class="doc-icon"><i class="fa-solid fa-file-lines"></i></div>
                    <div class="doc-info">
                        <h4>${doc.filename}</h4>
                        <div class="doc-meta">
                            <span>${new Date(doc.upload_date).toLocaleDateString('ar-DZ')}</span> • 
                            <span>${doc.total_chunks} جزء</span>
                        </div>
                    </div>
                `;
                list.appendChild(card);
            });
        } else {
            list.innerHTML = '<p style="color:var(--text-secondary)">لا توجد وثائق مرفوعة.</p>';
        }
    } catch (error) {
        console.error('خطأ في تحميل الوثائق:', error);
    }
}

// --- الباحث القانوني الذكي ---
function setupSearch() {
    const searchBtn = document.getElementById('search-btn');
    const searchInput = document.getElementById('search-input');

    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    // الأسئلة السريعة
    document.querySelectorAll('.quick-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            searchInput.value = btn.dataset.query;
            performSearch();
        });
    });
}

async function performSearch() {
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');
    const query = searchInput.value.trim();

    if (!query) return;

    searchResults.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> جاري البحث...</div>';

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });

        const data = await response.json();

        if (!data.answer) {
            throw new Error("لم يتم استلام إجابة من السيرفر.");
        }

        let html = `
            <div class="markdown-content">
                ${marked.parse(data.answer)}
            </div>
            <div class="sources-list">
                <h3>المصادر</h3>
        `;

        if (data.sources && data.sources.length) {
            data.sources.forEach(source => {
                html += `
                    <div class="source-card">
                        <div class="source-header">
                            <span><i class="fa-solid fa-file-lines"></i> ${source.filename}</span>
                            <span>جزء ${source.chunk_index}</span>
                        </div>
                    </div>
                `;
            });
        }

        html += '</div>';
        searchResults.innerHTML = html;
        addToolbar(searchResults, data.answer);

    } catch (error) {
        searchResults.innerHTML = `<p style="color:var(--danger-color)">خطأ: ${error.message}</p>`;
    }
}

// --- إدارة القضايا ---
function setupCases() {
    const newCaseBtn = document.getElementById('new-case-btn');
    const loadCasesBtn = document.getElementById('load-cases-btn');
    const caseFormModal = document.getElementById('case-form-modal');
    const caseForm = document.getElementById('case-form');
    const closeModalBtn = caseFormModal?.querySelector('.close-modal');
    const cancelBtn = caseFormModal?.querySelector('.btn-cancel');

    if (newCaseBtn) {
        newCaseBtn.addEventListener('click', () => {
            caseFormModal.style.display = 'flex';
        });
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            caseFormModal.style.display = 'none';
        });
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            caseFormModal.style.display = 'none';
        });
    }

    if (loadCasesBtn) {
        loadCasesBtn.addEventListener('click', loadCases);
    }

    if (caseForm) {
        caseForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveCase(caseForm);
        });
    }

    loadCases();
}

async function loadCases() {
    try {
        const response = await fetch(`${API_URL}/cases`);
        const data = await response.json();

        const casesList = document.getElementById('cases-list');
        if (!casesList) return;

        if (data.cases && data.cases.length > 0) {
            casesList.innerHTML = '';
            data.cases.forEach(c => {
                const card = document.createElement('div');
                card.className = 'doc-card case-card';
                card.innerHTML = `
                    <div class="doc-icon"><i class="fa-solid fa-folder-open"></i></div>
                    <div class="doc-info">
                        <h4>${c.case_number}</h4>
                        <div class="doc-meta">
                            <span>${c.case_type}</span> • 
                            <span>${c.court}</span>
                        </div>
                        <span class="case-status">${c.status}</span>
                    </div>
                `;
                card.addEventListener('click', () => viewCase(c.case_id));
                casesList.appendChild(card);
            });
        } else {
            casesList.innerHTML = `
                <div class="placeholder-state">
                    <i class="fa-solid fa-folder-plus"></i>
                    <p>لا توجد قضايا. أضف قضية جديدة للبدء.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('خطأ في تحميل القضايا:', error);
    }
}

async function saveCase(form) {
    const formData = new FormData(form);

    // Build payload matching backend CaseCreate model
    const caseData = {
        case_number: formData.get('case_number'),
        case_type: formData.get('case_type'),
        court: formData.get('court'),
        defendant_name: formData.get('defendant_name'),
        plaintiff_name: formData.get('plaintiff_name') || '',
        charges: formData.get('charges') ? formData.get('charges').split(',').map(c => c.trim()) : [],
        facts: formData.get('facts') || '',
        notes: formData.get('notes') || ''
    };

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_URL}/cases`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(caseData)  // Send flat, not nested
        });

        if (response.ok) {
            const result = await response.json();
            alert(result.message || 'تم حفظ القضية بنجاح!');
            form.reset();
            document.getElementById('case-form-modal').style.display = 'none';
            loadCases();
        } else {
            const err = await response.json();
            throw new Error(err.detail || 'فشل حفظ القضية');
        }
    } catch (error) {
        alert('خطأ: ' + error.message);
    }
}

async function viewCase(caseId) {
    try {
        const response = await fetch(`${API_URL}/cases/${caseId}`);
        const data = await response.json();
        console.log('بيانات القضية:', data);
        // يمكن إضافة عرض تفاصيل القضية هنا
    } catch (error) {
        console.error('خطأ في عرض القضية:', error);
    }
}

// --- توليد المرافعات ---
function setupPleading() {
    const generateBtn = document.getElementById('generate-pleading-btn');
    const caseSelect = document.getElementById('pleading-case-select');

    if (generateBtn) {
        generateBtn.addEventListener('click', generatePleading);
    }

    if (caseSelect) {
        caseSelect.addEventListener('change', loadCaseForPleading);
        loadCasesForPleading(); // تحميل القضايا عند بدء التشغيل
    }
}

async function loadCasesForPleading() {
    try {
        const response = await fetch(`${API_URL}/cases`);
        const data = await response.json();
        const caseSelect = document.getElementById('pleading-case-select');

        if (caseSelect && data.cases) {
            // Clear existing options except the first one
            caseSelect.innerHTML = '<option value="">-- اختر قضية أو اكتب يدوياً --</option>';

            data.cases.forEach(c => {
                const option = document.createElement('option');
                option.value = c.id;  // Fixed: was c.case_id
                option.textContent = `${c.case_number} - ${c.case_type}`;
                caseSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('خطأ في تحميل القضايا:', error);
    }
}

async function loadCaseForPleading() {
    const caseSelect = document.getElementById('pleading-case-select');
    const caseId = caseSelect.value;

    if (!caseId) return;

    try {
        const response = await fetch(`${API_URL}/cases/${caseId}`);
        const data = await response.json();
        const caseData = data.case;

        // ملء الحقول ببيانات القضية
        document.getElementById('pleading-case-number').value = caseData.case_number || '';
        document.getElementById('pleading-court').value = caseData.court || '';
        // Handle facts - can be string or object
        let factsText = '';
        if (typeof caseData.facts === 'string') {
            factsText = caseData.facts;
        } else if (typeof caseData.facts === 'object' && caseData.facts) {
            // Build comprehensive facts text from nested structure
            const parts = [];
            if (caseData.facts.summary) parts.push('📋 ملخص الوقائع:\n' + caseData.facts.summary);
            if (caseData.facts.defendant_version) parts.push('\n\n🛡️ رواية المتهم:\n' + caseData.facts.defendant_version);
            if (caseData.facts.victim_version) parts.push('\n\n⚖️ رواية المجني عليه:\n' + caseData.facts.victim_version);
            if (caseData.facts.contradictions && caseData.facts.contradictions.length > 0) {
                parts.push('\n\n⚠️ التناقضات:\n- ' + caseData.facts.contradictions.join('\n- '));
            }
            factsText = parts.join('');
        }
        document.getElementById('pleading-facts').value = factsText;

        // الحصول على اسم المتهم
        if (caseData.parties && caseData.parties.defendant) {
            document.getElementById('pleading-defendant').value = caseData.parties.defendant.full_name || '';
        } else if (caseData.defendant_name) {
            document.getElementById('pleading-defendant').value = caseData.defendant_name || '';
        }

        // الحصول على التهمة
        if (caseData.charges && caseData.charges.length > 0) {
            if (typeof caseData.charges[0] === 'object') {
                document.getElementById('pleading-charge').value = caseData.charges[0].charge || '';
            } else {
                document.getElementById('pleading-charge').value = caseData.charges.join(', ');
            }
        }
    } catch (error) {
        console.error('خطأ في تحميل بيانات القضية:', error);
    }
}

async function generatePleading() {
    const facts = document.getElementById('pleading-facts').value.trim();
    const defendantName = document.getElementById('pleading-defendant').value.trim();
    const court = document.getElementById('pleading-court').value.trim();
    const caseNumber = document.getElementById('pleading-case-number').value.trim();
    const charge = document.getElementById('pleading-charge').value.trim();
    const pleadingType = document.getElementById('pleading-type').value;
    const style = document.getElementById('pleading-style').value;
    const resultsContainer = document.getElementById('pleading-results');

    if (!facts && !defendantName) {
        alert('الرجاء ملء بيانات القضية أو اختيار قضية محفوظة');
        return;
    }

    resultsContainer.innerHTML = `
        <div style="text-align:center; padding: 2rem;">
            <i class="fa-solid fa-circle-notch fa-spin" style="font-size: 2rem; color: var(--accent-color);"></i>
            <p style="margin-top: 1rem;">جاري توليد المرافعة...</p>
            <p style="font-size: 0.8rem; color: var(--text-secondary);">هذا قد يستغرق دقيقة واحدة.</p>
        </div>
    `;

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_URL}/legal/pleading`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                case_data: {
                    case_number: caseNumber,
                    facts: facts,
                    case_type: 'جنائي',
                    court: court || 'محكمة الجنايات',
                    defendant_name: defendantName,
                    charges: charge ? [charge] : []
                },
                pleading_type: pleadingType,
                style: style,
                top_k: 30
            })
        });

        if (!response.ok) throw new Error('فشل توليد المرافعة');

        const data = await response.json();

        let html = `
            <div class="pleading-header">
                <h3><i class="fa-solid fa-file-signature"></i> ${pleadingType === 'دفاع' ? 'مذكرة دفاع' : pleadingType === 'استئناف' ? 'عريضة استئناف' : 'طعن بالنقض'}</h3>
                <span class="pleading-style">${style}</span>
            </div>
            <div class="markdown-content">
                ${marked.parse(data.pleading)}
            </div>
            <div class="sources-list">
                <h3>المصادر المستخدمة (${data.metadata.total_sources})</h3>
        `;

        if (data.sources && data.sources.length) {
            data.sources.forEach(source => {
                html += `
                    <div class="source-card">
                        <div class="source-header">
                            <span><i class="fa-solid fa-file-lines"></i> ${source.filename}</span>
                        </div>
                    </div>
                `;
            });
        }

        html += '</div>';
        resultsContainer.innerHTML = html;
        addToolbar(resultsContainer, data.pleading);

    } catch (error) {
        resultsContainer.innerHTML = `
            <div style="color: var(--danger-color); text-align: center;">
                <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem;"></i>
                <p>خطأ في التوليد: ${error.message}</p>
            </div>
        `;
    }
}

// --- البحث في الاجتهادات ---
function setupJurisprudence() {
    const searchBtn = document.getElementById('search-jurisprudence-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', searchJurisprudence);
    }
}

async function searchJurisprudence() {
    const legalIssue = document.getElementById('legal-issue').value.trim();
    const chamber = document.getElementById('chamber-filter').value;
    const resultsContainer = document.getElementById('jurisprudence-results');

    if (!legalIssue) {
        alert('الرجاء إدخال المسألة القانونية');
        return;
    }

    resultsContainer.innerHTML = `
        <div style="text-align:center; padding: 2rem;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--accent-color);"></i>
            <p style="margin-top: 1rem;">جاري البحث في الاجتهادات...</p>
        </div>
    `;

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_URL}/legal/jurisprudence`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                legal_issue: legalIssue,
                chamber: chamber || null,
                top_k: 20
            })
        });

        if (!response.ok) throw new Error('فشل البحث');

        const data = await response.json();

        let html = `
            <div class="jurisprudence-header">
                <h3><i class="fa-solid fa-gavel"></i> نتائج البحث: ${legalIssue}</h3>
            </div>
            <div class="markdown-content">
                ${marked.parse(data.analysis)}
            </div>
            <div class="sources-list">
                <h3>المصادر (${data.metadata.total_sources})</h3>
        `;

        if (data.sources && data.sources.length) {
            data.sources.forEach(source => {
                html += `
                    <div class="source-card">
                        <div class="source-header">
                            <span><i class="fa-solid fa-book"></i> ${source.filename}</span>
                            ${source.relevance_score ? `<span>صلة: ${(source.relevance_score * 100).toFixed(0)}%</span>` : ''}
                        </div>
                        ${source.snippet ? `<div class="source-snippet" style="font-size: 0.9em; color: var(--text-secondary); margin-top: 0.5rem; border-right: 2px solid var(--accent-color); padding-right: 0.5rem; background: rgba(0,0,0,0.1); padding: 5px;">"${source.snippet.replace(/[#*]/g, '').trim()}..."</div>` : ''}
                    </div>
                `;
            });
        }

        html += '</div>';
        resultsContainer.innerHTML = html;
        addToolbar(resultsContainer, data.analysis);

    } catch (error) {
        resultsContainer.innerHTML = `
            <div style="color: var(--danger-color); text-align: center;">
                <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem;"></i>
                <p>خطأ في البحث: ${error.message}</p>
            </div>
        `;
    }
}

// --- المستشار القانوني ---
function setupConsultant() {
    const consultBtn = document.getElementById('get-consultation-btn');
    if (!consultBtn) return;

    consultBtn.addEventListener('click', getConsultation);
}

async function getConsultation() {
    const situationInput = document.getElementById('situation-input');
    const resultsContainer = document.getElementById('consultation-results');
    const consultBtn = document.getElementById('get-consultation-btn');

    const situation = situationInput.value.trim();

    if (!situation) {
        alert('يرجى وصف وضعك القانوني قبل طلب الاستشارة');
        return;
    }

    if (situation.length < 10) {
        alert('يرجى تقديم وصف أكثر تفصيلاً للوضع (10 حرفاً على الأقل)');
        return;
    }

    // إظهار حالة التحميل
    consultBtn.disabled = true;
    consultBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> جاري تحليل وضعك...';

    resultsContainer.innerHTML = `
        <div class="loading-state">
            <i class="fa-solid fa-balance-scale fa-2x fa-pulse"></i>
            <p>جاري البحث في القوانين وتحليل وضعك القانوني...</p>
            <small>قد يستغرق هذا حتى دقيقة</small>
        </div>
    `;

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_URL}/legal-consultant`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ situation: situation })
        });

        if (!response.ok) throw new Error('فشل في الحصول على الاستشارة');

        const data = await response.json();

        if (data.status === 'error') {
            throw new Error(data.consultation);
        }

        // عرض الاستشارة
        displayConsultation(data, resultsContainer);

    } catch (error) {
        console.error('خطأ:', error);
        resultsContainer.innerHTML = `
            <div class="error-state">
                <i class="fa-solid fa-exclamation-triangle"></i>
                <p>حدث خطأ أثناء معالجة طلبك</p>
                <small>${error.message}</small>
            </div>
        `;
    } finally {
        consultBtn.disabled = false;
        consultBtn.innerHTML = '<i class="fa-solid fa-comments"></i> احصل على التوجيه القانوني';
    }
}

function displayConsultation(data, container) {
    const consultation = data.consultation || '';
    const sources = data.sources || [];

    // تحويل Markdown إلى HTML بسيط
    let formattedConsultation = consultation
        .replace(/## (.*)/g, '<h3 class="consultation-section">$1</h3>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/^- (.*)/gm, '<li>$1</li>')
        .replace(/^\d+\. (.*)/gm, '<li>$1</li>')
        .replace(/\n---\n/g, '<hr class="consultation-divider">')
        .replace(/\n\n/g, '</p><p>')
        .replace(/^(.*)$/gm, function (match) {
            if (match.startsWith('<')) return match;
            return match;
        });

    // لف القوائم
    formattedConsultation = formattedConsultation.replace(/(<li>.*<\/li>\s*)+/g, '<ul class="consultation-list">$&</ul>');

    let html = `
        <div class="consultation-container">
            <div class="consultation-header">
                <i class="fa-solid fa-user-tie"></i>
                <h3>التوجيه القانوني لوضعك</h3>
            </div>
            
            <div class="consultation-content">
                ${formattedConsultation}
            </div>
    `;

    // إضافة المصادر
    if (sources.length > 0) {
        html += `
            <div class="consultation-sources">
                <h4><i class="fa-solid fa-book"></i> المصادر المستخدمة</h4>
                <div class="sources-grid">
        `;
        sources.forEach((source, index) => {
            const filename = source.filename || `مصدر ${index + 1}`;
            html += `
                <div class="source-chip">
                    <i class="fa-solid fa-file-lines"></i>
                    ${filename.replace('.txt', '').replace('_', ' ')}
                </div>
            `;
        });
        html += '</div></div>';
    }

    html += '</div>';

    container.innerHTML = html;

    // إضافة أزرار النسخ والطباعة
    addToolbar(container, consultation);
}

// --- أدوات مساعدة ---
function addToolbar(container, contentToProcess) {
    const toolbar = document.createElement('div');
    toolbar.className = 'response-toolbar';

    const copyBtn = document.createElement('button');
    copyBtn.className = 'toolbar-btn';
    copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> نسخ';
    copyBtn.onclick = () => copyToClipboard(contentToProcess, copyBtn);

    const printBtn = document.createElement('button');
    printBtn.className = 'toolbar-btn';
    printBtn.innerHTML = '<i class="fa-solid fa-print"></i> طباعة';
    printBtn.onclick = () => window.print();

    toolbar.appendChild(copyBtn);
    toolbar.appendChild(printBtn);
    container.appendChild(toolbar);
}

async function copyToClipboard(text, btn) {
    try {
        await navigator.clipboard.writeText(text);
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check"></i> تم النسخ!';
        btn.classList.add('success');

        setTimeout(() => {
            btn.innerHTML = originalHtml;
            btn.classList.remove('success');
        }, 2000);
    } catch (err) {
        console.error('خطأ في النسخ:', err);
        alert('تعذر نسخ النص');
    }
}
