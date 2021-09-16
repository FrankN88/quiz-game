from flask import Flask, redirect, url_for, render_template, request, session
from flask_pymongo import PyMongo

#Config access to MongoDB
app = Flask(__name__)
app.config["MONGO_URI"] = os.environ['MONGO_URI']
mongo = PyMongo(app)