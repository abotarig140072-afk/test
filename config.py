# config.py
import os

# تحديد المسار الحالي للملف
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# تحديد اسم ومسار قاعدة البيانات
DATABASE = os.path.join(BASE_DIR, 'tests_platform.db')