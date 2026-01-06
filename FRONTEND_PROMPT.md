# 🎯 Prompt for UI/UX Design Tool
## Complete Qanouni-AI Frontend (Arabic Legal AI)

---

## ⚠️ CRITICAL REQUIREMENTS

You MUST create a **COMPLETE, FUNCTIONAL** frontend, not just visual mockups.
Each page MUST include:
1. HTML structure
2. CSS styling (Tailwind or custom)
3. **FULL JavaScript** with API integration

---

## 🔧 Technical Constraints

### API URL Configuration (MANDATORY in EVERY page)
```javascript
// Put this at the TOP of every page's script
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000/api' 
    : '/api';
```

### Authentication Header (for protected pages)
```javascript
function getAuthHeader() {
    const token = localStorage.getItem('token');
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
}
```

---

## 📄 Page 1: Login/Register (`login.html`)

### Design
- Split layout: Form on left, branding on right (RTL: reversed)
- Glassmorphism cards, dark theme (#0f172a background)
- Tab switching between Login and Register
- Arabic fonts (Noto Sans Arabic or Tajawal)

### Form Fields

**Login Tab:**
- Username (text)
- Password (password with show/hide toggle)
- Submit button "تسجيل الدخول"

**Register Tab:**
- Full Name (text)
- Username (text)  
- Email (text, optional)
- Password (password)
- Role selector: "عادي" / "مميز" (radio buttons)
- Submit button "إنشاء حساب"

### Required JavaScript

```javascript
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000/api' : '/api';

// Tab switching
function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
    document.getElementById(`${tab}-form`).classList.remove('hidden');
}

// Login
async function login(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const res = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        const data = await res.json();
        
        if (data.success) {
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            window.location.href = 'index.html';
        } else {
            showError(data.detail || 'خطأ في تسجيل الدخول');
        }
    } catch (err) {
        showError('خطأ في الاتصال بالخادم');
    }
}

// Register
async function register(e) {
    e.preventDefault();
    const formData = {
        username: document.getElementById('reg-username').value,
        password: document.getElementById('reg-password').value,
        full_name: document.getElementById('reg-fullname').value,
        email: document.getElementById('reg-email').value || null,
        role: document.querySelector('input[name="role"]:checked').value
    };
    
    try {
        const res = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(formData)
        });
        const data = await res.json();
        
        if (data.success) {
            showSuccess('تم إنشاء الحساب بنجاح');
            switchTab('login');
        } else {
            showError(data.detail || 'خطأ في التسجيل');
        }
    } catch (err) {
        showError('خطأ في الاتصال بالخادم');
    }
}

function showError(msg) {
    const el = document.getElementById('error-msg');
    el.textContent = msg;
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 5000);
}

function showSuccess(msg) {
    const el = document.getElementById('success-msg');
    el.textContent = msg;
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 5000);
}
```

---

## 📄 Page 2: Main Dashboard (`index.html`)

### Layout Structure
```
┌─────────────────────────────────────────────────┐
│ [Sidebar]  │        [Main Content Area]         │
│            │                                    │
│ - Logo     │   Dynamic content based on         │
│ - Nav      │   selected menu item               │
│ - User     │                                    │
│ - Logout   │                                    │
└─────────────────────────────────────────────────┘
```

### Sidebar Navigation (Arabic, RTL)
1. 📤 رفع الوثائق (Upload)
2. 🔍 الباحث القانوني الذكي (Legal Research)
3. ⚖️ المستشار القانوني (Consultant)
4. 📝 توليد المرافعات (Pleading)
5. 📁 إدارة القضايا (Cases)
6. 📚 الاجتهادات القضائية (Jurisprudence)

### Required JavaScript (section switching)
```javascript
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000/api' : '/api';

function getAuthHeader() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
    };
}

// Check auth on load
document.addEventListener('DOMContentLoaded', () => {
    if (!localStorage.getItem('token')) {
        window.location.href = 'login.html';
    }
    loadUserInfo();
    switchSection('search'); // default section
});

function loadUserInfo() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    document.getElementById('user-name').textContent = user.username || 'مستخدم';
    document.getElementById('user-role').textContent = user.role === 'premium' ? 'مميز' : 'عادي';
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = 'login.html';
}

function switchSection(section) {
    document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));
    document.getElementById(`section-${section}`).classList.remove('hidden');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`[data-section="${section}"]`).classList.add('active');
}
```

---

## 📄 Section: Legal Research (الباحث القانوني الذكي)

### UI Elements
- Large search input with placeholder "اكتب سؤالك القانوني..."
- Quick tags (pills): عقوبات، أحوال شخصية، عقود، إجراءات
- Submit button "ابحث"
- Results area (Markdown rendered)
- Sources list (collapsible)
- Loading spinner

### JavaScript
```javascript
async function searchLegal() {
    const query = document.getElementById('search-input').value;
    if (!query) return;
    
    showLoading(true);
    try {
        const res = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: getAuthHeader(),
            body: JSON.stringify({query, filters: null})
        });
        const data = await res.json();
        
        document.getElementById('result-answer').innerHTML = marked.parse(data.answer);
        renderSources(data.sources);
    } catch (err) {
        showError('خطأ في البحث');
    }
    showLoading(false);
}
```

---

## 📄 Section: Legal Consultant (المستشار القانوني)

### UI Elements
- Large textarea "صف مشكلتك القانونية..."
- Submit button "احصل على استشارة"
- Result card with Markdown

### JavaScript
```javascript
async function getConsultation() {
    const situation = document.getElementById('situation-input').value;
    showLoading(true);
    
    const res = await fetch(`${API_URL}/legal-consultant`, {
        method: 'POST',
        headers: getAuthHeader(),
        body: JSON.stringify({situation})
    });
    const data = await res.json();
    
    document.getElementById('consultation-result').innerHTML = marked.parse(data.consultation);
    showLoading(false);
}
```

---

## 📄 Section: Pleading Generator (توليد المرافعات)

### UI Elements
- Dropdown "اختر قضية محفوظة" (populated from /api/cases)
- OR Manual entry fields:
  - Case number, Defendant, Charges, Facts, Court
- Pleading type selector: دفاع / استئناف / نقض
- Generate button
- Result with copy/print buttons

### JavaScript
```javascript
async function loadCases() {
    const res = await fetch(`${API_URL}/cases`, {headers: getAuthHeader()});
    const data = await res.json();
    const select = document.getElementById('case-select');
    select.innerHTML = '<option value="">-- اختر قضية --</option>';
    data.cases.forEach(c => {
        select.innerHTML += `<option value="${c.id}">${c.case_number} - ${c.case_type}</option>`;
    });
}

async function generatePleading() {
    const caseData = getCaseFormData(); // collect from form
    const pleadingType = document.querySelector('input[name="pleading-type"]:checked').value;
    
    const res = await fetch(`${API_URL}/legal/pleading`, {
        method: 'POST',
        headers: getAuthHeader(),
        body: JSON.stringify({case_data: caseData, pleading_type: pleadingType})
    });
    const data = await res.json();
    
    document.getElementById('pleading-result').innerHTML = marked.parse(data.pleading);
}
```

---

## 📄 Section: Cases Management (إدارة القضايا)

### API Endpoints
- GET `/api/cases` - List all
- POST `/api/cases` - Create new
- GET `/api/cases/{id}` - Get one
- PUT `/api/cases/{id}` - Update
- DELETE `/api/cases/{id}` - Delete

### UI Elements
- Grid of case cards
- "+ قضية جديدة" button
- Modal for create/edit form
- Delete confirmation

---

## 📄 Section: Jurisprudence (الاجتهادات القضائية)

### API Endpoint
POST `/api/legal/jurisprudence`
```json
{"legal_issue": "...", "chamber": "الغرفة الجزائية", "top_k": 20}
```

---

## 🎨 Design System

### Colors
```css
--primary: #743df5;
--bg-dark: #0f172a;
--card-dark: #1e293b;
--text: #f1f5f9;
--text-muted: #94a3b8;
```

### Typography
```css
font-family: 'Noto Sans Arabic', 'Tajawal', sans-serif;
```

### Components
- Glassmorphism panels: `backdrop-blur-xl bg-white/5 border border-white/10`
- Buttons: Gradient, rounded-lg, shadow
- Inputs: Glass effect, focus ring
- Cards: Hover lift effect

---

## ✅ Delivery Checklist

For EACH page, you must provide:
- [ ] Complete HTML structure
- [ ] All CSS (inline or in `<style>`)
- [ ] **Full JavaScript with API calls**
- [ ] Error handling
- [ ] Loading states
- [ ] Responsive design

---

*Generate ALL pages. Do NOT skip JavaScript.*
