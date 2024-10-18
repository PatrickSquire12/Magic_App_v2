from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'your_secret_key'

login_manager = LoginManager()

@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect(url_for('login'))

login_manager.init_app(app)

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
                if stored_username == username:
                    if stored_password == password:
                        return True
                    else:
                        return False
    except FileNotFoundError:
        return False
    return None  # Return None if username is not found


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
    # Clear existing flash messages only at the start of a new session
    if 'new_session' not in session:
        session.pop('_flashes', None)
        session['new_session'] = True

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print("username: " + username)
        print("password: " + password)
        credentials_check = check_credentials(username, password)
        print("credentials_check: " + str(credentials_check))

        if credentials_check is None:
            print("Username not recognized. Redirecting back to login.")
            flash('Username not recognized. Please try again or register.')
            return redirect(url_for('login'))
        elif credentials_check:
            user = User(username)
            login_user(user)
            session.permanent = True  # Mark session as permanent
            print(f"User {username} logged in successfully")

            # Redirect to index with username in the URL
            return redirect(url_for('index', username=username))
        else:
            print("Invalid credentials provided. Redirecting back to login.")
            flash('Invalid credentials')
            return redirect(url_for('login'))

    print("Rendering login page.")
    return render_template('login.html')
    






@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    username = request.args.get('username')  # Retrieve the username from the URL
    print("Username from URL: " + str(username))

    if not username:
        print("No username found in URL. Redirecting to login.")
        return redirect(url_for('login'))

    print("Username is valid. Continuing with index page.")
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    print("User folder path: " + user_folder)

    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
        print("Created user folder.")

    main_file = session.get('main_file', None)
    other_files = session.get('other_files', [{'name': None, 'filename': None}] * 20)

    # Check if the files actually exist in the uploads folder
    for i, other_file in enumerate(other_files):
        other_file_path = os.path.join(user_folder, f'other_file_{i}.txt')
        print(f"Checking existence of: {other_file_path}")
        if not os.path.exists(other_file_path):
            other_files[i] = {'name': None, 'filename': None}
            print(f"File {other_file_path} does not exist. Setting name and filename to None.")

    print("Rendering index page.")
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
        
        # Load users from file
        load_users_from_file()
        
        if username not in users:
            flash('Username not recognized. Please try again or register.')
            return redirect(url_for('reset_password'))
        
        # Update the password in the file
        users[username]['password'] = new_password
        with open(CREDENTIALS_FILE, 'w') as file:
            for user, data in users.items():
                file.write(f'{user},{data["password"]}\n')
        
        flash('Password reset successfully. Please log in with your new password.')
        return redirect(url_for('login'))
    
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
                
                
@app.route('/guide')
def guide():
    return render_template('guide.html')


if __name__ == '__main__':
    load_users_from_file()  # Load users from file before running the app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
