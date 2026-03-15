# ShelfBuddy - Smart Pantry & Recipe Assistant

**Live Demo:** [ShelfBuddy](https://shelf-buddy-v2.onrender.com/)  
> **Note:** The app may take around 30 seconds to load on first visit due to Render free-tier cold start.

ShelfBuddy is a Flask-based web application that helps users check the shelf life of food items, manage a personal pantry, and discover recipe suggestions based on available ingredients. It is designed as a practical utility project focused on reducing food waste and improving day-to-day kitchen planning.

The application combines pantry tracking with recipe discovery by allowing users to search for an item, view its storage-based shelf life, save it to their pantry, and optionally use ingredients with a selected cuisine preference to get relevant recipe suggestions.

---

## Features

### Core Features
- **Shelf Life Checker**
  - Search for food or grocery items
  - View estimated shelf life based on storage conditions
  - Supports different storage methods such as room temperature, refrigeration, and freezing

- **Personal Pantry Management**
  - Create an account and log in
  - Save food items to a personal pantry
  - View pantry items linked to the logged-in user

- **Recipe Finder**
  - Enter an ingredient or food item to search for recipes
  - Optionally select a **cuisine type** to refine recipe results
  - Get recipe suggestions based on the entered ingredient and selected cuisine

- **Authentication System**
  - User registration and login
  - Secure password reset workflow
  - OTP-based verification for password recovery

- **Form Validation & User Feedback**
  - Flash messages for success and error handling
  - Input validation across authentication and password reset flows

- **Database-Driven Product Data**
  - Stores product names, categories, and shelf life values
  - Uses structured food data for shelf-life lookup and pantry storage

---

## Tech Stack

### Backend
- **Python**
- **Flask**

### Frontend
- **HTML**
- **CSS**
- **JavaScript**

### Database
- **SQLite**

### Deployment
- **Render**

### External Integrations
- **SMTP / Email Service** for OTP-based password reset
- **Recipe API Integration** for recipe suggestions based on ingredients and optional cuisine selection

---

## Installation & Local Setup
### 1. Clone the repository
```
git clone https://github.com/PraneethVarma5/Shelf_Buddy_V2.git
cd Shelf_Buddy_V2
```

### 2. Create and activate a virtual environment
```
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies
```
pip install -r requirements.txt
```

### 4. Populate the database
```
python populate_sqlite.py
```

### 5. Run the application
```
python app.py
```

### 6. Open in browser
```
http://127.0.0.1:5000
```
---

## Environment Variables

Create a .env file in the project root and add the following:

```env
SPOONACULAR_API_KEY=your_spoonacular_api_key
DATABASE_PATH=shelfbuddy.db
SECRET_KEY=your_secret_key_here
SENDER_EMAIL=email_you_want_send_mail_from
BREVO_API_KEY=your_brevo_api
```

