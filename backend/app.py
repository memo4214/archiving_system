from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from bson.objectid import ObjectId
import os
import uuid  # Generate unique filenames for images

# App Configuration

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "../frontend/templates")
STATIC_DIR = os.path.join(BASE_DIR, "../frontend/static")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret")  
# Database Configuration

client = MongoClient("mongodb://localhost:27017/")
db = client["archiving_system"]
users_collection = db["users"]
books_collection = db["books"]
archived_books_collection = db["archived_books"]

# File Upload Configuration

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOADS_DIR
os.makedirs(UPLOADS_DIR, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Helpers

def role_required(allowed_roles):
    """Decorator to restrict access based on user roles."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user" not in session:
                flash("You must log in first", "error")
                return redirect(url_for("login"))
            if session.get("role") not in allowed_roles:
                flash("Access denied: insufficient permissions", "error")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

#----------------------------
# Routes

# Home route
@app.route("/")
def home():
    return redirect(url_for("login"))

#  Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = users_collection.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            session["user"] = username
            session["role"] = user.get("role", "archiver")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password", "error")
        return redirect(url_for("login"))
    
    return render_template("login.html")

#  Dashboard route
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    
    username = session["user"]
    role = session.get("role", "archiver")
    return render_template("dashboard.html", username=username, role=role)

#  Add User route (Admin)
@app.route("/add", methods=["GET", "POST"])
@role_required(["admin"])
def add_user():
    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip()
        role = request.form.get("role")
        password = request.form.get("password")

        if not (username and email and role and password):
            flash("All fields are required", "error")
            return redirect(url_for("add_user"))

        if users_collection.find_one({"username": username}):
            flash("Username already exists", "error")
            return redirect(url_for("add_user"))

        hashed_password = generate_password_hash(password)
        users_collection.insert_one({
            "username": username,
            "email": email,
            "role": role,
            "password": hashed_password
        })
        flash("User added successfully", "success")
        return redirect(url_for("dashboard"))
    
    return render_template("form.html")

# Show Users route (Admin) 
@app.route("/show")
@role_required(["admin"])
def show_users():
    users = list(users_collection.find({}, {"_id": 0}))
    return {"users": users}

# Book Management routes (Admin + Editor)

# Add Book route
@app.route("/add_book", methods=["GET", "POST"])
@role_required(["admin", "editor"])
def add_book():
    if request.method == "POST":
        title = request.form.get("title")
        author = request.form.get("author")
        year = request.form.get("year")
        category = request.form.get("category")
        subcategory = request.form.get("subcategory")
        image_file = request.files.get("image")

        if not (title and author and year and category and subcategory):
            flash("All fields are required", "error")
            return redirect(url_for("add_book"))

        book_data = {
            "title": title,
            "author": author,
            "year": year,
            "category": category,
            "subcategory": subcategory
        }

        if image_file and allowed_file(image_file.filename):
            unique_name = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            image_file.save(image_path)
            book_data["image"] = unique_name

        books_collection.insert_one(book_data)
        flash("Book added successfully", "success")
        return redirect(url_for("show_books"))

    return render_template("add_book.html")

# Show Books route
@app.route("/show_books")
@role_required(["admin", "editor", "archiver"])
def show_books():
    books = list(books_collection.find({}))
    return render_template("show_books.html", books=books, role=session.get("role"))


# Edit Book route
@app.route("/edit_book/<book_id>", methods=["GET", "POST"])
@role_required(["admin", "editor"])
def edit_book(book_id):
    book = books_collection.find_one({"_id": ObjectId(book_id)})
    if not book:
        flash("Book not found", "error")
        return redirect(url_for("show_books"))

    if request.method == "POST":
        title = request.form.get("title")
        author = request.form.get("author")
        year = request.form.get("year")
        category = request.form.get("category")
        subcategory = request.form.get("subcategory")
        image_file = request.files.get("image")

        update_data = {
            "title": title,
            "author": author,
            "year": year,
            "category": category,
            "subcategory": subcategory
        }

        if image_file and allowed_file(image_file.filename):
            unique_name = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            image_file.save(image_path)
            update_data["image"] = unique_name

        books_collection.update_one({"_id": ObjectId(book_id)}, {"$set": update_data})
        flash("Book updated successfully", "success")
        return redirect(url_for("show_books"))

    return render_template("edit_book.html", book=book)


# Delete Book route
@app.route("/delete_book/<book_id>")
@role_required(["admin", "editor"])
def delete_book(book_id):
    books_collection.delete_one({"_id": ObjectId(book_id)})
    flash("Book deleted successfully", "success")
    return redirect(url_for("show_books"))

# Archiving routes (Admin + Archiver)

# Archive Bookroute
@app.route("/archive_book/<book_id>")
@role_required(["admin", "archiver"])
def archive_book(book_id):
    book = books_collection.find_one({"_id": ObjectId(book_id)})
    if not book:
        flash("Book not found", "error")
        return redirect(url_for("show_books"))

    archived_books_collection.insert_one(book)
    books_collection.delete_one({"_id": ObjectId(book_id)})

    flash("Book archived successfully", "success")
    return redirect(url_for("archived_books"))

# Show Archived Books route
@app.route("/archived_books")
@role_required(["admin", "archiver"])
def archived_books():
    books = list(archived_books_collection.find({}))
    return render_template("archived_books.html", books=books, role=session.get("role"))


# Unarchive Book route
@app.route("/unarchive_book/<book_id>")
@role_required(["admin", "archiver"])
def unarchive_book(book_id):
    book = archived_books_collection.find_one({"_id": ObjectId(book_id)})
    if not book:
        flash("Book not found in archive", "error")
        return redirect(url_for("archived_books"))

    books_collection.insert_one(book)
    archived_books_collection.delete_one({"_id": ObjectId(book_id)})

    flash("Book unarchived successfully", "success")
    return redirect(url_for("show_books"))


@app.route("/search_books", methods=["GET"])
@role_required(["admin", "editor", "archiver", "viewer"])
def search_books():
    query = request.args.get("query", "").strip()
    filter_by = request.args.get("filter_by", "all")

    search_filter = {}
    if query:
        if filter_by == "title":
            search_filter = {"title": {"$regex": query, "$options": "i"}}
        elif filter_by == "author":
            search_filter = {"author": {"$regex": query, "$options": "i"}}
        elif filter_by == "year":
            search_filter = {"year": {"$regex": query, "$options": "i"}}
        elif filter_by == "category":
            search_filter = {"category": {"$regex": query, "$options": "i"}}
        elif filter_by == "subcategory":
            search_filter = {"subcategory": {"$regex": query, "$options": "i"}}
        else:  # all
            search_filter = {
                "$or": [
                    {"title": {"$regex": query, "$options": "i"}},
                    {"author": {"$regex": query, "$options": "i"}},
                    {"year": {"$regex": query, "$options": "i"}},
                    {"category": {"$regex": query, "$options": "i"}},
                    {"subcategory": {"$regex": query, "$options": "i"}},
                ]
            }

    books = list(books_collection.find(search_filter))
    return render_template("show_books.html", books=books, role=session.get("role"))


# Logout route

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("role", None)
    return redirect(url_for("login"))

# Run Application
if __name__ == '__main__':
    app.run(debug=True)
