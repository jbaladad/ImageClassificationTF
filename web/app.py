from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import numpy
import tensorflow as tf
import requests
import subprocess
import json

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.ImageClassification
users = db["Users"]

def UserExist(username):
    if users.find({"Username": username}).count() == 0:
        return False
    else:
        return True

class Register(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]

        if UserExist(username):
            retJson = {
                "status": 301,
                "message": "Invalid username"
            }

            return jsonify(retJson)

        hashedPw = bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt())

        users.insert({
            "Username": username,
            "Password": hashedPw,
            "Tokens": 4
        })

        retJson = {
            "status": 200,
            "message": "You successfully signed up for this API."
        }

        return jsonify(retJson)

def verifyPassword(username, password):
    hashedPw = users.find({
        "Username": username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode("utf8"), hashedPw)  == hashedPw:
        return True
    else:
        return False

def generateReturnDictionary(status, message):
    retJson = {
        "status": status,
        "message": message
    }            

    return retJson

def verifyCredentials(username, password):
    if not UserExist(username):
        return generateReturnDictionary(301, "Invalid Username"), True

    correctPw = verifyPassword(username, password)
    if not correctPw:
        return generateReturnDictionary(302, "Invalid Password"), True

    return None, False

class Classify(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        url = postedData["url"]

        retJson, error = verifyCredentials(username, password)
        if error:
            return jsonify(retJson)
    
        tokens = users.find({
            "Username": username
        })[0]["Tokens"]

        if tokens <= 0:
            return jsonify(generateReturnDictionary(303, "Not enough tokens"))

        r = requests.get(url)
        retJson = {}
        with open("temp.jpg", "wb") as f:
            f.write(r.content)
            proc = subprocess.Popen('python classify_image.py --model_dir=. --image_file=./temp.jpg', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            proc.communicate()[0]
            proc.wait()
            with open("text.txt") as g:
                retJson = json.load(g)

        users.update({
            "Username": username
        }, {
            "$set": {
                "Tokens": tokens-1
            }
        })        
        return retJson

class Refill(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["admin_pw"]
        amount = postedData["amount"]
    
        if not UserExist(username):
            return jsonify(generateReturnDictionary(301, "Invalid Username"))

        correctPw = "abc123"
        if not password == correctPw:
            return jsonify(generateReturnDictionary(304, "Invalid Admin Password"))

        users.update({
            "Username": username
        }, {
            "$set": {
                "Tokens": amount
            }
        })     

        return jsonify(generateReturnDictionary(200, "Refilled Successfully"))

api.add_resource(Register, '/register')
api.add_resource(Classify, '/classify')
api.add_resource(Refill, '/refill')

if __name__ == "__main__":
    app.run(host="0.0.0.0")