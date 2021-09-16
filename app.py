from flask import Flask, redirect, url_for, render_template, request, session
from flask_pymongo import PyMongo
import os
if os.path.exists("env.py"):
    import env

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
db_questions = mongo.db.questions

# ==============================================================
# HOME/LOGIN PAGE
# ==============================================================
@app.route("/")
def home():
    return render_template("home.html")