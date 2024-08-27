from warnings import catch_warnings


from flask import Flask, render_template, url_for, redirect, request, abort, session
import os
import boto3
from botocore.exceptions import ClientError

from typing import List
import pprint
import logging


from Instance import Instance, ActionsOnInstances
from Instance import ActionsOnInstances as Actions, InstanceStates as States, ActionStrings
import settings


aws_config = {}
client = None


def load_aws_config():
    global aws_config
    aws_config['region_name'] = os.environ['AWS_REGION']
    aws_config['access_key'] = os.environ['ACCESS_KEY']


def connect_to_boto():
    global client
    client = boto3.client('ec2', region_name=aws_config['region_name'])


def load_controlled_instance_list():
    instance_list:List[Instance] = []

    reservations = client.describe_instances( Filters=[
                                    {'Name': 'tag-key', 'Values': [settings.EC2_TAG_NAME]}
                                ])['Reservations']
    instances = [y for x in reservations for y in  x['Instances']]
    for i in instances:
        cur_inst = Instance()
        cur_inst.InstanceId = i['InstanceId']
        cur_inst.InstanceType = i["InstanceType"]

        for t in i['Tags']:
            if t['Key'] == 'Name':
                cur_inst.InstanceName = t['Value']
            if t['Key'] == settings.EC2_TAG_NAME:
                cur_inst.PermissionString = t['Value']
        instance_list.append(cur_inst)
    return instance_list


def load_instance_status(il):
    to_check = [x.InstanceId for x in il]
    status_resp = client.describe_instance_status(InstanceIds=to_check, IncludeAllInstances=True)
    status = status_resp['InstanceStatuses']
    for instance in status:
        for i in il:
            if i.InstanceId == instance["InstanceId"]:
                i.InstanceState = instance["InstanceState"]["Name"]
                i.InstanceStateCode = instance["InstanceState"]["Code"]


def load_instance_allowed_actions(il):

    for i in il:
        allowed = ""
        if i.InstanceStateCode == States.STOPPED.value:
            allowed = allowed + Actions.START
            allowed = allowed + Actions.TERMINATE

        if i.InstanceStateCode == States.RUNNING.value:
            allowed = allowed + Actions.SHUTDOWN

        i.ApplicableActions = allowed


def start_ec2_instance(instance):
    msg = f"Starting {instance}..."
    logging.info(msg)
    try:
        response = client.start_instances(InstanceIds=[instance.InstanceId])
    except ClientError as e:
        resp_text = e.response['Error']['Message']
        return False, resp_text
    return True, msg


def stop_ec2_instance(instance):
    logging.info(msg:=f"Shutting down {instance}...")
    try:
        response = client.stop_instances(InstanceIds=[instance.InstanceId])
    except ClientError as e:
        resp_text = e.response['Error']['Message']
        return False, resp_text
    return True, msg


def terminate_ec2_instance(instance):
    logging.info(msg := f"Terminating {instance}...")
    try:
        response = client.terminate_instances(InstanceIds=[instance.InstanceId])
    except ClientError as e:
        resp_text = e.response['Error']['Message']
        return False, resp_text
    return True, msg


app = Flask(__name__)
app.secret_key = os.environ['FLASK_KEY']


def boot_strap():
    load_aws_config()
    connect_to_boto()
    il = load_controlled_instance_list()
    load_instance_status(il)
    load_instance_allowed_actions(il)
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    return il


@app.route("/")
def index():
    il = boot_strap()
    msg_info = session.pop('msg_info', default=None)
    msg_alert = session.pop('msg_alert', default=None)

    return render_template('console.j2', instances=il, msg_info=msg_info, msg_alert=msg_alert)

@app.route("/action", methods=['GET'])
def do_action():
    if session.get('user') is None:
        return redirect(url_for('do_login'))

    session.pop('msg_info', None)
    session.pop('msg_alert', None)
    il = boot_strap()
    action_str = request.args.get('action', '').capitalize()
    instance_id = request.args.get('id', '')
    logging.debug(f"action_str: {action_str} on {instance_id}")

    instance = None
    for i in il:
        if i.InstanceId == instance_id:
            instance = i
            break
    if not instance:
        abort(400)

    action = ActionStrings.get(action_str, None)
    if not action:
        abort(400)

    if not instance.check_permission(action):
        abort(405)

    if action == Actions.START:
        result, msg = start_ec2_instance(instance)
    elif action == Actions.SHUTDOWN:
        result, msg = stop_ec2_instance(instance)
    elif action == Actions.TERMINATE:
        result, msg = terminate_ec2_instance(instance)


    session['msg_info'] = msg if result else None
    session['msg_alert'] = msg if not result else None

    return redirect(url_for('index'))


@app.route("/login", methods=['GET', 'POST'])
def do_login():
    if request.method == 'GET':
        login_alert=session.pop('login_alert', None)
        return render_template('login.j2',login_alert=login_alert)
    elif request.method == 'POST':
        username = request.form.get('user')
        password = request.form.get('pwd')
        if password == os.environ.get("PASSWORD"):
            session['user'] = username
            session.pop('login_alert', None)
            return redirect(url_for('index'))
        else:
            session.pop('user', None)
            session['login_alert'] = "Invalid Login!"
            return redirect(url_for('do_login'))


@app.route("/logout", methods=['GET'])
def do_logout():
    session.pop('user', None)
    return redirect(url_for('index'))