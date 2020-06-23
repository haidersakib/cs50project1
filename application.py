import os
import requests

from flask import Flask, session, render_template, request, redirect, url_for, flash, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register")
def register():
    session.clear()
    return render_template("register.html")


@app.route("/alright", methods=["POST"])
def alright():
    name = request.form.get("name")
    password = request.form.get("password")
    if not name:
        return render_template("error.html", massege="name is not given")
    elif not password:
        return render_template("error.html", massege="password is not given")
    session["names"] = name

    db.execute("INSERT INTO users(username, password) VALUES(:name, :password)",
               {"name": name, "password": password})
    db.commit()
    return render_template("alright.html", massege="you are registerd successfully", name=name)


@app.route("/login")
def login():
    session.clear()
    return render_template("login.html")


@app.route("/loged_in", methods=["POST"])
def loged_in():
    name = request.form.get("name")
    password = request.form.get("password")
    if not name:
        return render_template("error.html", massege="name is not given")
    elif not password:
        return render_template("error.html", massege="password is not given")
    session["names"] = name
    find = db.execute("SELECT * FROM users WHERE username = :name AND password = :password",
                      {"name": name, "password": password}).fetchall()
    if find is None:
        return render_template("error.html", massege="no such user")
    else:
        return render_template("logedin.html", massege="you are logged in", name=session["names"])


@app.route("/searchbooks", methods=["GET"])
def searchbooks():
    if "names" in session:
        name = session["names"]
        return render_template("searchbooks.html", name=name)
    else:
        return render_template("error.html", massege="You are not logged in.Please log in first")


@app.route("/logout")
def logout():
    session.clear()

    return redirect("/")


@app.route("/book", methods=["GET", "POST"])
def books():
    name = session["names"]
    info = request.form.get("info")

    search = db.execute("SELECT isbn, title, author, pub_year FROM books_info WHERE document_with_idx @@ "
                        "plainto_tsquery(:info) "
                        "ORDER BY ts_rank(document_with_idx, plainto_tsquery(:info))", {"info": info}).fetchall()
    if search is None:
        return render_template("error.html", massege="no such book available")
    else:
        return render_template("yes.html", search=search, name=name)


@app.route("/book/<isbn>", methods=["GET", "POST"])
def book_info(isbn):
    search = db.execute("SELECT isbn, title, author, pub_year FROM books_info WHERE isbn = :isbn",
                        {"isbn": isbn}).fetchone()
    if request.method == "POST":
        name = session["names"]
        comment = request.form.get("comment")
        rating = request.form.get("rating")
        if not comment:
            return render_template("error.html", massege="no comment found")
        if not rating:
            return render_template("error.html", massege="no rating found")
        users_id = db.execute("SELECT * FROM users WHERE username =:name", {"name": name}).fetchone()
        userid = users_id.id
        db.execute("INSERT INTO rev_users(name, comment, users_id, rating, rev_isbn)"
                   "VALUES(:name, :comment, :users_id, :rating, :rev_isbn)",
                   {"name": name, "comment": comment, "users_id": userid, "rating": rating, "rev_isbn": isbn})
        if db.execute("SELECT comment, rating FROM rev_users WHERE users_id = :id AND rev_isbn = :isbn",
                      {"id": userid, "isbn": isbn}).rowcount > 1:
            flash('you cannot give review more than once', 'warning')
            return redirect("/book/" + isbn)
        db.commit()
        flash("Review submitted")
        return redirect("/book/" + isbn)
    else:
        review = db.execute("SELECT * FROM rev_users WHERE rev_isbn = :rev_isbn",
                            {"rev_isbn": isbn}).fetchall()
        name = session["names"]
        res = requests.get("https://www.goodreads.com/book/review_counts.json",
                           params={"key": "hWIDEwS2rEKzxAgJT1w", "isbns": isbn})
        data = res.json()
        books_info = data["books"][0]

        return render_template("books.html", review=review, search=search, isbn=isbn, books_info=books_info,
                               name=name)


@app.route("/read")
def read():
    return redirect("https://www.goodreads.com")


@app.route("/api/<isbn>")
def api_books(isbn):
    isbns = db.execute("SELECT isbn FROM books_info WHERE isbn = :isbn", {"isbn": isbn})
    if isbns is None:
        return jsonify({"error": "isbn not available"}), 422

    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": "hWIDEwS2rEKzxAgJT1w", "isbns": isbn})
    data = res.json()
    books_info = data["books"][0]
    info = db.execute("SELECT * FROM books_info WHERE isbn= :isbn", {"isbn": isbn}).fetchone()
    return jsonify({
        "title": info.title,
        "author": info.author,
        "isbn": info.isbn,
        "publication_year": info.pub_year,
        "total_review": books_info["work_ratings_count"],
        "average_rating": books_info["average_rating"]
    })
