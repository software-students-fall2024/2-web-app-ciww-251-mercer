from flask import Flask, render_template
from pymongo import MongoClient
from dotenv import load_dotenv
from os import getenv
from hashlib import sha256
from bson import ObjectId

load_dotenv()

app = Flask(__name__)

connstr = getenv("DB_URI")

if connstr is None:
    raise Exception("Database URI could not be loaded. Check .env file.")

db = MongoClient(connstr)
collection = db['TODO']['users']

'''
task document
{
    task_id: ObjectId
    title: string
    description: string
    due_date: time 
    completed: boolean
}
'''
class TaskSchema:
    def __init__(self, title, description=None, due_date=None, completed=False):
        self._id = ObjectId()
        self.title = title
        self.description = description
        self.due_date = due_date
        self.completed = completed

    def to_dict(self):
        return {
            '_id': str(self._id),
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date,
            'completed': self.completed
        }
'''
user document
{
    username: string unique
    password_hash: string 
    tasks: Task[]
}
'''
class UserSchema:
    def __init__(self, username, password = None):
        self.username = username
        self.password_hash = self.hash_password(password) if password else ""
        self.tasks = []

    def hash_password(self, password):
        return sha256(password.encode()).hexdigest()

    def to_dict(self):
        return {
            'username': self.username,
            'password_hash': self.password_hash,
            'tasks': self.tasks
        }
    
    @staticmethod
    def get_user(username):
        user = collection.find_one({'username': username})
        if not user:
            raise Exception("user does not exist")

        record = UserSchema(user['username'])
        record.password_hash = user['password_hash']
        record.tasks = user['tasks']
        return record

    def authenticate(self):
        user = collection.find_one({'username': self.username})
        if not user:
            raise Exception("user does not exist")
        if self.password_hash != user['password_hash']:
            raise Exception("password is incorrect")

    def insert_record(self):
        user = collection.find_one({'username': self.username})
        if user is not None:
            raise Exception("username already exists")
        
        collection.insert_one(self.to_dict())
    
    def add_task(self, task):
        self.tasks.append(task)
        collection.update_one(
            {'username': self.username},
            {'$push':{'tasks': task.to_dict()}}
        )

    def get_tasks(self):
        user = collection.find_one({'username': self.username})
        if not user:
            raise Exception("user does not exist")
        return user.get('tasks', [])

    def delete_task(self, task_id):
        deleted = collection.update_one(
            {'username': self.username},
            {'$pull': {'tasks': {'id': task_id}}}
        )
        if deleted.modified_count == 0:
            raise Exception("task does not exist")

    def update_task(self, task_id, updated):
        update = collection.update_one(
            {'username': self.username, 'tasks.id': task_id},
            {'$set': {'tasks.$': updated.to_dict()}}
        )

        if update.modified_count == 0:
            raise Exception("task does not exist")


@app.route("/")
#@login_required
def index():
    return render_template('index.html')


@app.route("/add_task", methods=['GET'])
def add_task_form():
    return render_template("add_task.html")

# @app.route('/add_task', methods=['POST'])
# def add_task():
#     taskname = request.form.get('taskname')
#     description = request.form.get('description')
#     due_date = request.form.get('due_date')
#     done = request.form.get('done') == 'on'
#
#     #print(f"Task Name: {taskname}, Description: {description}, Due Date: {due_date}, Done: {done}")
#
#     task = {
#         'title': taskname,
#         'completed': done
#     }
#
#     if description:
#         task['description'] = description
#     if due_date:
#         task['due_date'] = due_date
#
#     tasks.insert_one(task)
#
#     return redirect('/')


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
