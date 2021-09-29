import os
from flask import Flask, redirect, url_for, render_template, request, session
from flask_pymongo import PyMongo
from bson import ObjectId
if os.path.exists("env.py"):
    import env

"""
Config access to MongoDB with .env file
"""
app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)

"""
Get collections from mongo db
"""
db_users = mongo.db.users
db_questions = mongo.db.questions
db_quiz_done = mongo.db.quiz_done
db_answers_done = mongo.db.answers_done


@app.route("/", methods=["POST", "GET"])
def home():
    """
    Home page
    """
    
    return render_template("home.html")


@app.route("/login", methods=["POST", "GET"])
def login():
    """
    Login page with access
    """

    # Variables initialization
    error = None
    message = None

    if request.method == "POST":
        # Click on button "Create account"

        #Get vars from page
        username = request.form['username']
        password = request.form['password']

        user = db_users.find_one({'username':username,'password':password})
        if user:
            #Check if user exists -> Open session and go to quiz

            #Create session for user by username
            session['id_user'] = str(user['_id'])
            session['username'] = user['username']
            session['level'] = user['level']

            if user['level'] == "admin":
                #Check level of this user
                
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


@app.route("/logout")
def logout():
    """
    Logout function: remove session to log user out
    """

    # Clear session
    session.clear()

    # return to login page
    return redirect(url_for('login'))


@app.route("/registration", methods=["POST", "GET"])
def registration():
    """
    Registration page
    """

    # Variables initialization
    error = None
    message = None

    if request.method == "POST":
        # Click on button "Create account"
        
        #Get vars from page
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password2']
        level = "user"

        if password != password2:
            #Check if password1 and password2 are equals
            
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
            message = "User created successfully, now you can log in"
            return render_template("registration.html",message=message)
    else:

        #Simply open page
        return render_template("registration.html")



@app.route("/quiz", methods=["POST", "GET"])
def quiz():
    """
    Quiz page
    """

    if session.get("id_quiz") is None:
        #If not exist quiz session -> create new one

        #Create new quiz session in db and get the id
        query = {'id_user' : session.get("id_user"), 'total_corrects' : 0}
        id_quiz = str(db_quiz_done.insert_one(query).inserted_id)

        #Create session for actual quiz starting from the first question
        session['id_quiz'] = id_quiz
        session['quiz_question'] = 0

        #Go to quiz page
        return redirect(url_for('quiz'))

    else:

        # Get inputs from user if exist
        next_question = request.args.get('next')
        answer = request.args.get('ans')

        #Get all questions
        questions = list(db_questions.find())

        #Check if number of actual question is smoller than total questions
        if session.get('quiz_question') >= len(questions):

            #Go directli to results page
            return redirect(url_for("results"))

        #Get the actual question number
        question = questions[session.get('quiz_question')]

        if next_question is None:
            # If there is already an answer, use it and don't change it with a new one
            query = {"id_quiz_done":session['id_quiz'], "id_question": str(question["_id"])}
            answer_db = db_answers_done.find_one(query)
            if answer_db:
                answer = answer_db['answer_number']
                if question['correct'] == answer:
                    response = 'correct'
                else:
                    response = 'wrong'
                return render_template("quiz.html",question = question, tot_question = len(questions), answer = answer, response = response)

        if answer:
            #Check if there is an answer

            #save choice in db
            query = { 'id_quiz_done' : session['id_quiz'], 'id_question' : str(question['_id']), 'answer_number' : answer }
            db_answers_done.insert_one(query)

            if question['correct'] == answer:
                #check if the answer is correct

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
        
        if next_question:
            #Go to the next question

            #go to the next one
            session['quiz_question'] = session.get("quiz_question")+1

            if session['quiz_question'] >= len(questions):
                #check if you have another question

                #show the result page
                return redirect(url_for("results"))
            
            else:
                
                #go to the next question
                return redirect(url_for('quiz'))

        else:

            #Go to login page
            return render_template("quiz.html",question = question, tot_question = len(questions))


@app.route("/results", methods=["POST", "GET"])
def results():
    """
    Results page, only for logged users
    """

    id_quiz_done = request.args.get('id_quiz')    
    if id_quiz_done is None:
        #Check if id_quiz exists or exists last session
        id_quiz_done = session['id_quiz']

    if id_quiz_done is None:
        #If quiz session not exists -> start new quiz
        return redirect(url_for('quiz'))

    if request.args.get('try_again'):
        #If push on "Try again" -> reset session
        session.pop('id_quiz', None)
        session.pop('quiz_question', None)
        return redirect(url_for('quiz'))

    #get info from db of this quiz session
    questions = list(db_questions.find())
    tot_corrects = db_quiz_done.find_one({"_id": ObjectId(id_quiz_done)})['total_corrects']

    #print results
    results = []
    for question in questions:
        query = {"id_quiz_done": id_quiz_done, "id_question" : str(question['_id'])}
        answer_done = db_answers_done.find_one(query)

        # This is the final object shown to the user
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

@app.route("/404")
def page404():
    """
    Page 404
    """
    return render_template("404.html")


@app.route("/all_results")
def all_results():
    """
    Results page, only for logged users
    """

    if session.get("id_user") is None:
        #check if user are logged
        return redirect(url_for('login'))
    
    #get all quiz done by user
    results = []
    lists = list(db_quiz_done.find({"id_user" : session.get("id_user")}))
    for res in lists:
        obj = {
            "id_quiz" : str(res['_id']),
            "total_corrects" : res['total_corrects'],
        }
        results.append(obj)
    
    #print
    return render_template("all_results.html",results=results)


# QUESTIONS PAGE (ONLY ADMIN)
@app.route("/questions", methods=["POST", "GET"])
def questions():

    if session.get("level") != "admin":
        # BLOCK IF IS ADMIN
        return redirect(url_for('login'))

    #GET MESSAGE AND ERRORS IF EXIST
    message = session.get('message')
    session['message'] = ""
    error = session.get('error')
    session['error'] = ""

    #Prepare fields
    fields = {}

    id_question = request.args.get('id_question')
    if id_question:
        #Take values if is edit mode

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

    if request.method == "POST":
        # Click on button "Save question"

        #Get all fields from post
        question = request.form['question']
        answer1 = request.form['answer1']
        answer2 = request.form['answer2']
        answer3 = request.form['answer3']
        answer4 = request.form['answer4']
        correct = request.form['correct']

        if question == "" or answer1 == "" or answer2 == "" or answer3 == "" or answer4 == "" or correct == "":
            #Check if all fields are filled

            #Return page with error
            error = "Error: All fields are required"
            session['error'] = error
            return redirect(url_for('questions'))

        else:

            if id_question:
                #Get id question if you want to edit an existing one

                #Edit question
                query = {"_id": ObjectId(id_question)}
                values = {'question' : question, 'answer1' : answer1, 'answer2' : answer2, 'answer3' : answer3, 'answer4' : answer4, 'correct' : correct}
                db_questions.update_one(query, {"$set": values})

                #Jump to questions page whit message
                message = "Question edited successfully"
                session['message'] = message

            else:

                #Adding new question
                query = {'question' : question, 'answer1' : answer1, 'answer2' : answer2, 'answer3' : answer3, 'answer4' : answer4, 'correct' : correct}
                db_questions.insert_one(query)

                #Jump to questions page whit message
                message = "Question created successfully"
                session['message'] = message

            return redirect(url_for('questions'))

    else:
        # Simply open page

        #Get all questions
        questions = list(db_questions.find())

        #Open page
        return render_template("questions.html",questions=questions,id_question=id_question,tot=len(questions),fields=fields,error=error,message=message)


@app.route("/delete_question", methods=["POST", "GET"])
def delete_question():
    """
    Delete question (only for admins)
    """

    if session.get("level") != "admin":
        #BLOCK IF IS ADMIN
        return redirect(url_for('login'))

    id_question = request.args['id_question']
    if id_question == "":
        #Get id question to delete record from db

        #Return page with error
        error = "Error: ID not found"
        session['error'] = error
        return redirect(url_for('questions'))

    else:

        #Delete record
        query = { "_id": ObjectId(id_question) }
        db_questions.remove(query)

        #Redirect to questions page
        return redirect(url_for('questions'))


@app.route("/users", methods=["POST", "GET"])
def users():
    """
    Users page, only for admins
    """

    if session.get("level") != "admin":
        #BLOCK IF IS ADMIN
        return redirect(url_for('login'))

    #GET MESSAGES AND ERRORS IF EXIST
    message = session.get('message')
    session['message'] = ""
    error = session.get('error')
    session['error'] = ""

    #Prepare fields
    fields = {}

    id_user = request.args.get('id_user')
    if id_user:
        #Take values if is edit mode

        # Get fields from db
        query = { "_id": ObjectId(id_user) }
        result = db_users.find_one(query)
        
        # Get fields from Database
        fields = {
            'username' : result['username'],
            'password' : result['password'],
            'level' : result['level']
        }

    if request.method == "POST":
        # Click on button "Save question"

        username = request.form['username']
        password = request.form['password']
        level = request.form['level']

        if id_user == "" or username == "" or password == "" or level == "":

            #Return page with error
            error = "Error: All fields are required"
            session['error'] = error
            return redirect(url_for('users'))

        else:

            if id_user:
                #Get id user if you want to edit an existing one

                #Edit user
                query = {"_id": ObjectId(id_user)}
                values = {'username' : username, 'password' : password, 'level' : level}
                db_users.update_one(query, {"$set": values})

                #Jump to users page whit message
                message = "User edited successfully"
                session['message'] = message

            else:

                #Adding new user
                query = {'username' : username, 'password' : password, 'level' : level}
                db_users.insert_one(query)

                #Jump to users page whit message
                message = "User created successfully"
                session['message'] = message

            return redirect(url_for('users'))

    #get list of users
    users = list(db_users.find())

    #render page
    return render_template("users.html",users=users,tot=len(users),id_user=id_user,fields=fields,error=error,message=message)


@app.route("/delete_user", methods=["POST", "GET"])
def delete_user():
    """
    Delete user, only for admins
    """

    if session.get("level") != "admin":
        #BLOCK IF IS ADMIN
        return redirect(url_for('login'))

    id_user = request.args['id_user']
    if id_user == "":
        #Get id question to delete record from db

        #Return page with error
        error = "Error: ID not found"
        session['error'] = error
        return redirect(url_for('users'))

    else:

        #Delete record
        query = { "_id": ObjectId(id_user) }
        db_users.remove(query)

        #Redirect to questions page
        return redirect(url_for('users'))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=False)
