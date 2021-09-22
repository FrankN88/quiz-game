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
            session['id_user'] = str(user['_id'])
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
    session.clear()

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

    #If not exist quiz session -> create new one
    if session.get("id_quiz") is None:

        #Create new quiz session in db and get the id
        query = {'id_user' : session.get("id_user"), 'total_corrects' : 0}
        id_quiz = str(db_quiz_done.insert_one(query).inserted_id)

        #Create session for actual quiz starting from the first question
        session['id_quiz'] = id_quiz
        session['quiz_question'] = 0

        #Go to quiz page
        return redirect(url_for('quiz'))

    else:

        #Get all questions
        questions = list(db_questions.find())

        #Check if number of actual question is smoller than total questions
        if session.get('quiz_question') >= len(questions):

            #Go directli to results page
            return redirect(url_for("results"))

        #Get the actual question number
        question = questions[session.get('quiz_question')]

        #Check if there is an answer
        answer = request.args.get('ans')
        if(answer):

            #save choice in db
            query = { 'id_quiz_done' : session['id_quiz'], 'id_question' : str(question['_id']), 'answer_number' : answer }
            db_answers_done.insert_one(query)

            #check if the answer is correct
            if question['correct'] == answer:

                #get info from db of this quiz session
                query = {"_id": ObjectId(session['id_quiz'])}
                quiz = db_quiz_done.find_one(query)

                #increment correct from total
                values = {'total_corrects' : quiz['total_corrects']+1}
                db_quiz_done.update_one(query, {"$set": values})

                #answer is correct
                return render_template("quiz.html",question = question, tot_question = len(questions), answer = answer, response = 'correct')

            else:

                #anser is wrong
                return render_template("quiz.html",question = question, tot_question = len(questions), answer = answer, response = 'wrong')
        

        #Go to the next question
        next_question = request.args.get('next')
        if(next_question):

            #go to the next one
            session['quiz_question'] = session.get("quiz_question")+1

            #check if you have another question
            if session['quiz_question'] >= len(questions):

                #show the result page
                return redirect(url_for("results"))
            
            else:
                
                #go to the next question
                return redirect(url_for('quiz'))

        else:

            #Go to login page
            return render_template("quiz.html",question = question, tot_question = len(questions))

# ==============================================================
# RESULT PAGE
# ==============================================================
@app.route("/results", methods=["POST", "GET"])
def results():

    #Get id quiz from session
    id_quiz_done = session['id_quiz']

    #If quiz session not exists -> start new quiz
    if id_quiz_done is None:
        return redirect(url_for('quiz'))

    #get info from db of this quiz session
    questions = list(db_questions.find())
    tot_corrects = db_quiz_done.find_one({"_id": ObjectId(id_quiz_done)})['total_corrects']

    #print results
    results = []
    for question in questions:
        query = {"id_quiz_done": id_quiz_done, "id_question" : str(question['_id'])}
        answer_done = db_answers_done.find_one(query)

        obj = {
            "question" : question['question'],
            "answer1" : question['answer1'],
            "answer2" : question['answer2'],
            "answer3" : question['answer3'],
            "answer4" : question['answer4'],
            "correct" : question['correct'],
            "answer_done" : answer_done['answer_number']
        }
        
        results.append(obj)

    #Show results of quiz
    return render_template("results.html",results=results,tot_questions=len(questions),tot_corrects=tot_corrects)

# ==============================================================
# QUESTIONS PAGE (ONLY ADMIN)
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
