import pprint

from flask import Flask, render_template
import os
import boto3
from botocore.exceptions import ClientError
from werkzeug.serving import connection_dropped_errors

from Instance import Instance
from typing import List

aws_config = {}
client = None
instance_list:List[Instance] = []


def load_aws_config():
    global aws_config
    aws_config['region_name'] = os.environ['AWS_REGION']
    aws_config['access_key'] = os.environ['ACCESS_KEY']


def connect_to_boto():
    global client
    client = boto3.client('ec2', region_name=aws_config['region_name'])


def load_controlled_instance_list():
    global instance_list

    reservations = client.describe_instances( Filters=[
                                    {'Name': 'tag-key', 'Values': ['AWS_Web_Console_Controlled']}
                                ])['Reservations']
    instances = [y for x in reservations for y in  x['Instances']]
    for i in instances:
        cur_inst = Instance()
        cur_inst.InstanceId = i['InstanceId']
        cur_inst.InstanceType = i["InstanceType"]
        for t in i['Tags']:
            if t['Key'] == 'Name':
                cur_inst.InstanceName = t['Value']
        instance_list.append(cur_inst)



def load_instance_status():
    status_resp = client.describe_instance_status(InstanceIds=[x.InstanceId for x in instance_list])
    status = status_resp['InstanceStatuses']
    for instance in status:
        for i in instance_list:
            if i.InstanceId == instance["InstanceId"]:
                i.InstanceState = instance["InstanceState"]["Name"]
                i.InstanceStateCode = instance["InstanceState"]["Code"]


def start_ec2_instance(instance):
    pass


def stop_ec2_instance(instance):
    pass


app = Flask(__name__)

@app.route("/")
def hello_world():
    load_aws_config()
    connect_to_boto()
    load_controlled_instance_list()
    load_instance_status()
    return render_template('console.html', instances=instance_list)
