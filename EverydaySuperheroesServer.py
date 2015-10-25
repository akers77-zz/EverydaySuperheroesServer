from functools import wraps
import json
import bcrypt as bcrypt
from flask import Flask, request, abort, session, jsonify
from datetime import datetime
from datamodels.Models import *

app = Flask(__name__)
app.secret_key = "\xf3rh\xf7\x86\xfb\x0e\xd8\xc1E\xa3\xdf\xfar\xdf2\x05\xd3CR\xf2C\x95\xef"

jobAttribute = ["jobid"]
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

    if not requiredAttributes(newJobAttributes, request.get_json()):
        abort(404, attributesErrorMessage)

    json = request.get_json()

    nextRequester = Job.select().count() + 1

    activejobs = Job.select().where((Job.requester_id == nextRequester) & (not Job.completed))

    #Should only ever be 0 or 1
    getJobIds = [job.id for job in activejobs]
    if len(getJobIds) > 0:
        abort(404, "Cannot create job - user already has an active job!")

    job = Job.create(accepted=False,
                         attendee=None,
                         completed=False,
                         date=datetime.now(),
                         description=json["description"],
                         latitude=json["latitude"],
                         longitude=json["longitude"],
                         name=json["name"],
                         requester=nextRequester,
                         type=json["type"]
                         )
    job.save()

    return jsonify(job=job.id)


@app.route("/updatelocation", methods=["POST"])
def update_location():
    login_required()

    if not requiredAttributes(locationAttributes, request.get_json()):
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


@app.route('/acceptjob', methods=['POST'])
def accept_job():
    login_required()

    if not requiredAttributes(jobAttribute, request.get_json()):
        abort(404, attributesErrorMessage)

    json = request.get_json()

    job = get_object_or_404(Job, Job.id == json['jobid'])
    if job.requester == session["user_id"]:
        abort(404, "You cannot accept your own job!")

    try:
        acceptedJobs = Job.get(Job.attendee == session["user_id"])
        abort(404, "User has already selected a job - cannot accept another")
    except Job.DoesNotExist:
        person = get_object_or_404(User, User.id == session["user_id"])

        job.accepted = True
        job.attendee = person
        job.save()

    return success


@app.route("/getattendeelocation", methods=['GET'])
def get_attendee_location():
    #login_required()

    if not requiredAttributes(jobAttribute, request.args):
        abort(404, attributesErrorMessage)

    try:
        job = Job.select().where(Job.id == request.args['jobid'] & Job.accepted).get()
    except Job.DoesNotExist:
        abort(404, "Job is not currently being attended!")

    try:
        userloc = UserLocation.select().where(UserLocation.user == job.attendee).get()
    except UserLocation.DoesNotExist:
        abort(404, "Attendee location not set!")

    return jsonify(attendee=job.attendee_id, latitude=userloc.latitude, longitude=userloc.longitude)


@app.route("/getjobinfo", methods=["GET"])
def get_job_info():
    #login_required()

    if not requiredAttributes(jobAttribute, request.args):
        abort(404, attributesErrorMessage)

    args = request.args

    try:
        #job = Job.select().where(Job.id == json["job"] & (Job.attendee == session["user_id"] | Job.requester == session["user_id"])).get()
        job = Job.select().where(Job.id == args["jobid"]).get()
    except Job.DoesNotExist:
        abort(404, "No such job exists!")

    return jsonify(jobId=job.id,description=job.description,type=job.type,longitude=job.longitude,latitude=job.latitude,
                   name=job.name,accepted=job.accepted,attendee=job.attendee_id,requester=job.requester_id)


@app.route("/getuserjob", methods=["GET"])
def get_user_job():
    login_required()

    job = Job.select().where(Job.requester == session["user_id"] & Job.completed == False).get()

    return jsonify(job=job.id)


@app.route("/isattended", methods=["GET"])
def isattended():
    login_required()

    if not requiredAttributes(jobAttribute, request.args):
        abort(404, attributesErrorMessage)

    args = request.args

    job = Job.select().where((Job.requester_id == session["user_id"] | Job.attendee_id == session["user_id"])
                             & Job.id == args["jobid"])

    return jsonify(attended=job.attended, completed=job.completed)


@app.route("/registeruser", methods=["POST"])
def register_user():
    if not requiredAttributes(userRegisterAttributes, request.get_json()):
        abort(404, attributesErrorMessage)

    requestjson = request.get_json()

    try:
        registeredUser = User.get(User.email == requestjson["email"])
        abort(404, "Email address already in use!")

    except User.DoesNotExist:
        password = requestjson['password'].encode('utf-8')
        encryptedpassword = bcrypt.hashpw(password, bcrypt.gensalt())

        user = User.create(email=requestjson["email"], name=requestjson["name"], password=encryptedpassword)
        user.save()

        auth_user(user)
        return success


@app.route('/login', methods=['POST'])
def login():
    if not requiredAttributes(loginAttributes, request.get_json()):
        abort(404, attributesErrorMessage)

    requestjson = request.get_json()

    try:
        user = User.get(email=requestjson['email'])
    except User.DoesNotExist:
        abort(404, "The username or password is incorrect")

    password = requestjson['password'].encode('utf-8')
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


def requiredAttributes(attributes, dictionary):
    for attribute in attributes:
        if attribute not in dictionary:
            return False

    return True


def get_object_or_404(model, *expressions):
    try:
        return model.get(*expressions)
    except model.DoesNotExist:
        abort(404, "Model does not exist!")


if __name__ == "__main__":
    app.run()