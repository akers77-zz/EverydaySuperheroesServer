from functools import wraps
import json
import bcrypt as bcrypt
from flask import Flask, request, abort, session, jsonify
from datetime import datetime
from datamodels.Models import *

app = Flask(__name__)
app.secret_key = "\xf3rh\xf7\x86\xfb\x0e\xd8\xc1E\xa3\xdf\xfar\xdf2\x05\xd3CR\xf2C\x95\xef"

acceptJobAttributes = ["job"]
locationAttributes = ["latitude", "longitude"]
loginAttributes = ["email", "password"]
newJobAttributes = ["description", "latitude", "longitude", "name", "type"]
userRegisterAttributes = ["email", "name", "password"]

attributesErrorMessage = "Not all attributes supplied!"

success = json.dumps({'success':True}), 200, {'ContentType':'application/json'}

def login_required():
    if not "logged_in" in session.keys():
        abort(404, "Not logged in!")


def auth_user(user):
    session['logged_in'] = True
    session['user_id'] = user.id
    session['name'] = user.name


def get_current_user():
    if session.get('logged_in'):
        return User.get(User.id == session['user_id'])


@app.route("/createjob", methods=["POST"])
def createjob():
    #login_required()

    if not requiredAttributes(newJobAttributes):
        abort(404, attributesErrorMessage)

    json = request.get_json()

    try:
        activejobs = Job.select().where((Job.requester == 2) & (Job.completed == False)).get()
        abort(404, "Cannot create job - user already has an active job!")
    except Job.DoesNotExist:
        job = Job.create(accepted=False,
                             acceptor=None,
                             completed=False,
                             date=datetime.now(),
                             description=json["description"],
                             latitude=json["latitude"],
                             longitude=json["longitude"],
                             name=json["name"],
                             requester=2,
                             type=json["type"]
                             )
        job.save()

    return success


@app.route("/locationupdate", methods=["POST"])
def location_update():
    login_required()

    if not requiredAttributes(locationAttributes):
        abort(404, attributesErrorMessage)

    json = request.get_json()

    try:
        previousLocation = UserLocation.get(UserLocation.user == session["user_id"])
        previousLocation.latitude = json["latitude"]
        previousLocation.longitude = json["longitude"]
        previousLocation.save()
    except UserLocation.DoesNotExist:
        location = UserLocation.create(user=session["user_id"],
                                       latitude=json["latitude"],
                                       longitude=json["longitude"],
                                       time=datetime.now())
        location.save()

    return success


@app.route("/getuserjob", methods=["POST"])
def accept_job():
    login_required()

    job = get_object_or_404(Job, Job.requester == session["user_id"])

    return jsonify()


@app.route("/registeruser", methods=["POST"])
def register_user():
    if not requiredAttributes(userRegisterAttributes):
        abort(404, attributesErrorMessage)

    json = request.get_json()

    try:
        registeredUser = User.get(User.email == json["email"])
        abort(404, "Email address already in use!")

    except User.DoesNotExist:
        password = json['password'].encode('utf-8')
        encryptedPassword = bcrypt.hashpw(password, bcrypt.gensalt())

        user = User.create(email=json["email"], name=json["name"], password=encryptedPassword)
        user.save()

        auth_user(user)
        return success


@app.route('/login', methods=['POST'])
def login():
    if not requiredAttributes(loginAttributes):
        abort(404, attributesErrorMessage)

    json = request.get_json()

    try:
        user = User.get(email=json['email'])
    except User.DoesNotExist:
        abort(404, "The username or password is incorrect")

    password = json['password'].encode('utf-8')
    userPassword = user.password.encode('utf-8')

    if bcrypt.hashpw(password, userPassword) != userPassword:
        abort(404, "The email or password is incorrect")
    else:
        auth_user(user)
        return success


@app.route('/logout/')
def logout():
    session.pop('logged_in', None)
    return success

def requiredAttributes(requiredattributes):
    json = request.get_json()

    for attribute in requiredattributes:
        if not attribute in json:
            return False

    return True


def get_object_or_404(model, *expressions):
    try:
        return model.get(*expressions)
    except model.DoesNotExist:
        abort(404, "Model does not exist!")


if __name__ == "__main__":
    app.run()