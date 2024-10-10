from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'your_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# In-memory user storage for demonstration purposes
users = {'user1': {'password': 'password1'}, 'user2': {'password': 'password2'}}

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            flash('Username already exists')
        else:
            users[username] = {'password': password}
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], current_user.id)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    main_file = session.get('main_file', None)
    other_files = session.get('other_files', [{'name': None, 'filename': None}] * 20)
    return render_template('index.html', main_file=main_file, other_files=other_files)

@app.route('/upload_main', methods=['POST'])
@login_required
def upload_main():
    main_file = request.files['main_file']
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], current_user.id)
    main_file_path = os.path.join(user_folder, 'main_file.txt')
    main_file.save(main_file_path)
    session['main_file'] = main_file.filename
    return redirect(url_for('index'))

@app.route('/upload_other/<int:file_index>', methods=['POST'])
@login_required
def upload_other(file_index):
    file_name = request.form['file_name']
    other_file = request.files['other_file']
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], current_user.id)
    other_files = session.get('other_files', [{'name': None, 'filename': None}] * 20)
    other_file_path = os.path.join(user_folder, f'other_file_{file_index}.txt')
    other_file.save(other_file_path)
    other_files[file_index] = {'name': file_name, 'filename': other_file.filename}
    session['other_files'] = other_files
    return redirect(url_for('index'))

@app.route('/compare')
@login_required
def compare():
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], current_user.id)
    main_file_path = os.path.join(user_folder, 'main_file.txt')
    other_files = session.get('other_files', [])
    results = []
    for i, other_file in enumerate(other_files):
        if other_file['filename']:
            other_file_path = os.path.join(user_folder, f'other_file_{i}.txt')
            percentage = calculate_percentage(main_file_path, other_file_path)
            results.append((other_file['name'], percentage))
    return render_template('results.html', results=results)

def calculate_percentage(main_file_path, other_file_path):
    with open(main_file_path, 'r') as mf, open(other_file_path, 'r') as of:
        main_lines = set(mf.readlines())
        other_lines = set(of.readlines())
        
    matching_lines = main_lines.intersection(other_lines)
    percentage = (len(matching_lines) / len(other_lines)) * 100
    return percentage

if __name__ == '__main__':
    app.run(debug=True)
