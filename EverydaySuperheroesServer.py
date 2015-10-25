from functools import wraps
import json
import bcrypt as bcrypt
from flask import Flask, request, abort, session, jsonify
from datetime import datetime
from datamodels.Models import *

app = Flask(__name__)

jobAttributes = ["jobid", "userid"]
userIdAttribute = ["userid"]
locationAttributes = ["jobid", "latitude", "longitude"]
newJobAttributes = ["user","description", "latitude", "longitude", "name", "type"]
userRegisterAttributes = ["email", "name", "password"]

attributesErrorMessage = "Not all attributes supplied!"

success = json.dumps({'success':True}), 200, {'ContentType':'application/json'}


@app.route("/createjob", methods=["POST"])
def createjob():
    if not requiredAttributes(newJobAttributes, request.get_json()):
        abort(404, attributesErrorMessage)

    json = request.get_json()

    activejobs = Job.select().where((Job.requester_id == json["userid"]) & (not Job.completed))

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
                         requester=json["userid"],
                         type=json["type"]
                         )
    job.save()

    return jsonify(job=job.id)


@app.route("/updatelocation", methods=["POST"])
def update_location():
    if not requiredAttributes(locationAttributes, request.get_json()):
        abort(404, attributesErrorMessage)

    json = request.get_json()

    try:
        job = Job.get(Job.id == json["jobid"])

        try:
            previousLocation = UserLocation.get(UserLocation.user == job.attendee_id)
            previousLocation.latitude = json["latitude"]
            previousLocation.longitude = json["longitude"]
            previousLocation.save()
        except UserLocation.DoesNotExist:
            location = UserLocation.create(user=json["userid"],
                                           latitude=json["latitude"],
                                           longitude=json["longitude"],
                                           time=datetime.now())
            location.save()
    except Job.DoesNotExist:
        abort(404, "Job does not exist")

    return success


@app.route('/acceptjob', methods=['POST'])
def accept_job():
    if not requiredAttributes(jobAttributes, request.get_json()):
        abort(404, attributesErrorMessage)

    json = request.get_json()

    job = get_object_or_404(Job, Job.id == json['jobid'])
    if job.requester == json["userid"]:
        abort(404, "You cannot accept your own job!")

    try:
        acceptedJobs = Job.get(Job.attendee == json["userid"])
        abort(404, "User has already selected a job - cannot accept another")
    except Job.DoesNotExist:
        person = get_object_or_404(User, User.id == json["userid"])

        job.accepted = True
        job.attendee = person
        job.save()

    return success


@app.route("/getattendeelocation", methods=['GET'])
def get_attendee_location():
    if not requiredAttributes(jobAttributes, request.args):
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
    if not requiredAttributes(jobAttributes, request.args):
        abort(404, attributesErrorMessage)

    args = request.args

    try:
        job = Job.get(Job.id == args['jobid'])
    except Job.DoesNotExist:
        abort(404, "No such job exists!")

    return jsonify(jobId=job.id,description=job.description,type=job.type,longitude=job.longitude,latitude=job.latitude,
                   name=job.name,accepted=job.accepted,attendee=job.attendee_id,requester=job.requester_id)


@app.route("/getuserjob", methods=["GET"])
def get_user_job():
    if not requiredAttributes(userIdAttribute, request.args):
        abort(404, attributesErrorMessage)

    job = Job.select().where(Job.requester == request.args['userid'] & Job.completed == False).get()

    return jsonify(job=job.id)


@app.route("/isattended", methods=["GET"])
def isattended():
    if not requiredAttributes(jobAttributes, request.args):
        abort(404, attributesErrorMessage)

    args = request.args

    job = Job.select().where((Job.requester_id == args["userid"] | Job.attendee_id == args["userid"])
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