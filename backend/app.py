from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from bson.objectid import ObjectId
import os
import uuid  # Generate unique filenames for images
import pymongo.errors
from models.datasets import hunger_games_dataset

# App Configuration

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "../frontend/templates")
STATIC_DIR = os.path.join(BASE_DIR, "../frontend/static")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret")  

# Dummy data for fallback when database connection fails
dummy_books = [
    {
        "_id": ObjectId("68f127fa1e0ebbb59b464250"),
        "title": "Powerless",
        "author": "Matthew Cody",
        "year": "2011",
        "category": "Children / Middle-grade / Action & Adventure",
        "subcategory": "Supers of Noble's Green",
        "image": "eed690343b6748c69606b127c7559798_9781665954884.jpg"
    },
    {
        "_id": ObjectId("68f234d84bf88416046e55a4"),
        "title": "Angels & Demons",
        "author": "Dan Brown",
        "year": "2000",
        "category": "Fiction",
        "subcategory": "Mystery, Thriller, Conspiracy, or Religious Thriller",
        "image": "d983586416d04602b16645ccd5ef9079_AngelsAndDemons.jpg"
    },
    {
        "_id": ObjectId("68f235b34bf88416046e55a5"),
        "title": "Deception Point",
        "author": "Dan Brown",
        "year": "2001",
        "category": "Fiction",
        "subcategory": "Techno-Thriller / Political Thriller",
        "image": "6209c61a1832470a9b0d18cfc03d8d00_DeceptionPointDanBrownNovel.jpg"
    },
    {
        "_id": ObjectId("68f236364bf88416046e55a6"),
        "title": "Consent to Kill",
        "author": "Vince Flynn",
        "year": "2005",
        "category": "Fiction",
        "subcategory": "Political Thriller / Espionage",
        "image": "a2eeb7cd968046fead8f223978f8fe36_V_Flynn_Consent_to_Kill.jpg"
    },
    {
        "_id": ObjectId("68f2371b4bf88416046e55a7"),
        "title": "Sins of Empire",
        "author": "Brian McClellan",
        "year": "2017",
        "category": "Fiction",
        "subcategory": "Fantasy / Epic Fantasy",
        "image": "9187b349e1674e3b925dccced389a719_Sins_of_Empire.jpg"
    },
    {
        "_id": ObjectId("68f238804bf88416046e55a8"),
        "title": "The Da Vinci Code",
        "author": "Dan Brown",
        "year": "2003",
        "category": "Fiction",
        "subcategory": "Mystery / Thriller",
        "image": "ecdaea9114e74921a139436c40856e9f_DaVinciCode.jpg"
    },
    {
        "_id": ObjectId("68f239a64bf88416046e55aa"),
        "title": "The Kite Runner",
        "author": "Khaled Hosseini",
        "year": "2003",
        "category": "Fiction",
        "subcategory": "Drama / Historical Fiction",
        "image": "0e7ce46f58844d58a00acb69fd55994f_kite.jpg"
    },
    {
        "_id": ObjectId("68f23aa24bf88416046e55ab"),
        "title": "A Game of Thrones",
        "author": "George R. R. Martin",
        "year": "1996",
        "category": "Fiction",
        "subcategory": "Fantasy / Epic Fantasy",
        "image": "50b447c9d97a482e99e4e16f5007d636_AGameOfThrones.jpg"
    }
]

# Archived books collection data
dummy_archived_books = [
    {
        "_id": ObjectId("68f238ee4bf88416046e55a9"),
        "title": "The Hunger Games",
        "author": "Suzanne Collins",
        "year": "2008",
        "category": "Fiction",
        "subcategory": "Dystopian / Adventure",
        "image": "cb0dc430c7494baf8d5b1648784eb135_the.jpg"
    }
]

dummy_users = [
    {
        "_id": ObjectId("68efd975cad8469cf153509a"),
        "username": "mohannad_211180",
        "email": "mohannad@gmail.com",
        "role": "admin",
        "password": "scrypt:32768:8:1$zJuVqdAD5FqWySYQ$830d1aeed47a887731f22be346547abed4230a585c5c56b529753e2bf579ce8488045aa640f531755b27f7ab041e30d84d25ca014df322e0bd988ad82bbd747e"
    },
    {
        "_id": ObjectId("68f0bfe9d45e9a02d9287b7f"),
        "username": "laila",
        "email": "laila@gmail.com",
        "role": "editor",
        "password": "scrypt:32768:8:1$194YGljS9hInGtnb$faeb8826e1d7de25b2d12e4287b78d21047abfc7d1750aa46d9f10d0d6ea5a7c75a5ed0aed8f338e406b4edda988b24adb7a0ec1d9088a0ece401b44d82e4985"
    },
    {
        "_id": ObjectId("68f10bf100953281c5c37a2f"),
        "username": "ammar",
        "email": "ammar@gmail.com",
        "role": "archiver",
        "password": "scrypt:32768:8:1$AWH1mP8eLkm311jE$85a1e064d32b40f09c67aaf1d4e0de4304193b4206b04eac7f4df0bdc9a64c3a5bb56c22bc4c40301c5ab76433ab492cd01bf3a51bb429b1fce8481d05913542"
    },
    {
        "_id": ObjectId("68f29a723fbf2fe02c982b39"),
        "username": "ayham",
        "email": "ayham@gmail.com",
        "role": "archiver",
        "password": "scrypt:32768:8:1$rjBoyPNmuf5jLpkX$b103a89b24d8e7c2de319435f66a1ae81616a62b444d3b2c0be25f893361cf5dba0d44c0e65b7d35883e876e05eebb4cb600a559e48052db883d58909c191afe"
    }
]

# Database Configuration
try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    # Test the connection
    client.server_info()
    print("Connected to MongoDB successfully")
    db = client["archiving_system"]
    users_collection = db["users"]
    books_collection = db["books"]
    archived_books_collection = db["archived_books"]
except pymongo.errors.ServerSelectionTimeoutError:
    print("Warning: Could not connect to MongoDB. Using dummy data instead.")
    # Create in-memory collections using dummy data
    from pymongo.collection import Collection
    class DummyCollection:
        def __init__(self, data):
            self.data = data
            
        def find(self, query=None):
            # Simple implementation for find
            if query is None:
                return self.data
            return [item for item in self.data if all(item.get(k) == v for k, v in query.items())]
            
        def find_one(self, query):
            # Simple implementation for find_one
            results = self.find(query)
            return results[0] if results else None
            
        def insert_one(self, document):
            # Simple implementation for insert_one
            if "_id" not in document:
                document["_id"] = ObjectId()
            self.data.append(document)
            return type('obj', (object,), {'inserted_id': document["_id"]})
            
        def update_one(self, query, update):
            # Simple implementation for update_one
            for i, item in enumerate(self.data):
                if all(item.get(k) == v for k, v in query.items()):
                    if "$set" in update:
                        for k, v in update["$set"].items():
                            self.data[i][k] = v
                    break
            return type('obj', (object,), {'modified_count': 1})
            
        def delete_one(self, query):
            # Simple implementation for delete_one
            for i, item in enumerate(self.data):
                if all(item.get(k) == v for k, v in query.items()):
                    del self.data[i]
                    return type('obj', (object,), {'deleted_count': 1})
            return type('obj', (object,), {'deleted_count': 0})
    
    # Create dummy collections
    users_collection = DummyCollection(dummy_users)
    books_collection = DummyCollection(dummy_books)
    archived_books_collection = DummyCollection(dummy_archived_books)

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
