from flask import Flask, render_template, redirect, request, session, url_for, flash
import os
import json
import csv
from uuid import uuid4

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# --- Yordamchi funksiyalar ---

def load_users():
    path = 'data/users.json'
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open('data/users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

def load_results():
    path = 'data/results.json'
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_results(results):
    with open('data/results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

# --- Routes ---

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    if username == 'admin' and password == 'admin123':
        session['user'] = 'admin'
        return redirect('/admin')

    users = load_users()
    for user in users:
        if user['username'] == username and user['password'] == password:
            session['user'] = username
            session['test_progress'] = 0
            return redirect('/user')

    flash('Noto‘g‘ri login yoki parol!')
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('test_progress', None)
    return redirect('/')

@app.route('/admin')
def admin_panel():
    if session.get('user') != 'admin':
        return redirect('/')
    users = load_users()
    results = load_results()
    return render_template('admin_dashboard.html', users=users, results=results)

@app.route('/admin/add_user', methods=['POST'])
def add_user():
    if session.get('user') != 'admin':
        return redirect('/')

    new_user = {
        "username": request.form['username'],
        "password": request.form['password']
    }
    users = load_users()
    users.append(new_user)
    save_users(users)
    return redirect('/admin')

@app.route('/admin/delete_user/<username>')
def delete_user(username):
    if session.get('user') != 'admin':
        return redirect('/')

    users = load_users()
    users = [u for u in users if u['username'] != username]
    save_users(users)
    return redirect('/admin')

@app.route('/admin/add_question', methods=['GET', 'POST'])
def add_question():
    if session.get('user') != 'admin':
        return redirect('/')

    if request.method == 'POST':
        subject = request.form['subject']
        question = request.form['question']
        options = [
            request.form['option_a'],
            request.form['option_b'],
            request.form['option_c'],
            request.form['option_d']
        ]
        answer_index = ['A', 'B', 'C', 'D'].index(request.form['answer'])
        correct_answer = options[answer_index]

        filepath = f'subjects/{subject}.csv'
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([question] + options + [correct_answer])

        flash('Savol muvaffaqiyatli qo‘shildi!')
        return redirect('/admin/add_question')

    return render_template('admin_add_question.html')

@app.route('/admin/questions/<subject>')
def view_questions(subject):
    if session.get('user') != 'admin':
        return redirect('/')
    questions = []
    filepath = f'subjects/{subject}.csv'
    if os.path.exists(filepath):
        with open(filepath, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                questions.append({'index': i, 'question': row[0], 'options': row[1:-1], 'answer': row[-1]})
    return render_template('admin_questions.html', subject=subject, questions=questions)

@app.route('/admin/delete_question/<subject>/<int:index>')
def delete_question(subject, index):
    if session.get('user') != 'admin':
        return redirect('/')
    filepath = f'subjects/{subject}.csv'
    rows = []
    with open(filepath, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    if 0 <= index < len(rows):
        rows.pop(index)
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    return redirect(url_for('view_questions', subject=subject))

@app.route('/user')
def user_panel():
    if not session.get('user') or session.get('user') == 'admin':
        return redirect('/')
    results = load_results()
    user_results = [r for r in results if r['username'] == session['user']]
    user = {'name': session['user']}  # **Bu joy qo'shildi**
    return render_template('user_dashboard.html', results=user_results, user=user)

@app.route('/user/test/<subject>')
def take_test(subject):
    if not session.get('user') or session.get('user') == 'admin':
        return redirect('/')

    # Faqat 1 marta topshirishga tekshiruv
    results = load_results()
    for r in results:
        if r['username'] == session['user'] and r['subject'] == subject:
            flash(f"Siz bu testni allaqachon topshirgansiz: {subject}")
            return redirect('/user')

    questions = []
    filepath = f'subjects/{subject}.csv'
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            questions.append({
                'question': row[0],
                'options': row[1:-1],
                'answer': row[-1]
            })
    return render_template('test_page.html', questions=questions, subject=subject)

@app.route('/user/submit_test/<subject>', methods=['POST'])
def submit_test(subject):
    correct = 0
    total = 0
    answers = {}

    filepath = f'subjects/{subject}.csv'
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            total += 1
            qid = f'q{i}'
            user_ans = request.form.get(qid)
            if user_ans == row[-1]:
                correct += 1
            answers[row[0]] = {'your_answer': user_ans, 'correct_answer': row[-1]}

    result = {
        'id': str(uuid4()),
        'username': session['user'],
        'subject': subject,
        'score': f'{correct}/{total}',
        'answers': answers
    }

    results = load_results()
    results.append(result)
    save_results(results)

    # Keyingi fan
    fanlar = ['huquq', 'tarbiya', 'tarix']
    if 'test_progress' not in session:
        session['test_progress'] = 0
    session['test_progress'] += 1

    if session['test_progress'] < len(fanlar):
        next_subject = fanlar[session['test_progress']]
        return redirect(url_for('take_test', subject=next_subject))
    else:
        flash('Barcha testlar yakunlandi!')
        return redirect('/user')

@app.route('/admin/delete_result/<id>')
def delete_result(id):
    if session.get('user') != 'admin':
        return redirect('/')

    results = load_results()
    results = [r for r in results if r['id'] != id]
    save_results(results)
    return redirect('/admin')


if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    os.makedirs('subjects', exist_ok=True)
    for file in ['tarix.csv', 'tarbiya.csv', 'huquq.csv']:
        open(os.path.join('subjects', file), 'a', encoding='utf-8').close()
    for data_file in ['users.json', 'results.json']:
        path = os.path.join('data', data_file)
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump([], f)
    app.run(debug=True)
