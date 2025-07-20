from flask import Flask, render_template, request, redirect, session, send_file, url_for
import sqlite3
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import csv

app = Flask(__name__)
app.secret_key = 'secret_key'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE,
        name TEXT,
        class TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT UNIQUE)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        subject_id INTEGER,
        marks INTEGER,
        FOREIGN KEY(student_id) REFERENCES students(student_id),
        FOREIGN KEY(subject_id) REFERENCES subjects(id))''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username=? AND password=?',
                            (username, password)).fetchone()
        conn.close()
        if user:
            session['user'] = username
            return redirect('/dashboard')
        else:
            return render_template('login.html', error='Invalid Credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                         (username, password))
            conn.commit()
            conn.close()
            return redirect('/login')
        except:
            return render_template('register.html', error='Username already exists')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    conn = get_db_connection()
    students = conn.execute('''
        SELECT DISTINCT students.student_id, students.name, students.class
        FROM students
        JOIN marks ON students.student_id = marks.student_id
    ''').fetchall()
    subjects = conn.execute('SELECT * FROM subjects').fetchall()
    conn.close()
    return render_template('dashboard.html', students=students, subjects=subjects)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if 'user' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        student_id = request.form['student_id'].strip()
        name = request.form['name'].strip()
        class_ = request.form['class'].strip()

        conn = get_db_connection()
        existing = conn.execute('SELECT * FROM students WHERE student_id = ?', (student_id,)).fetchone()
        if existing:
            conn.close()
            return render_template('add_student.html', error='Student ID already exists!')

        conn.execute('INSERT INTO students (student_id, name, class) VALUES (?, ?, ?)',
                     (student_id, name, class_))
        conn.commit()
        conn.close()
        return redirect('/dashboard')
    
    return render_template('add_student.html')

@app.route('/add_subject', methods=['GET', 'POST'])
def add_subject():
    if 'user' not in session:
        return redirect('/login')
    if request.method == 'POST':
        subject_name = request.form['subject_name'].strip().upper()
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO subjects (subject_name) VALUES (?)',
                         (subject_name,))
            conn.commit()
        except sqlite3.IntegrityError:
            return render_template('add_subject.html', error="Subject already exists!")
        finally:
            conn.close()
        return redirect('/dashboard')
    return render_template('add_subject.html')

@app.route('/enter_marks', methods=['GET', 'POST'])
def enter_marks():
    if 'user' not in session:
        return redirect('/login')
    conn = get_db_connection()
    students = conn.execute('SELECT student_id, name FROM students').fetchall()
    subjects = conn.execute('SELECT id, subject_name FROM subjects').fetchall()
    if request.method == 'POST':
        student_id = request.form['student_id']
        subject_id = request.form['subject_id']
        marks = request.form['marks']
        conn.execute('INSERT INTO marks (student_id, subject_id, marks) VALUES (?, ?, ?)',
                     (student_id, subject_id, marks))
        conn.commit()
        conn.close()
        return redirect('/dashboard')
    return render_template('enter_marks.html', students=students, subjects=subjects)

@app.route('/view_records')
def view_records():
    if 'user' not in session:
        return redirect('/login')
    conn = get_db_connection()
    records = conn.execute('''
        SELECT marks.id, students.name, students.class, subjects.subject_name, marks.marks
        FROM marks
        JOIN students ON marks.student_id = students.student_id
        JOIN subjects ON marks.subject_id = subjects.id
    ''').fetchall()
    conn.close()
    return render_template('view_records.html', records=records)

@app.route('/edit_mark/<int:id>', methods=['GET', 'POST'])
def edit_mark(id):
    if 'user' not in session:
        return redirect('/login')
    conn = get_db_connection()
    if request.method == 'POST':
        new_marks = request.form['marks']
        conn.execute('UPDATE marks SET marks = ? WHERE id = ?', (new_marks, id))
        conn.commit()
        conn.close()
        return redirect('/view_records')
    
    record = conn.execute('''
        SELECT marks.id, students.name, students.class, subjects.subject_name, marks.marks
        FROM marks
        JOIN students ON marks.student_id = students.student_id
        JOIN subjects ON marks.subject_id = subjects.id
        WHERE marks.id = ?
    ''', (id,)).fetchone()
    conn.close()
    return render_template('edit_mark.html', record=record)

@app.route('/delete_mark/<int:id>')
def delete_mark(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_db_connection()
    result = conn.execute('SELECT subject_id, student_id FROM marks WHERE id = ?', (id,)).fetchone()
    if not result:
        conn.close()
        return redirect('/view_records')

    subject_id = result['subject_id']
    student_id = result['student_id']

    conn.execute('DELETE FROM marks WHERE id = ?', (id,))
    conn.commit()

    subject_count = conn.execute('SELECT COUNT(*) as cnt FROM marks WHERE subject_id = ?', (subject_id,)).fetchone()
    if subject_count['cnt'] == 0:
        conn.execute('DELETE FROM subjects WHERE id = ?', (subject_id,))
        conn.commit()

    student_count = conn.execute('SELECT COUNT(*) as cnt FROM marks WHERE student_id = ?', (student_id,)).fetchone()
    if student_count['cnt'] == 0:
        conn.execute('DELETE FROM students WHERE student_id = ?', (student_id,))
        conn.commit()

    conn.close()
    return redirect('/view_records')

@app.route('/delete_subject/<int:id>')
def delete_subject(id):
    if 'user' not in session:
        return redirect('/login')

    conn = get_db_connection()
    usage = conn.execute('SELECT COUNT(*) as cnt FROM marks WHERE subject_id = ?', (id,)).fetchone()

    if usage['cnt'] == 0:
        conn.execute('DELETE FROM subjects WHERE id = ?', (id,))
        conn.commit()
    
    conn.close()
    return redirect('/dashboard')

@app.route('/visualize')
def visualize():
    if 'user' not in session:
        return redirect('/login')
    conn = get_db_connection()
    data = conn.execute('''
        SELECT students.name, AVG(marks.marks) as avg_marks
        FROM marks
        JOIN students ON marks.student_id = students.student_id
        GROUP BY students.student_id
    ''').fetchall()
    conn.close()
    names = [row['name'] for row in data]
    averages = [row['avg_marks'] for row in data]
    plt.figure(figsize=(10, 5))
    plt.bar(names, averages, color='blue')
    plt.xlabel('Student Name')
    plt.ylabel('Average Marks')
    plt.title('Average Marks Per Student')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/export')
def export():
    if 'user' not in session:
        return redirect('/login')
    conn = get_db_connection()
    data = conn.execute('''
        SELECT students.student_id, students.name, students.class,
               subjects.subject_name, marks.marks
        FROM marks
        JOIN students ON marks.student_id = students.student_id
        JOIN subjects ON marks.subject_id = subjects.id
    ''').fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID', 'Name', 'Class', 'Subject', 'Marks'])
    for row in data:
        writer.writerow([row['student_id'], row['name'], row['class'],
                         row['subject_name'], row['marks']])
    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='marks.csv')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

if __name__ == '__main__':
    if not os.path.exists('database.db'):
        init_db()
    app.run(debug=True)
