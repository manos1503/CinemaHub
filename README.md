# Login Website

A web application with sign-up and login functionality with the following features:

## Requirements

### Sign Up
- Email must be in @mail domain
- Password must have:
  - Minimum 8 characters
  - At least one capital letter
  - At least one number
- Password must be entered twice to verify they match
- Upon successful signup, displays "Signed in"

### Login
- Must already have signed up to login
- Upon successful login, displays "Logged in"
- Credentials must match registered account

## Setup

1. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python app.py
   ```

3. Open your browser and go to:
   ```
   http://localhost:5000
   ```

## Features

- Client-side and server-side validation
- Real-time password requirement checking
- Session management
- User-friendly interface
- Error handling with helpful messages
