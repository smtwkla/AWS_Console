from flask import Flask, render_template, url_for, redirect, request, abort
import os
import boto3
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
    logging.info(f"Start {instance}")


def stop_ec2_instance(instance):
    logging.info(f"Shutdown {instance}")


def terminate_ec2_instance(instance):
    logging.info(f"Terminate {instance}")


app = Flask(__name__)


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
    return render_template('console.j2', instances=il)

@app.route("/action", methods=['GET'])
def do_action():
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
        start_ec2_instance(instance_id)
    elif action == Actions.SHUTDOWN:
        stop_ec2_instance(instance_id)
    elif action == Actions.TERMINATE:
        terminate_ec2_instance(instance_id)

    return redirect(url_for('index'))