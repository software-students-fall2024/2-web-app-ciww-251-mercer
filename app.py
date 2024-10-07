from flask import Flask, render_template
from flask.app import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

connstr = os.getenv("DB_URI")

if connstr is None:
    raise Exception("Database URI could not be loaded. Check .env file.")

db = MongoClient(connstr)

@app.route("/")
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