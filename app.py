"""
Import modules
"""
import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from flask import Flask, redirect, url_for, render_template, request, session
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
from bson import ObjectId

app = Flask(__name__)

# AWS S3 variables
s3_bucket_name = "myquizgame"
s3_bucket_url = "https://myquizgame.s3.eu-west-1.amazonaws.com/"
client = boto3.client('s3',
                      aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                      aws_secret_access_key=os.environ.get
                      ("AWS_SECRET_ACCESS_KEY"))

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

    if request.method == "POST":
        # Click onto "Create account" button

        # Get vars from page
        username = request.form["username"]
        password = request.form["password"]

        user = db_users.find_one({"username": username, "password": password})
        if user:
            # if user exists -> Open session and go to the quiz

            # Create session for user by username
            session["id_user"] = str(user["_id"])
            session["username"] = user["username"]
            session["level"] = user["level"]

            if user["level"] == "admin":
                # Check level of this user - Jump to page for create questions
                return redirect(url_for("questions"))

            # Jump to page Quiz
            return redirect(url_for("quiz"))

        # Return error in login page
        error = "Error: incorrect username or password"
        return render_template("login.html", error=error)

    # Simply open page
    return render_template("login.html")


@app.route("/logout")
def logout():
    """
    Logout function: remove session to log user out
    """

    # Clear session
    session.clear()

    # return to the login page
    return redirect(url_for("login"))


@app.route("/registration", methods=["POST", "GET"])
def registration():
    """
    Registration page
    """

    # Variables initialization
    error = None
    message = None

    if request.method == "POST":
        # Click on button "Create account" - Get vars from page
        username = request.form["username"]
        password = request.form["password"]
        password2 = request.form["password2"]
        level = "user"

        if username == "" or password == "" or password2 == "":
            # Check if all fields are filled

            # Return page with error
            error = "Error: All fields are required"
            session["error"] = error
            return render_template("registration.html", error=error)

        if password != password2:
            # Check if passwords are equal - Return error in registration page
            error = "Error: Passwords do not match"
            return render_template("registration.html", error=error)

        # Check if user exists -> Return Error
        user_exists = db_users.find_one({"username": username})
        if user_exists:

            # Return error in registration page
            error = "Error: this username alredy exists"
            return render_template("registration.html", error=error)

        # Create new record in DB
        new_user = {
            "username": username,
            "password": password,
            "level": level,
            "created_at": now(),
        }
        db_users.insert_one(new_user)

        # Jump to login page whit message
        message = "User created successfully, now you can log in"
        return render_template("registration.html", message=message)

    # Simply open page
    return render_template("registration.html")


@app.route("/quiz", methods=["POST", "GET"])
def quiz():
    """
    Quiz page
    """

    if session.get("id_quiz") is None:
        # If not exist quiz session -> create new one

        # Create new quiz session in db and get the id
        query = {
            "id_user": session.get("id_user"),
            "total_corrects": 0,
            "created_at": now(),
        }
        id_quiz = str(db_quiz_done.insert_one(query).inserted_id)

        # Create session for the quiz starting from the first question
        session["id_quiz"] = id_quiz
        session["quiz_question"] = 0

        # Go to the quiz page
        return redirect(url_for("quiz"))

    # Get inputs from user if exist
    next_question = request.args.get("next")
    answer = request.args.get("ans")

    # Get all questions
    list_questions = list(db_questions.find())

    # Check if number of actual question is smoller than total questions
    if session.get("quiz_question") >= len(list_questions):

        # Go directly to results page
        return redirect(url_for("results"))

    # Get the actual question number
    question = list_questions[session.get("quiz_question")]

    if next_question is None:
        # If answer present, use it
        query = {
            "id_quiz_done": session["id_quiz"],
            "id_question": str(question["_id"]),
        }
        answer_db = db_answers_done.find_one(query)
        if answer_db:
            answer = answer_db["answer_number"]
            if question["correct"] == answer:
                response = "correct"
            else:
                response = "wrong"
            return render_template(
                "quiz.html",
                question=question,
                tot_question=len(list_questions),
                answer=answer,
                response=response,
            )

    if answer:
        # Check if there is an answer

        # save choice in db
        query = {
            "id_quiz_done": session["id_quiz"],
            "id_question": str(question["_id"]),
            "answer_number": answer,
            "created_at": now(),
        }
        db_answers_done.insert_one(query)

        if question["correct"] == answer:
            # check if the answer is correct

            # get info from db of this quiz session
            query = {"_id": ObjectId(session["id_quiz"])}
            quiz_db = db_quiz_done.find_one(query)

            # If there are no correct, set to zero
            total_corrects = 0
            if quiz_db:
                total_corrects = quiz_db["total_corrects"]

            # increment correct from total
            values = {"total_corrects": total_corrects + 1}
            db_quiz_done.update_one(query, {"$set": values})

            # answer is correct
            return render_template(
                "quiz.html",
                question=question,
                tot_question=len(list_questions),
                answer=answer,
                response="correct",
            )

        # answer is wrong
        return render_template(
            "quiz.html",
            question=question,
            tot_question=len(list_questions),
            answer=answer,
            response="wrong",
        )

    if next_question:
        # Go to the next question

        # go to the next one
        session["quiz_question"] = session.get("quiz_question") + 1

        if session["quiz_question"] >= len(list_questions):
            # check if you have another question

            # show the result page
            return redirect(url_for("results"))

        # go to the next question
        return redirect(url_for("quiz"))

    # Go to login page
    return render_template(
        "quiz.html", question=question, tot_question=len(list_questions)
    )


@app.route("/results", methods=["POST", "GET"])
def results():
    """
    Results page, only for logged users
    """

    id_quiz_done = request.args.get("id_quiz")
    if id_quiz_done is None:
        # Check if id_quiz exists or exists last session
        id_quiz_done = session["id_quiz"]

    if id_quiz_done is None:
        # If quiz session does not exist -> start new quiz
        return redirect(url_for("quiz"))

    if request.args.get("try_again"):
        # If push on "Try again" -> reset session
        session.pop("id_quiz", None)
        session.pop("quiz_question", None)
        return redirect(url_for("quiz"))

    # get info from db of this quiz session
    questions_list = list(db_questions.find())
    tot_corrects = db_quiz_done.find_one({"_id": ObjectId(id_quiz_done)})[
        "total_corrects"
    ]

    # print results
    result = []
    for question in questions_list:
        query = {"id_quiz_done": id_quiz_done,
                 "id_question": str(question["_id"])}

        # If there are no answers to the questions, enter zero
        answer_done = 0
        answer_db = db_answers_done.find_one(query)
        if answer_db:
            answer_done = answer_db["answer_number"]

        # This is the final object shown to the user
        obj = {
            "question": question["question"],
            "answer1": question["answer1"],
            "answer2": question["answer2"],
            "answer3": question["answer3"],
            "answer4": question["answer4"],
            "correct": question["correct"],
            "answer_done": answer_done,
        }

        result.append(obj)

    # Show quiz results
    return render_template(
        "results.html",
        results=result,
        tot_questions=len(questions_list),
        tot_corrects=tot_corrects,
    )


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
        # check if user are logged
        return redirect(url_for("login"))

    # get all quiz done by user
    result = []
    lists = list(db_quiz_done.find({"id_user": session.get("id_user")}))
    for res in lists:
        obj = {
            "id_quiz": str(res["_id"]),
            "total_corrects": res["total_corrects"],
            "created_at": res["created_at"],
        }
        result.append(obj)

    # print
    return render_template("all_results.html",
                           results=result, tot_results=len(result))


# Edit profile page (only for logged user)
@app.route("/edit_profile", methods=["POST", "GET"])
def edit_profile():
    """
    In this page you can edit your image
    """

    if session.get("id_user") is None:
        # check if user are logged
        return redirect(url_for("login"))

    # get image if is present
    contents = show_image(s3_bucket_name, session.get("id_user"))

    # upload file
    if request.method == "POST":
        image = request.files['file']

        # check if extension is jpg
        fileinfo = image.filename.split('.')
        extension = fileinfo[len(fileinfo)-1]
        if extension != "jpg":
            error = "Only jpg images are allowed"
            return render_template("edit_profile.html", image="", error=error)

        # rename the file with user id
        filename = session.get("id_user")+'.'+extension
        image_file = secure_filename(filename)

        # upload image on AWS Bucket
        try:
            s3 = boto3.resource('s3')
            s3.Bucket(s3_bucket_name).put_object(Key=image_file, Body=image)
        except ClientError:
            raise Exception("Exception when uploading"
                            "the image to AWS S3 bucket")

        # return to edit profile page
        return redirect(url_for("edit_profile"))

    # print
    return render_template("edit_profile.html", image=contents)


# Upload file function
def upload_file(file_name, bucket):
    object_name = file_name
    s3_client = boto3.client('s3')
    response = s3_client.upload_file(file_name, bucket, object_name)
    return response


# Show image in bucket on AWS
def show_image(bucket, id_user):
    s3_client = boto3.client('s3')
    url = ""

    try:
        for item in s3_client.list_objects(Bucket=bucket)['Contents']:
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                 Params={'Bucket': bucket, 'Key': item['Key']},
                 ExpiresIn=100
                 )

            if presigned_url.find(id_user) != -1:
                url = presigned_url

    except Exception as e:
        pass

    # Return URL of the image
    return url


# Delete your image profile
@app.route("/delete_image_profile")
def delete_image_profile():

    if session.get("id_user") is None:
        # check if user are logged
        return redirect(url_for("login"))

    # get full name of the image
    namefile = session.get("id_user")+".jpg"

    # delete image from bucket
    s3_client = boto3.client('s3')
    response = s3_client.delete_object(
        Bucket=s3_bucket_name,
        Key=namefile
    )

    # return to edit profile page
    return redirect(url_for("edit_profile"))


# Questions page (only for admin)
@app.route("/questions", methods=["POST", "GET"])
def questions():
    """
    Questions page, only for admins
    """

    if session.get("level") != "admin":
        # Block if it's admin
        return redirect(url_for("login"))

    # Get message and errors
    message = session.get("message")
    session["message"] = ""
    error = session.get("error")
    session["error"] = ""

    # Prepare fields
    fields = {}

    id_question = request.args.get("id_question")
    if id_question:
        # Take values if is edit mode

        # Get fields from db
        query = {"_id": ObjectId(id_question)}
        result = db_questions.find_one(query)

        # Get fields from Database
        fields = {
            "question": result["question"],
            "answer1": result["answer1"],
            "answer2": result["answer2"],
            "answer3": result["answer3"],
            "answer4": result["answer4"],
            "correct": result["correct"],
        }

    if request.method == "POST":
        # Click on button "Save question"

        # Get all fields from post
        question = request.form["question"]
        answer1 = request.form["answer1"]
        answer2 = request.form["answer2"]
        answer3 = request.form["answer3"]
        answer4 = request.form["answer4"]
        correct = request.form["correct"]

        if (
            question == "" or
            answer1 == "" or
            answer2 == "" or
            answer3 == "" or
            answer4 == "" or
            correct == ""
        ):
            # Check if all fields are filled

            # Return page with error
            error = "Error: All fields are required"
            session["error"] = error
            return redirect(url_for("questions"))

        if id_question:
            # Get id question if you want to edit an existing one

            # Edit question
            query = {"_id": ObjectId(id_question)}
            values = {
                "question": question,
                "answer1": answer1,
                "answer2": answer2,
                "answer3": answer3,
                "answer4": answer4,
                "correct": correct,
            }
            db_questions.update_one(query, {"$set": values})

            # Jump to questions page whit message
            message = "Question edited successfully"
            session["message"] = message

        else:

            # Adding new question
            query = {
                "question": question,
                "answer1": answer1,
                "answer2": answer2,
                "answer3": answer3,
                "answer4": answer4,
                "correct": correct,
            }
            db_questions.insert_one(query)

            # Jump to questions page with message
            message = "Question created successfully"
            session["message"] = message

        return redirect(url_for("questions"))

    # Simply open page

    # Get all questions
    questions_list = list(db_questions.find())

    # Open page
    return render_template(
        "questions.html",
        questions=questions_list,
        id_question=id_question,
        tot=len(questions_list),
        fields=fields,
        error=error,
        message=message,
    )


@app.route("/delete_question", methods=["POST", "GET"])
def delete_question():
    """
    Delete question (only for admins)
    """

    if session.get("level") != "admin":
        # Block if admin
        return redirect(url_for("login"))

    id_question = request.args["id_question"]
    if id_question == "":
        # Get id question to delete record from db

        # Return page with error
        error = "Error: ID not found"
        session["error"] = error
        return redirect(url_for("questions"))

    # Delete record
    query = {"_id": ObjectId(id_question)}
    db_questions.remove(query)

    # Redirect to questions page
    return redirect(url_for("questions"))


@app.route("/users", methods=["POST", "GET"])
def users():
    """
    Users page, only for admins
    """

    if session.get("level") != "admin":
        # Block if admin
        return redirect(url_for("login"))

    # Get messages and errors
    message = session.get("message")
    session["message"] = ""
    error = session.get("error")
    session["error"] = ""

    # Prepare fields
    fields = {}

    id_user = request.args.get("id_user")
    if id_user:
        # Take values if is edit mode

        # Get fields from db
        query = {"_id": ObjectId(id_user)}
        result = db_users.find_one(query)

        # Get fields from db
        fields = {
            "username": result["username"],
            "password": result["password"],
            "level": result["level"],
            "created_at": result["created_at"],
        }

    if request.method == "POST":
        # Click on button "Save question"

        username = request.form["username"]
        password = request.form["password"]
        level = request.form["level"]

        if id_user == "" or username == "" or password == "" or level == "":

            # Return page with error
            error = "Error: All fields are required"
            session["error"] = error
            return redirect(url_for("users"))

        if id_user:
            # Get id user if you want to edit an existing one

            # Edit user
            query = {"_id": ObjectId(id_user)}
            values = {"username": username,
                      "password": password,
                      "level": level}
            db_users.update_one(query, {"$set": values})

            # Jump to users page whit message
            message = "User edited successfully"
            session["message"] = message

        else:

            # Adding new user
            query = {
                "username": username,
                "password": password,
                "level": level,
                "created_at": now(),
            }
            db_users.insert_one(query)

            # Jump to users page with message
            message = "User created successfully"
            session["message"] = message

        return redirect(url_for("users"))

    # get list of users
    users_list = list(db_users.find())

    # render page
    return render_template(
        "users.html",
        users=users_list,
        tot=len(users_list),
        id_user=id_user,
        fields=fields,
        error=error,
        message=message,
    )


@app.route("/delete_user", methods=["POST", "GET"])
def delete_user():
    """
    Delete user, only for admins
    """

    if session.get("level") != "admin":
        # Block if admin
        return redirect(url_for("login"))

    id_user = request.args["id_user"]
    if id_user == "":
        # Get id question to delete record from db

        # Return page with error
        error = "Error: ID not found"
        session["error"] = error
        return redirect(url_for("users"))

    # Delete record
    query = {"_id": ObjectId(id_user)}
    db_users.remove(query)

    # Redirect to questions page
    return redirect(url_for("users"))


def now():
    """
    Function to get actual datetime
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")), debug=False)
