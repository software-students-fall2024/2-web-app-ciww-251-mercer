from flask import Flask, render_template
from pymongo import MongoClient
from dotenv import load_dotenv
from os import getenv
from hashlib import sha256

load_dotenv()

app = Flask(__name__)

connstr = getenv("DB_URI")

if connstr is None:
    raise Exception("Database URI could not be loaded. Check .env file.")

db = MongoClient(connstr)

class TaskSchema:
    def __init__(self, title, description=None, due_date=None, completed=False):
        self.title = title
        self.description = description
        self.due_date = due_date
        self.completed = completed

    def to_dict(self):
        return {
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date,
            'completed': self.completed
        }


class UserSchema:
    def __init__(self, username, password):
        self.username = username
        self.password_hash = self.hash_password(password)

    def hash_password(self, password):
        return sha256(password.encode()).hexdigest()

    def to_dict(self):
        return {
            'username': self.username,
            'password_hash': self.password_hash
        }


@app.route("/")
#@login_required
def index():
    return render_template('index.html')


@app.route("/add_task")
def add_task():
    return render_template("add_task.html")

# @app.route("/edit_task")
# def edit_task():
#     return render_template("edit_task.html")
#
# @app.route("/list_tasks")
# def list_tasks():
#     return render_template("list_tasks.html")
#
# @app.route("/search_task")
# def search_task():
#     return render_template("search_task.html")
