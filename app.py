# -*- coding: utf-8 -*-
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, Blueprint
)
import sqlite3
import os
import hashlib
import datetime
from datetime import datetime as dt # For template 'now' function
import click
from flask.cli import with_appcontext
from config import DATABASE

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_random_key_change_this'


# --- 1. Admin Blueprint Definition ---
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
def require_admin_login():
    """Ensures user is logged in and is the admin."""
    if 'user_id' not in session:
        flash('الرجاء تسجيل الدخول للوصول لهذه الصفحة.', 'warning')
        return redirect(url_for('login'))
    if session.get('username') != 'admin':
        flash('ليس لديك الصلاحيات الكافية.', 'danger')
        return redirect(url_for('dashboard')) # Redirect non-admins away

@admin_bp.route('/')
def index():
    """Redirects base admin URL to manage tests page."""
    return redirect(url_for('admin.manage_tests'))

@admin_bp.route('/manage-tests', methods=['GET', 'POST'])
def manage_tests():
    """Handles adding new tests and displaying existing ones."""
    conn = None
    if request.method == 'POST': # Add new test
        test_name = request.form.get('test_name')
        test_type = request.form.get('test_type')
        test_level = request.form.get('test_level')

        if not test_name or not test_type or not test_level:
            flash('الرجاء ملء جميع الحقول.', 'danger')
            return redirect(url_for('admin.manage_tests'))

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tests (name, type, level) VALUES (?, ?, ?)",
                (test_name, test_type, int(test_level))
            )
            conn.commit()
            flash(f'تمت إضافة الاختبار "{test_name}" بنجاح.', 'success')
        except sqlite3.Error as e:
            flash(f'حدث خطأ أثناء إضافة الاختبار: {e}', 'danger')
        except ValueError:
            flash('المرحلة يجب أن تكون رقماً.', 'danger')
        finally:
            if conn:
                conn.close()
        return redirect(url_for('admin.manage_tests'))

    # (GET) Display existing tests
    current_tests = []
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type, level FROM tests ORDER BY id ASC")
        current_tests = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f'حدث خطأ أثناء جلب الاختبارات: {e}', 'danger')
    finally:
        if conn:
            conn.close()

    return render_template('admin/manage_tests.html', current_tests=current_tests)

@admin_bp.route('/manage-questions/<int:test_id>', methods=['GET', 'POST'])
def manage_questions(test_id):
    """Handles adding new questions and displaying questions for a specific test."""
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST': # Add new question
        question_text = request.form.get('question_text')
        option1 = request.form.get('option1')
        option2 = request.form.get('option2')
        option3 = request.form.get('option3')
        option4 = request.form.get('option4')
        correct_option = request.form.get('correct_option')

        if not all([question_text, option1, option2, option3, option4, correct_option]):
            flash('الرجاء ملء جميع حقول السؤال.', 'danger')
        elif correct_option not in [option1, option2, option3, option4]:
             flash('الإجابة الصحيحة يجب أن تكون مطابقة تماماً لأحد الخيارات الأربعة.', 'warning')
        else:
            try:
                cursor.execute("""
                    INSERT INTO questions (test_id, text, option1, option2, option3, option4, correct_option)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (test_id, question_text, option1, option2, option3, option4, correct_option))
                conn.commit()
                flash('تمت إضافة السؤال بنجاح.', 'success')
            except sqlite3.Error as e:
                flash(f'حدث خطأ أثناء إضافة السؤال: {e}', 'danger')

        conn.close()
        return redirect(url_for('admin.manage_questions', test_id=test_id))

    # (GET) Display test info and questions
    cursor.execute("SELECT name FROM tests WHERE id = ?", (test_id,))
    test = cursor.fetchone()
    if not test:
        flash('الاختبار غير موجود.', 'danger')
        conn.close()
        return redirect(url_for('admin.manage_tests'))

    cursor.execute("SELECT id, text, correct_option FROM questions WHERE test_id = ? ORDER BY id ASC", (test_id,))
    questions = cursor.fetchall()

    conn.close()
    return render_template('admin/manage_questions.html', test=test, questions=questions, test_id=test_id)


@admin_bp.route('/delete-question/<int:question_id>/<int:test_id>')
def delete_question(question_id, test_id):
    """Deletes a specific question."""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        conn.commit()
        flash('تم حذف السؤال بنجاح.', 'success')
    except sqlite3.Error as e:
        flash(f'حدث خطأ أثناء حذف السؤال: {e}', 'danger')
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin.manage_questions', test_id=test_id))


@admin_bp.route('/manage-users')
def manage_users():
    """Displays all non-admin users."""
    conn = None
    users = []
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email FROM users WHERE username != 'admin' ORDER BY id")
        users = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f'خطأ في جلب المستخدمين: {e}', 'danger')
    finally:
        if conn:
            conn.close()

    return render_template('admin/manage_users.html', users=users)

@admin_bp.route('/delete-user/<int:user_id>')
def delete_user(user_id):
    """Deletes a user and their associated results (due to ON DELETE CASCADE)."""
    conn = None
    try:
        conn = get_db() # Includes PRAGMA foreign_keys = ON
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        flash(f'تم حذف المستخدم (ID: {user_id}) وجميع نتائجه بنجاح.', 'success')
    except sqlite3.Error as e:
        flash(f'حدث خطأ أثناء حذف المستخدم: {e}', 'danger')
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin.manage_users'))

# --- NEW: Route to delete a test ---
@admin_bp.route('/delete-test/<int:test_id>')
def delete_test(test_id):
    """Deletes a test and its associated questions/results (due to ON DELETE CASCADE)."""
    conn = None
    try:
        conn = get_db() # Includes PRAGMA foreign_keys = ON
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tests WHERE id = ?", (test_id,))
        conn.commit()
        flash(f'تم حذف الاختبار (ID: {test_id}) وجميع أسئلته ونتائجه بنجاح.', 'success')
    except sqlite3.Error as e:
        flash(f'حدث خطأ أثناء حذف الاختبار: {e}.', 'danger')
        print(f"Error deleting test {test_id}: {e}") # Log error for debugging
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin.manage_tests'))
# --- End NEW ---


# --- Register Admin Blueprint ---
app.register_blueprint(admin_bp)

# --- Make 'now' available to templates ---
@app.context_processor
def inject_now():
    return {'now': dt.utcnow}

# --- Define datetime format filter ---
def format_datetime_filter(value, format='%Y-%m-%d %H:%M'):
    """Format a datetime object or string for display."""
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = dt.strptime(value, '%Y-%m-%d %H:%M:%S.%f') # Most common SQLite format
        except ValueError:
            try:
                value = dt.strptime(value, '%Y-%m-%d %H:%M:%S') # Without microseconds
            except ValueError:
                 try:
                      value = dt.strptime(value, '%Y-%m-%d %H:%M') # Format used in submit_test
                 except ValueError:
                    return value # Return original string if parsing fails
    if isinstance(value, datetime.datetime):
         return value.strftime(format)
    return value


# --- Register filter with Jinja ---
app.jinja_env.filters['format_datetime'] = format_datetime_filter


# --- 2. Database Helper Functions ---
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON") # Enable foreign key support for cascade delete
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    """Initializes the database schema and adds initial data."""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Enable foreign key support (redundant here but good practice)
        cursor.execute("PRAGMA foreign_keys = ON")

        # Create tables with ON DELETE CASCADE where appropriate
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('قياس', 'تحصيلي')),
            level INTEGER NOT NULL DEFAULT 1
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            option1 TEXT NOT NULL,
            option2 TEXT NOT NULL,
            option3 TEXT NOT NULL,
            option4 TEXT NOT NULL,
            correct_option TEXT NOT NULL,
            FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            test_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            percentage INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE
        )
        ''')

        conn.commit()
        print("Database tables created or already exist.")

        # Add initial data only if tests table is empty
        cursor.execute("SELECT COUNT(*) FROM tests")
        if cursor.fetchone()[0] == 0:
            print("Adding initial test data...")
            # Add Qiyas tests and questions
            cursor.execute("INSERT INTO tests (name, type, level) VALUES (?, ?, ?)",
                           ("اختبار قدرات تجريبي (كمي) - المرحلة 1", "قياس", 1))
            test1_id = cursor.lastrowid
            questions1 = [
                (test1_id, "إذا كان س + 5 = 12، فما قيمة س؟", "5", "6", "7", "8", "7"),
                (test1_id, "ما هو ناتج 3 × (4 + 6)؟", "18", "22", "30", "42", "30"),
                (test1_id, "دائرة نصف قطرها 5 سم، ما محيطها؟ (ط ≈ 3.14)", "15.7 سم", "25 سم", "31.4 سم", "50 سم", "31.4 سم"),
            ]
            cursor.executemany("INSERT INTO questions (test_id, text, option1, option2, option3, option4, correct_option) VALUES (?, ?, ?, ?, ?, ?, ?)", questions1)

            cursor.execute("INSERT INTO tests (name, type, level) VALUES (?, ?, ?)",
                           ("اختبار قدرات تجريبي (كمي) - المرحلة 2", "قياس", 2))

            # Add Tahseli tests and questions
            cursor.execute("INSERT INTO tests (name, type, level) VALUES (?, ?, ?)",
                           ("اختبار تحصيلي تجريبي (أحياء) - المرحلة 1", "تحصيلي", 1))
            test2_id = cursor.lastrowid
            questions2 = [
                (test2_id, "ما هي الوحدة الأساسية للحياة؟", "النسيج", "العضو", "الخلية", "الجهاز", "الخلية"),
                (test2_id, "أي جزء من الخلية النباتية مسؤول عن عملية البناء الضوئي؟", "الميتوكوندريا", "النواة", "الجدار الخلوي", "البلاستيدات الخضراء", "البلاستيدات الخضراء"),
            ]
            cursor.executemany("INSERT INTO questions (test_id, text, option1, option2, option3, option4, correct_option) VALUES (?, ?, ?, ?, ?, ?, ?)", questions2)

            cursor.execute("INSERT INTO tests (name, type, level) VALUES (?, ?, ?)",
                           ("اختبار تحصيلي تجريبي (أحياء) - المرحلة 2", "تحصيلي", 2))

            conn.commit()
            print("Initial data added.")

    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
    finally:
        if conn:
            conn.close()

# --- 3. Database Initialization Command ---
@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clears existing data and creates new tables."""
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
        print("Removed old database.")
    init_db()
    click.echo('Initialized the database.')

app.cli.add_command(init_db_command)


# --- 4. Main Application Routes ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard')) if session.get('username') != 'admin' else redirect(url_for('admin.index'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
         return redirect(url_for('dashboard')) if session.get('username') != 'admin' else redirect(url_for('admin.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not email or not password or not confirm_password:
            flash('الرجاء ملء جميع الحقول.', 'danger')
            return redirect(url_for('register'))
        if password != confirm_password:
            flash('كلمتا المرور غير متطابقتين.', 'danger')
            return redirect(url_for('register'))

        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
            existing_user = cursor.fetchone()
            if existing_user:
                flash('اسم المستخدم أو البريد الإلكتروني موجود مسبقاً.', 'warning')
                return redirect(url_for('register'))

            hashed_password = hash_password(password)
            cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                           (username, email, hashed_password))
            conn.commit()
            flash('تم التسجيل بنجاح! يمكنك الآن تسجيل الدخول.', 'success')
            return redirect(url_for('login'))
        except sqlite3.Error as e:
            print(f"Database error during registration: {e}")
            flash('حدث خطأ أثناء التسجيل. الرجاء المحاولة مرة أخرى.', 'danger')
            return redirect(url_for('register'))
        finally:
            if conn:
                conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
         return redirect(url_for('dashboard')) if session.get('username') != 'admin' else redirect(url_for('admin.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('الرجاء إدخال اسم المستخدم وكلمة المرور.', 'danger')
            return redirect(url_for('login'))

        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user and user['password_hash'] == hash_password(password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash(f'أهلاً بك مجدداً، {user["username"]}!', 'success')
                return redirect(url_for('admin.index')) if user['username'] == 'admin' else redirect(url_for('dashboard'))
            else:
                flash('اسم المستخدم أو كلمة المرور غير صحيحة.', 'danger')
                return redirect(url_for('login'))
        except sqlite3.Error as e:
            print(f"Database error during login: {e}")
            flash('حدث خطأ أثناء تسجيل الدخول.', 'danger')
            return redirect(url_for('login'))
        finally:
            if conn:
                conn.close()
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('الرجاء تسجيل الدخول أولاً للوصول لهذه الصفحة.', 'warning')
        return redirect(url_for('login'))
    if session.get('username') == 'admin':
        flash('يتم توجيهك للوحة تحكم المدير.', 'info')
        return redirect(url_for('admin.index'))

    username = session.get('username', 'زائر')
    user_id = session.get('user_id')
    available_tests_qiyas = {}
    available_tests_tahseli = {}
    past_results = []
    conn = None

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.type, MAX(t.level) as max_level
            FROM test_results tr JOIN tests t ON tr.test_id = t.id
            WHERE tr.user_id = ? GROUP BY t.type
        """, (user_id,))
        completed_progress = cursor.fetchall()
        max_completed_qiyas = 0
        max_completed_tahseli = 0
        for row in completed_progress:
            if row['type'] == 'قياس': max_completed_qiyas = row['max_level']
            elif row['type'] == 'تحصيلي': max_completed_tahseli = row['max_level']

        next_qiyas_level = max_completed_qiyas + 1
        cursor.execute("SELECT id, name, level FROM tests WHERE type = 'قياس' AND (level = 1 OR level = ?) ORDER BY level, name", (next_qiyas_level,))
        for test in cursor.fetchall():
            level = test['level']
            if level not in available_tests_qiyas: available_tests_qiyas[level] = []
            available_tests_qiyas[level].append(dict(test))

        next_tahseli_level = max_completed_tahseli + 1
        cursor.execute("SELECT id, name, level FROM tests WHERE type = 'تحصيلي' AND (level = 1 OR level = ?) ORDER BY level, name", (next_tahseli_level,))
        for test in cursor.fetchall():
            level = test['level']
            if level not in available_tests_tahseli: available_tests_tahseli[level] = []
            available_tests_tahseli[level].append(dict(test))

        cursor.execute("""
            SELECT tr.score, tr.total_questions, tr.percentage, tr.timestamp, t.name as test_name
            FROM test_results tr JOIN tests t ON tr.test_id = t.id
            WHERE tr.user_id = ? ORDER BY tr.timestamp DESC
        """, (user_id,))
        past_results = cursor.fetchall()
        print(f"Found {len(past_results)} past results for user {user_id}")
    except sqlite3.Error as e:
        print(f"Database error loading data for dashboard: {e}")
        flash('حدث خطأ أثناء تحميل بيانات لوحة التحكم.', 'danger')
    finally:
        if conn: conn.close()

    return render_template('dashboard.html',
                           username=username,
                           tests_qiyas_by_level=available_tests_qiyas,
                           tests_tahseli_by_level=available_tests_tahseli,
                           past_results=past_results)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('تم تسجيل الخروج بنجاح.', 'info')
    return redirect(url_for('index'))

@app.route('/test/<int:test_id>')
def take_test(test_id):
    if 'user_id' not in session:
        flash('الرجاء تسجيل الدخول أولاً لبدء الاختبار.', 'warning')
        return redirect(url_for('login'))
    if session.get('username') == 'admin':
         flash('لا يمكن للمدير أداء الاختبارات.', 'warning')
         return redirect(url_for('admin.index'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM tests WHERE id = ?", (test_id,))
        test_info = cursor.fetchone()
        if not test_info:
            flash('الاختبار غير موجود.', 'danger')
            return redirect(url_for('dashboard'))

        cursor.execute("SELECT id, text, option1, option2, option3, option4 FROM questions WHERE test_id = ?", (test_id,))
        questions = cursor.fetchall()
        if not questions:
            flash('لا توجد أسئلة لهذا الاختبار حالياً.', 'warning')
            return redirect(url_for('dashboard'))

        questions_list = [dict(q) for q in questions]
        for q in questions_list:
            q['options'] = [q['option1'], q['option2'], q['option3'], q['option4']]
        test_data = {'id': test_info['id'], 'title': test_info['name'], 'questions': questions_list}
        return render_template('test.html', test=test_data)
    except sqlite3.Error as e:
        print(f"Database error loading test {test_id}: {e}")
        flash('حدث خطأ أثناء تحميل الاختبار.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn: conn.close()

@app.route('/submit/<int:test_id>', methods=['POST'])
def submit_test(test_id):
    if 'user_id' not in session:
        flash('انتهت جلستك، الرجاء تسجيل الدخول مرة أخرى.', 'warning')
        return redirect(url_for('login'))
    if session.get('username') == 'admin':
         flash('لا يمكن للمدير إرسال نتائج الاختبارات.', 'warning')
         return redirect(url_for('admin.index'))

    user_id = session.get('user_id')
    conn = None

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM tests WHERE id = ?", (test_id,))
        test_info = cursor.fetchone()
        if not test_info:
            flash('الاختبار غير صالح.', 'danger')
            return redirect(url_for('dashboard'))

        cursor.execute("SELECT id, text, correct_option FROM questions WHERE test_id = ?", (test_id,))
        questions_from_db = cursor.fetchall()
        if not questions_from_db:
             flash('لا يمكن تصحيح الاختبار لعدم وجود أسئلة.', 'danger')
             return redirect(url_for('dashboard'))

        score = 0
        total_questions = len(questions_from_db)
        results_details = []
        for question in questions_from_db:
            question_id = question['id']
            submitted_answer = request.form.get(f'question_{question_id}')
            correct_answer = question['correct_option']
            is_correct = (submitted_answer == correct_answer)
            if is_correct: score += 1
            results_details.append({
                'question_text': question['text'],
                'submitted_answer': submitted_answer if submitted_answer else "لم تتم الإجابة",
                'correct_answer': correct_answer,
                'is_correct': is_correct
            })

        percentage = round((score / total_questions) * 100) if total_questions > 0 else 0
        try:
            current_time = dt.now() # Using dt alias
            cursor.execute("""
                INSERT INTO test_results (user_id, test_id, score, total_questions, percentage, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, test_id, score, total_questions, percentage, current_time))
            conn.commit()
            print(f"Result saved for user {user_id} on test {test_id}")
        except sqlite3.Error as e:
            print(f"Error saving test result: {e}")

        next_test_id = None
        try:
            cursor.execute("SELECT type, level FROM tests WHERE id = ?", (test_id,))
            current_test_info = cursor.fetchone()
            if current_test_info:
                current_type = current_test_info['type']
                current_level = current_test_info['level']
                next_level = current_level + 1
                cursor.execute("SELECT id FROM tests WHERE type = ? AND level = ? ORDER BY id LIMIT 1", (current_type, next_level))
                next_test = cursor.fetchone()
                if next_test:
                    next_test_id = next_test['id']
                    print(f"Next test found for type {current_type}, level {next_level}: ID {next_test_id}")
        except sqlite3.Error as e:
            print(f"Error finding next test: {e}")

        return render_template('results.html',
                               score=score, total_questions=total_questions, percentage=percentage,
                               test_title=test_info['name'], results_details=results_details,
                               next_test_id=next_test_id)
    except sqlite3.Error as e:
        print(f"Database error submitting test {test_id}: {e}")
        flash('حدث خطأ أثناء تصحيح الاختبار.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn: conn.close()


# --- 5. Run Application ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)