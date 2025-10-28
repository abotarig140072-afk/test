# ... هذا السطر موجود عندك ...
@admin_bp.before_request
def require_admin_login():
    # ... (الكود الموجود حالياً) ...
    if 'user_id' not in session:
        flash('الرجاء تسجيل الدخول للوصول لهذه الصفحة.', 'warning')
        return redirect(url_for('login'))

# --- أضف هذا المسار الجديد ---
@admin_bp.route('/')
def index():
    # هذا الكود سيقوم بإعادة توجيه أي زيارة لـ /admin/
    # إلى صفحة /admin/manage-tests تلقائياً
    return redirect(url_for('admin.manage_tests'))
# --- نهاية الإضافة ---

@admin_bp.route('/manage-tests', methods=['GET', 'POST'])
def manage_tests():
    # ... (باقي الكود كما هو) ...