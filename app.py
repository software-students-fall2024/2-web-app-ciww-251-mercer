from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_required, login_user
from pymongo import MongoClient
from dotenv import load_dotenv
from os import getenv
from hashlib import sha256
from bson import ObjectId 

load_dotenv()

connstr = getenv("DB_URI")
key = getenv("SECRET")

if connstr is None:
    raise Exception("Database URI could not be loaded: check .env file")

if key is None:
    raise Exception("Flask secret could nto be loaded: check .env file")

app = Flask(__name__)
app.secret_key = key

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


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


class UserSchema(UserMixin):
    def __init__(self, username, password=None):
        self.username = username
        self.password_hash = self.hash_password(password) if password else ""
        self.tasks = []
        self.id = None

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
            return None

        record = UserSchema(user['username'])
        record.password_hash = user['password_hash']
        record.tasks = user['tasks']
        record.id = str(user['_id'])
        return record

    def authenticate(self):
        user = collection.find_one({'username': self.username})
        if not user:
            raise Exception("user does not exist")
        if self.password_hash != user['password_hash']:
            raise Exception("password is incorrect")
        self.id = str(user._id)

    def insert_record(self):
        user = collection.find_one({'username': self.username})
        if user is not None:
            raise Exception("username already exists")
        user = collection.insert_one(self.to_dict())

    def add_task(self, task):
        self.tasks.append(task)
        collection.update_one(
            {'username': self.username},
            {'$push': {'tasks': task.to_dict()}}
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


@login_manager.user_loader
def load_user(user_id):
    user = collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        return None
    return UserSchema.get_user(user['username'])


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    username = request.form['username']
    password = request.form['password']

    try:
        new_user = UserSchema(username, password)
        new_user.insert_record()
        return redirect(url_for('login'))
    except Exception as e:
        return str(e)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form['username']
    password = request.form['password']
    user = UserSchema.get_user(username)
    if user:
        if user.hash_password(password) == user.password_hash:
            login_user(user)  # Log the user in
            return redirect(url_for('list_tasks'))
        else:
            return "Invalid password"
    return "Invalid username"


@app.route("/")
# @login_required
def index():
    return render_template('index.html')


@app.route("/add_task", methods=['GET'])
def add_task():
    return render_template("add_task.html")


@app.route("/add_task", methods=['POST'])
def add_task_post():
    #HARDCODED USER FOR NOW
    username = 'test_user'
    user_2 = UserSchema.get_user(username)
    if user_2 is None:
        user_2 = UserSchema(username)
        user_2.insert_record()

    taskname = request.form.get('taskname')
    description = request.form.get('description')
    due_date = request.form.get('due_date')
    completed = request.form.get('completed') == 'on'

    task_1 = TaskSchema(title=taskname, description=description, due_date=due_date, completed=completed)

    user_2 = UserSchema.get_user('test_user')

    try:
        user_2.add_task(task_1)
    except Exception as exc:
        raise exc

    return redirect('/add_task')


@app.route("/edit_task")
def edit_task():
    return render_template("edit_task.html")


@app.route("/list_tasks")
@login_required
def list_tasks():
    return render_template("list_tasks.html")


@app.route("/search_task")
def search_task():
    return render_template("search_task.html")
