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
users = {}

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

CREDENTIALS_FILE = 'user_data/user_credentials.txt'

def save_credentials(username, password):
    with open(CREDENTIALS_FILE, 'a') as file:
        file.write(f'{username},{password}\n')

def check_credentials(username, password):
    try:
        with open(CREDENTIALS_FILE, 'r') as file:
            for line in file:
                stored_username, stored_password = line.strip().split(',')
                if stored_username == username and stored_password == password:
                    return True
    except FileNotFoundError:
        return False
    return False

def load_users_from_file():
    try:
        with open(CREDENTIALS_FILE, 'r') as file:
            for line in file:
                username, password = line.strip().split(',')
                users[username] = {'password': password}
    except FileNotFoundError:
        pass

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            flash('Username already exists')
        else:
            users[username] = {'password': password}
            save_credentials(username, password)  # Save credentials to file
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if check_credentials(username, password):  # Check credentials from file
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
    
    # Check if the files actually exist in the uploads folder
    for i, other_file in enumerate(other_files):
        other_file_path = os.path.join(user_folder, f'other_file_{i}.txt')
        if not os.path.exists(other_file_path):
            other_files[i] = {'name': None, 'filename': None}
    
    return render_template('index.html', main_file=main_file, other_files=other_files)

@app.route('/paste_main', methods=['POST'])
@login_required
def paste_main():
    text = request.form['text']
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], current_user.id)
    main_file_path = os.path.join(user_folder, 'main_file.txt')
    with open(main_file_path, 'w') as f:
        f.write(text)
    session['main_file'] = 'Pasted Text'
    return redirect(url_for('index'))

@app.route('/paste_other/<int:file_index>', methods=['POST'])
@login_required
def paste_other(file_index):
    text = request.form['text']
    deck_name = request.form['deck_name']  # Get the deck name from the form
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], current_user.id)
    other_files = session.get('other_files', [{'name': None, 'filename': None}] * 20)
    other_file_path = os.path.join(user_folder, f'other_file_{file_index}.txt')
    with open(other_file_path, 'w') as f:
        f.write(text)
    other_files[file_index] = {'name': deck_name, 'filename': 'Pasted Text'}
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
            if os.path.exists(other_file_path):
                percentage = calculate_percentage(main_file_path, other_file_path)
                results.append((other_file['name'], percentage))
    
    return render_template('results.html', results=results)

def calculate_percentage(main_file_path, other_file_path):
    with open(main_file_path, 'r') as mf, open(other_file_path, 'r') as of:
        main_lines = mf.readlines()
        other_lines = of.readlines()
    
    # Strip newline characters, normalize text, and remove empty lines
    main_lines = [line.strip().lower() for line in main_lines if line.strip()]
    other_lines = [line.strip().lower() for line in other_lines if line.strip()]
    
    if not other_lines:
        return "0%"  # Avoid division by zero
    
    # Count matching lines
    matching_lines = sum(1 for line in other_lines if line in main_lines)
    
    # Calculate percentage and round to the nearest whole number
    percentage = round((matching_lines / len(other_lines)) * 100)
    return f"{percentage}%"
    
    
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        if username in users:
            users[username]['password'] = new_password
            update_credentials(username, new_password)
            flash('Password reset successful! Please log in.')
            return redirect(url_for('login'))
        else:
            flash('Username not found')
    return render_template('reset_password.html')


def update_credentials(username, new_password):
    lines = []
    with open(CREDENTIALS_FILE, 'r') as file:
        lines = file.readlines()
    
    with open(CREDENTIALS_FILE, 'w') as file:
        for line in lines:
            stored_username, stored_password = line.strip().split(',')
            if stored_username == username:
                file.write(f'{username},{new_password}\n')
            else:
                file.write(line)


if __name__ == '__main__':
    load_users_from_file()  # Load users from file before running the app
    app.run(debug=True)
