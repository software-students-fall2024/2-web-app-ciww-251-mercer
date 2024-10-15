from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user, logout_user
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
            {'$pull': {'tasks': {'_id': task_id}}}  # Corrected from 'id' to '_id'
        )
        if deleted.modified_count == 0:
            raise Exception("task does not exist")

    def update_task(self, task_id, updated):
        update = collection.update_one(
            {'username': self.username, 'tasks._id': str(task_id)},
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
            session['username'] = username
            login_user(user)  # Log the user in
            return redirect(url_for('list_tasks'))
        else:
            return "Invalid password"
    return "Invalid username"

@app.route('/logout')
def logout():
    print('hit')
    logout_user()
    return redirect(url_for('login'))

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route("/index")
@login_required
def index():
    return render_template('index.html')



@app.route("/add_task", methods=['GET'])
def add_task():
    return render_template("add_task.html")


@app.route("/add_task", methods=['POST'])
@login_required
def add_task_post():
    username = current_user

    title = request.form.get('title')
    description = request.form.get('description')
    due_date = request.form.get('due_date')
    completed = request.form.get('completed') == 'on'

    task_1 = TaskSchema(title=title, description=description, due_date=due_date, completed=completed)

    try:
       username.add_task(task_1)
    except Exception as exc:
        raise exc

    return redirect('/list_tasks')


@app.route("/edit_task/<task_id>", methods=['GET'])
@login_required
def edit_task(task_id):
    username = current_user
    task = None;

    for task_a in username.get_tasks():
        if str(task_a['_id']) == task_id:
            task = task_a

    return render_template("edit_task.html", task=task)

@app.route("/edit_task/<task_id>", methods=['POST'])
@login_required
def edit_task_post(task_id):
    username = current_user

    current_tasks = username.get_tasks()
    print("Current tasks:", current_tasks)

    title = request.form.get('title')
    description = request.form.get('description')
    due_date = request.form.get('due_date')
    done = request.form.get('completed') == 'on'

    task = TaskSchema(title=title, description=description, due_date=due_date, completed=done)
    task._id = ObjectId(task_id)
    print("Attempting to update task with ID:", task_id)
    try:
        username.update_task(task_id, task)
    except Exception as exc:
         raise exc

    return redirect('/list_tasks')


@app.route("/list_tasks", methods=['GET'])
@login_required
def list_tasks():
    username = current_user
    tasks = username.get_tasks()

    print("User:", username.username)
    return render_template("list_tasks.html", tasks=tasks)


@app.route("/search_task", methods=['GET'])
@login_required
def search_task():
    return render_template("search_task.html")

@app.route("/search_task", methods=['POST'])
@login_required
def search_task_post():
    searched = request.form.get('searchQuery')
    username = current_user
    tasks = username.get_tasks()

    found = [
        task for task in tasks
        if searched.lower() in task['title'].lower() or searched.lower() in task['description'].lower()
    ]

    return render_template("list_tasks.html", tasks=found)


@app.route("/delete_task/<task_id>", methods=['POST'])
@login_required
def delete_task(task_id):
    user = current_user
    try:
        user.delete_task(task_id)
    except Exception as exc:
        raise exc
    return redirect('/list_tasks')

@app.route('/static/<path:path>')
def static_path(path):
    return send_from_directory('static', path)
