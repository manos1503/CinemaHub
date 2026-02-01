from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import re
import json
import os
import random
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Configure Flask-Session for persistent storage
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)  # Stay logged in for 1 year
Session(app)

# Path for user data file
USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')

# Load users from file
def load_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save users to file
def save_users(users):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

# Load users on startup
users = load_users()

# Load movie database from TMDb API JSON file
def load_movies_from_api():
    """Load movies from TMDb API JSON file"""
    movies_file = os.path.join(os.path.dirname(__file__), 'movies_tmdb.json')
    if os.path.exists(movies_file):
        with open(movies_file, 'r') as f:
            return json.load(f)
    return None

movies_db = load_movies_from_api()



GENRES = ['Top Rated']

def validate_email(email):
    """Check if email is valid format (something@something)"""
    return '@' in email and email.count('@') == 1 and '.' in email.split('@')[1]

def validate_password(password):
    """
    Check password requirements:
    - At least 8 characters
    - At least one capital letter
    - At least one number
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one capital letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

@app.route('/')
def home():
    """Home page - redirect to signup if not logged in"""
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('signup'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        
        # Validate email
        if not validate_email(email):
            return render_template('signup.html', error='Please enter a valid email address')
        
        # Check if email already exists
        if email in users:
            return render_template('signup.html', error='Email already registered')
        
        # Validate password
        is_valid, message = validate_password(password1)
        if not is_valid:
            return render_template('signup.html', error=message)
        
        # Check passwords match
        if password1 != password2:
            return render_template('signup.html', error='Passwords do not match')
        
        # Register user
        users[email] = password1
        save_users(users)  # Save to file
        session.permanent = True
        session['user_email'] = email
        session['signed_in'] = True
        session['logged_in'] = True
        return render_template('success.html', message='Signed in')
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user exists
        if email not in users:
            return render_template('login.html', error='Email not found. Please sign up first.')
        
        # Check password
        if users[email] != password:
            return render_template('login.html', error='Incorrect password')
        
        # Login successful
        session.permanent = True
        session['user_email'] = email
        session['logged_in'] = True
        return redirect(url_for('movie_genres'))
    
    # Check if user has signed in before
    if 'signed_in' not in session:
        return render_template('login.html', error='You must sign up first before logging in')
    
    return render_template('login.html')

@app.route('/movies')
def movie_genres():
    """Movie genre selection page - requires login"""
    if 'logged_in' not in session:
        return redirect(url_for('signup'))
    return render_template('movie_genres.html', genres=GENRES, user_email=session.get('user_email'))

@app.route('/movies/compare', methods=['POST'])
def start_comparison():
    """Start movie comparison with selected genre"""
    if 'logged_in' not in session:
        return redirect(url_for('signup'))
    
    selected_genre = request.form.get('genre')
    
    if not selected_genre or selected_genre not in movies_db:
        return redirect(url_for('movie_genres'))
    
    # Initialize tracking of shown movies and history in session
    if 'shown_movies' not in session:
        session['shown_movies'] = {}
    if 'comparison_history' not in session:
        session['comparison_history'] = {}
    
    if selected_genre not in session['shown_movies']:
        session['shown_movies'][selected_genre] = []
    if selected_genre not in session['comparison_history']:
        session['comparison_history'][selected_genre] = []
    
    # Get available movies from the genre
    available_movies = movies_db[selected_genre]
    if len(available_movies) < 2:
        return redirect(url_for('movie_genres'))
    
    # Get movies that haven't been shown yet
    shown_ids = session['shown_movies'][selected_genre]
    unshown_movies = [m for m in available_movies if m['id'] not in shown_ids]
    
    # If all movies have been shown, reset and start over
    if len(unshown_movies) < 2:
        session['shown_movies'][selected_genre] = []
        unshown_movies = available_movies
    
    # Select 2 random movies from unshown movies
    movie1, movie2 = random.sample(unshown_movies, 2)
    
    # Mark these movies as shown
    session['shown_movies'][selected_genre].append(movie1['id'])
    session['shown_movies'][selected_genre].append(movie2['id'])
    
    # Store in history for undo
    session['comparison_history'][selected_genre] = []
    session['comparison_history'][selected_genre].append({
        'movie1_id': movie1['id'],
        'movie2_id': movie2['id'],
        'kept_side': None
    })
    session.modified = True
    
    return render_template('movie_compare.html', 
                         movie1=movie1, 
                         movie2=movie2, 
                         genre=selected_genre,
                         user_email=session.get('user_email'))

@app.route('/movies/next-comparison', methods=['POST'])
def next_comparison():
    """Get next movie pair for comparison"""
    if 'logged_in' not in session:
        return redirect(url_for('signup'))
    
    genre = request.form.get('genre')
    kept_movie_id = int(request.form.get('kept_movie_id'))
    kept_side = request.form.get('kept_side', 'left')  # Track which side user selected
    
    if not genre or genre not in movies_db:
        return redirect(url_for('movie_genres'))
    
    # Initialize tracking of shown movies and history in session
    if 'shown_movies' not in session:
        session['shown_movies'] = {}
    if 'comparison_history' not in session:
        session['comparison_history'] = {}
    
    if genre not in session['shown_movies']:
        session['shown_movies'][genre] = []
    if genre not in session['comparison_history']:
        session['comparison_history'][genre] = []
    
    # Get the kept movie
    kept_movie = None
    available_movies = movies_db[genre]
    
    for movie in available_movies:
        if movie['id'] == kept_movie_id:
            kept_movie = movie
            break
    
    if not kept_movie:
        return redirect(url_for('movie_genres'))
    
    # Get movies that haven't been shown yet (excluding the kept movie)
    shown_ids = session['shown_movies'][genre]
    unshown_movies = [m for m in available_movies if m['id'] not in shown_ids and m['id'] != kept_movie_id]
    
    # If all movies have been shown, reset and start over (except kept movie)
    if len(unshown_movies) == 0:
        session['shown_movies'][genre] = [kept_movie_id]
        unshown_movies = [m for m in available_movies if m['id'] != kept_movie_id]
    
    if not unshown_movies:
        return redirect(url_for('movie_genres'))
    
    new_movie = random.choice(unshown_movies)
    
    # Mark new movie as shown
    session['shown_movies'][genre].append(new_movie['id'])
    
    # Keep the selected movie on the same side
    if kept_side == 'left':
        movie1 = kept_movie
        movie2 = new_movie
    else:
        movie1 = new_movie
        movie2 = kept_movie
    
    # Store current state in history before showing new comparison
    session['comparison_history'][genre].append({
        'movie1_id': movie1['id'],
        'movie2_id': movie2['id'],
        'kept_side': kept_side
    })
    session.modified = True
    
    return render_template('movie_compare.html',
                         movie1=movie1,
                         movie2=movie2,
                         genre=genre,
                         user_email=session.get('user_email'))

@app.route('/movies/undo', methods=['POST'])
def undo_comparison():
    """Undo the last choice and go back"""
    if 'logged_in' not in session:
        return redirect(url_for('signup'))
    
    genre = request.form.get('genre')
    
    if not genre or genre not in movies_db:
        return redirect(url_for('movie_genres'))
    
    if 'comparison_history' not in session or genre not in session['comparison_history']:
        return redirect(url_for('movie_genres'))
    
    history = session['comparison_history'][genre]
    
    # Need at least 2 entries to undo (current + previous)
    if len(history) < 2:
        return redirect(url_for('movie_genres'))
    
    # Remove the last shown movies from shown_ids
    last_state = history[-1]
    if 'shown_movies' in session and genre in session['shown_movies']:
        try:
            session['shown_movies'][genre].remove(last_state['movie1_id'])
        except ValueError:
            pass
        try:
            session['shown_movies'][genre].remove(last_state['movie2_id'])
        except ValueError:
            pass
    
    # Remove current state from history
    history.pop()
    
    # Get the previous state
    previous_state = history[-1]
    
    # Fetch the previous movies
    available_movies = movies_db[genre]
    movie1 = None
    movie2 = None
    
    for movie in available_movies:
        if movie['id'] == previous_state['movie1_id']:
            movie1 = movie
        if movie['id'] == previous_state['movie2_id']:
            movie2 = movie
    
    if not movie1 or not movie2:
        return redirect(url_for('movie_genres'))
    
    session.modified = True
    
    return render_template('movie_compare.html',
                         movie1=movie1,
                         movie2=movie2,
                         genre=genre,
                         user_email=session.get('user_email'))

@app.route('/dashboard')
def dashboard():
    if 'logged_in' in session:
        return redirect(url_for('movie_genres'))
    return redirect(url_for('signup'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('signup'))

if __name__ == '__main__':
    print("Flask app starting...")
    print("Templates folder:", app.template_folder)
    app.run(debug=True, host='127.0.0.1', port=8000)
