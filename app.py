from flask import Flask, redirect, url_for, render_template, request, session
from flask_pymongo import PyMongo
from bson import ObjectId
import os

# ==============================================================
# Config access to MongoDB with .env file
# ==============================================================
app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)

# ==============================================================
# Get collection questions
# ==============================================================
db_users = mongo.db.users
db_questions = mongo.db.questions
db_quiz_done = mongo.db.quiz_done
db_answers_done = mongo.db.answers_done

# ==============================================================
# HOME/LOGIN PAGE
# ==============================================================
@app.route("/", methods=["POST", "GET"])
def login():

    # Variables initialization
    error = None
    message = None

    # Click on button "Create account"
    if request.method == "POST":

        #Get vars from page
        username = request.form['username']
        password = request.form['password']

        #Check if user exists -> Open session and go to quiz
        user = db_users.find_one({'username':username,'password':password})
        if user:

            #Create session for user by username
            session['username'] = user['username']
            session['level'] = user['level']

            #Check level of this user
            if user['level'] == "admin":
                
                #Jump to page for create questions
                return redirect(url_for('questions'))

            else:

                #Jump to page Quiz
                return redirect(url_for('quiz'))

        else:
            #Return error in login page
            error = "Error: incorrect username or password"
            return render_template("login.html",error=error)

    else:
        #Simply open page
        return render_template("login.html")

# ==============================================================
# LOGOUT
# ==============================================================
@app.route("/logout")
def logout():
    session.pop('username', default=None)

    #return to login page
    return redirect(url_for('login'))

# ==============================================================
# REGISTRATION PAGE
# ==============================================================
@app.route("/registration", methods=["POST", "GET"])
def registration():

    # Variables initialization
    error = None
    message = None

    # Click on button "Create account"
    if request.method == "POST":
        
        #Get vars from page
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password2']
        level = "user"

        #Check if password1 and password2 are equals
        if password != password2:
            
            #Return error in registration page
            error = "Error: Passwords do not match"
            return render_template("registration.html",error=error)
        
        #Check if user exists -> Return Error
        user_exists = db_users.find_one({'username':username})
        if user_exists:

            #Return error in registration page
            error = "Error: this username alredy exists"
            return render_template("registration.html",error=error)
        
        else:
            #Create new record in DB
            new_user = {'username' : username, 'password' : password, 'level' : level}
            db_users.insert_one(new_user)

            #Jump to login page whit message
            message = "User created successfully, now you can log in";
            return render_template("registration.html",message=message)
    else:

        #Simply open page
        return render_template("registration.html")


# ==============================================================
# QUIZ PAGE
# ==============================================================
@app.route("/quiz", methods=["POST", "GET"])
def quiz():

    #Check if session is ok
    if session.get("username"):

        #Go to quiz page
        return render_template("quiz.html")

    else:

        #Go to login page
        return redirect(url_for('login'))

# ==============================================================
# QUESTIONS PAGE
# ==============================================================
@app.route("/questions", methods=["POST", "GET"])
def questions():

    #BLOCK IF IS ADMIN
    if session.get("level") != "admin":
        return redirect(url_for('login'))

    #GET MESSAGE AND ERRORS IF EXIST
    message = session.get('message')
    session['message'] = "";
    error = session.get('error')
    session['error'] = "";

    #Prepare fields
    fields = {}

    #Take values if is edit mode
    id_question = request.args.get('id_question')
    if(id_question):

        # Get fields from db
        query = { "_id": ObjectId(id_question) }
        result = db_questions.find_one(query)
        
        # Get fields from Database
        fields = {
            'question':result['question'],
            'answer1':result['answer1'],
            'answer2':result['answer2'],
            'answer3':result['answer3'],
            'answer4':result['answer4'],
            'correct':result['correct']
        }

    # Click on button "Save question"
    if request.method == "POST":

        #Get all fields from post
        question = request.form['question']
        answer1 = request.form['answer1']
        answer2 = request.form['answer2']
        answer3 = request.form['answer3']
        answer4 = request.form['answer4']
        correct = request.form['correct']

        #Check if all fields are filled
        if question == "" or answer1 == "" or answer2 == "" or answer3 == "" or answer4 == "" or correct == "":

            #Return page with error
            error = "Error: All fields are required"
            session['error'] = error;
            return redirect(url_for('questions'))

        else:

            #Get id question if you want to edit an existing one
            if id_question:

                #Edit question
                query = {"_id": ObjectId(id_question)}
                values = {'question' : question, 'answer1' : answer1, 'answer2' : answer2, 'answer3' : answer3, 'answer4' : answer4, 'correct' : correct}
                db_questions.update_one(query, {"$set": values})

                #Jump to login page whit message
                message = "Question edited successfully";
                session['message'] = message;

            else:

                #Adding new question
                query = {'question' : question, 'answer1' : answer1, 'answer2' : answer2, 'answer3' : answer3, 'answer4' : answer4, 'correct' : correct}
                db_questions.insert_one(query)

                #Jump to login page whit message
                message = "Question created successfully";
                session['message'] = message;

            return redirect(url_for('questions'))

    # Simply open page
    else:

        #Get all questions
        questions = list(db_questions.find())

        #Open page
        return render_template("questions.html",questions=questions,id_question=id_question,tot=len(questions),fields=fields,error=error,message=message)

# ==============================================================
# DELETE QUESTION PAGE
# ==============================================================
@app.route("/delete_question", methods=["POST", "GET"])
def delete_question():

    #BLOCK IF IS ADMIN
    if session.get("level") != "admin":
        return redirect(url_for('login'))

    #Get id question to delete record from db
    id_question = request.args['id_question']
    if id_question == "":

        #Return page with error
        error = "Error: ID not found"
        session['error'] = error;
        return redirect(url_for('questions'))

    else:

        #Delete record
        query = { "_id": ObjectId(id_question) }
        db_questions.remove(query)

        #Redirect to questions page
        return redirect(url_for('questions'))
