# admin/__init__.py
from flask import Blueprint

# تعريف المخطط (Blueprint) لقسم الإدارة
# هذا هو التعريف الصحيح. 
# سيقوم Flask بالبحث عن القوالب في مجلد 'templates' الخاص بالتطبيق الرئيسي
# وعندما نطلب 'admin/admin_login.html' سيبحث عن 'templates/admin/admin_login.html'
admin_bp = Blueprint('admin', __name__, url_prefix='/admin') 

# استيراد المسارات لربطها بالمخطط
from . import routes