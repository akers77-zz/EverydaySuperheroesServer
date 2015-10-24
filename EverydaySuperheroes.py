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
    login_required()

    if not requiredAttributes(newJobAttributes):
        abort(404, attributesErrorMessage)

    try:
        activejobs = Job.select().where((Job.requester == session["user_id"]) & (Job.completed == False)).get()
        abort(404, "Cannot create job - user already has an active job!")
    except Job.DoesNotExist:
        job = Job.create(accepted=False,
                             acceptor=None,
                             completed=False,
                             date=datetime.now(),
                             description=request.form["description"],
                             latitude=request.form["latitude"],
                             longitude=request.form["longitude"],
                             name=request.form["name"],
                             requester=session["user_id"],
                             type=request.form["type"]
                             )
        job.save()

    return success


@app.route("/locationupdate", methods=["POST"])
def location_update():
    login_required()

    if not requiredAttributes(locationAttributes):
        abort(404, attributesErrorMessage)

    try:
        previousLocation = UserLocation.get(UserLocation.user == session["user_id"])
        previousLocation.latitude = request.form["latitude"]
        previousLocation.longitude = request.form["longitude"]
        previousLocation.save()
    except UserLocation.DoesNotExist:
        location = UserLocation.create(user=session["user_id"],
                                       latitude=request.form["latitude"],
                                       longitude=request.form["longitude"],
                                       time=datetime.now())
        location.save()

    return success



@app.route("/acceptjob", methods=["POST"])
def accept_job():
    login_required()

    if not requiredAttributes(acceptJobAttributes):
        abort(404, attributesErrorMessage)

    job = get_object_or_404(Job, Job.id == request.form["job"])
    if job.requester == session["user_id"]:
        abort(404, "Cannot accept your own job!")

    try:
        acceptedJobs = Job.get(Job.acceptor == session["user_id"])
        abort(404, "User has already selected a job - cannot accept another!")
    except Job.DoesNotExist:
        person = get_object_or_404(User, User.id == session["user_id"])

        job.accepted = True
        job.acceptor = person
        job.save()

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

    try:
        registeredUser = User.get(User.email == request.form["email"])
        abort(404, "Email address already in use!")

    except User.DoesNotExist:
        password = request.form['password'].encode('utf-8')
        encryptedPassword = bcrypt.hashpw(password, bcrypt.gensalt())

        user = User.create(email=request.form["email"], name=request.form["name"], password=encryptedPassword)
        user.save()

        auth_user(user)
        return success


@app.route('/login', methods=['POST'])
def login():
    if request.form['email']:
        try:
            user = User.get(email=request.form['email'])
        except User.DoesNotExist:
            abort(404, "The username or password is incorrect")

        password = request.form['password'].encode('utf-8')
        userPassword = user.password.encode('utf-8')

        if bcrypt.hashpw(password, userPassword) != userPassword:
            abort(404, "The email or password is incorrect")
        else:
            auth_user(user)
            return success
    else:
        abort(404, "No email address supplied!")


@app.route('/logout/')
def logout():
    session.pop('logged_in', None)
    return success

def requiredAttributes(requiredattributes):
    for attribute in requiredattributes:
        if not attribute in request.form:
            return False

    return True


def get_object_or_404(model, *expressions):
    try:
        return model.get(*expressions)
    except model.DoesNotExist:
        abort(404, "Model does not exist!")


if __name__ == "__main__":
    app.run()