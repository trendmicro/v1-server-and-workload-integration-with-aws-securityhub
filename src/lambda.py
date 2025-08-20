import datetime
import json
import os
import boto3
from botocore.retries.standard import RetryPolicy

def generate_finding_title(title):
    return "Trend Micro: {}".format(title)

def verify_required_properties(ws_event):
    result = True
    required_properties = [
        'HostOwnerID', 
        'HostInstanceID', 
        'TenantID', 
        'EventID', 
        "EventType", 
        'LogDate', 
        'HostAssetValue', 
        'HostGroupID', 
        'HostGroupName', 
        'HostID', 
        'Hostname', 
        'HostSecurityPolicyID', 
        'HostSecurityPolicyName'
        ]
    for prop in required_properties:
        if not prop in ws_event:
            result = False
            print(result)
            return result

def select_asff_eventType(EventType, types):
    if(EventType == 'PacketLog'):
        types.append("Unusual Behaviors/Network Flow")
    elif(EventType == 'IntegrityEvent'):
        types.append("Unusual Behaviors/VM")
    elif(EventType == 'LogInspectionEvent' or EventType == 'PayloadLog'):
        types.append("Unusual Behaviors/VM")
        types.append("Unusual Behaviors/Application")
    elif(EventType == 'WebReputationEvent' or EventType == 'AntiMalwareEvent'):
        types.append("TPPs/Execution")
    return types

def antimalwareStatusAction(action):
    state = ""
    if action == "Cleaned" or action == "Deleted":
        state = "REMOVED"
    elif action == "Quarantined" or action == "Access Denied":
        state = "OBSERVED"
    else:
        state = "REMOVAL_FAILED"
    return state
        
def addAdditionalInformation(Event, finding):
    if 'SystemEvent' in Event["EventType"]:
        pass
    if "PacketLog" in Event["EventType"]:
        finding['Severity']['Product'] = 0
        finding['Severity']['Normalized'] = int(20)
        select_asff_eventType(Event["EventType"], finding["Types"])
        finding['Title'] = "Trend Micro: Repeated attempted network connection on instance {}".format(Event['HostInstanceID'])
    if "PayloadLog" in Event["EventType"]:
        if 'Severity' in Event:
            finding['Severity']['Product'] = int(Event['Severity'])
            finding['Severity']['Normalized'] = int(int(Event['Severity']) * 17.5)
        select_asff_eventType(Event["EventType"], finding["Types"])
        finding['Title'] = "Trend Micro: Rule [{}] triggered".format(Event['Reason'])
    if "AntiMalwareEvent" in Event["EventType"]:
        finding['Malware'] = [
            {
                "Name": Event['MalwareName'],
                "Path": Event['InfectedFilePath'],
                "State": antimalwareStatusAction(Event['ScanResultString']),
                }
            ]
        if Event['ScanResultString'] == "Cleaned" or Event['ScanResultString'] == "Deleted":
            finding['Severity']['Label'] = "INFORMATIONAL"
        elif Event['ScanResultString'] == "Quarantined":
            finding['Severity']['Label'] = "LOW"
        else: 
            finding['Severity']['Label'] = "MEDIUM"
        select_asff_eventType(Event["EventType"], finding["Types"])
        finding['Title'] = "Malware [{}] detected".format(Event['MalwareName'])
    if "WebReputationEvent" in Event["EventType"]:
        if 'Risk' in Event:
            finding['Severity']['Product'] = int(Event['Risk'])
            finding['Severity']['Normalized'] = int(int(Event['Risk']) * 17.5)
        select_asff_eventType(Event["EventType"], finding["Types"])
        finding['Title'] = "High risk web request to IP [{}]".format(Event['TargetIP'])
    if "IntegrityEvent" in Event["EventType"]:
        if 'Severity' in Event:
            finding['Severity']['Product'] = int(Event['Severity'])
            finding['Severity']['Normalized'] = int(int(Event['Severity']) * 17.5)
        select_asff_eventType(Event["EventType"], finding["Types"])
        finding['Title'] = "Unexpected change to object [{}]".format(Event['Key'])
    if "LogInspectionEvent" in Event["EventType"]:
        if 'OSSEC_Level' in Event:
            finding['Severity']['Product'] = int(Event['OSSEC_Level'])
            if int(Event['OSSEC_Level']) >= 13:
                finding['Severity']['Normalized'] = int(int(Event['OSSEC_Level']) * 6.5)
            else:
                finding['Severity']['Normalized'] = int(int(Event['OSSEC_Level']) * 5)
        select_asff_eventType(Event["EventType"], finding["Types"])
        finding['Title'] = Event['OSSEC_Description']
    if "AppControlEvent" in Event["EventType"]:
        Process = {
            "Name": Event['FileName'],
            "Path": Event['Path'],
            "Pid": Event['ProcessID'],
        }
        finding["Process"] = Process
        if(Event['Operation'] <=1):
            finding['Severity']['Label'] = "LOW"
            finding['ProductFields']['trend-micro:SHA256'] = Event['SHA256'] if 'SHA256' in Event else ''
            finding['Title'] = "User {} performs allowed Execution of Unrecognized Software".format(Event['UserName'])
        else:
            finding['Severity']['Label'] = "INFORMATIONAL"
            finding['ProductFields']['trend-micro:SHA256'] = Event['SHA256'] if 'SHA256' in Event else ''
            finding['Title'] = "User {} tried performs Execution but Agent taking action of Block".format(Event['UserName'])
        finding['Types'].append("Unusual Behaviors/Application")
        finding['Title'] = "User {} performs allowed Execution of Unrecognized Software".format(Event['UserName'])
    if 'Tags' in Event:
        finding['ProductFields']['trend-micro:Tags'] = Event['Tags']
    if 'OriginString' in Event:
        finding['ProductFields']['trend-micro:Origin'] = Event['OriginString']
    return finding

def workload_security_event_to_asff(ws_event, region, awsaccountid):
    event_types = {
        'SystemEvent': 'system',
        'PacketLog': 'firewall',
        'PayloadLog': 'intrusionprevention',
        'AntiMalwareEvent': 'antimalware',
        'WebReputationEvent': 'webreputation',
        'IntegrityEvent': 'integrity',
        'LogInspectionEvent': 'log',
        'AppControlEvent': 'applicationcontrol'
        }

    finding = {
        "SchemaVersion": "2018-10-08",
        "Id": ws_event["UniqueID"],
        "ProductArn": f"arn:aws:securityhub:{region}:{awsaccountid}:product/{awsaccountid}/default",
        "GeneratorId": "trend-micro-workload-security-{}".format(event_types[ws_event["EventType"]]),
        "AwsAccountId": awsaccountid,
        "Types": [
            ],
        "CreatedAt": ws_event['LogDate'],
        "UpdatedAt": datetime.datetime.utcnow().isoformat("T") + "Z",
        "Severity": {
            "Product": 0,
            "Normalized": 0
            },
        "ProductFields": {
            'ProviderName': "Trend Micro Cloud One",
            "ProviderVersion": "20",
            'trend-micro:TenantName': ws_event['TenantName'] if 'TenantName' in ws_event else '',
            'trend-micro:TenantID': str(ws_event['TenantID']) if 'TenantID' in ws_event else '',
            'trend-micro:EventID': str(ws_event['EventID']) if 'EventID' in ws_event else '',
            'trend-micro:HostAssetValue': str(ws_event['HostAssetValue']) if 'HostAssetValue' in ws_event else '',
            'trend-micro:HostGroupID': str(ws_event['HostGroupID']) if 'HostGroupID' in ws_event else '',
            'trend-micro:HostGroupName': ws_event['HostGroupName'] if 'HostGroupName' in ws_event else '',
            'trend-micro:HostID': str(ws_event['HostID']) if 'HostID' in ws_event else '',
            'trend-micro:HostInstanceID': str(ws_event['HostInstanceID']) if 'HostInstanceID' in ws_event else '',
            'trend-micro:Hostname': ws_event['Hostname'] if 'Hostname' in ws_event else '',
            'trend-micro:HostSecurityPolicyID': str(ws_event['HostSecurityPolicyID']) if 'HostSecurityPolicyID' in ws_event else '',
            'trend-micro:HostSecurityPolicyName': ws_event['HostSecurityPolicyName'] if 'HostSecurityPolicyName' in ws_event else '',
            'trend-micro:Origin' : ws_event['OriginString'] if 'OriginString' in ws_event else '',
            'trend-micro:EventType' : ws_event['EventType'] if 'EventType' in ws_event else ''
            },
        "Description": "Workload Security Event, type: {}".format(event_types[ws_event["EventType"]]),
        "Resources": [
            {
                "Type": "AwsEc2Instance",
                "Id":  ws_event['HostInstanceID'] if 'HostInstanceID' in ws_event else ''
                }
            ],
        "Title": "Cloud One Workload Security push the following event type: {} for HostName: {}".format(event_types[ws_event["EventType"]], ws_event['Hostname'] if 'Hostname' in ws_event else ''),
        }
    converted_event = addAdditionalInformation(ws_event, finding)
    return converted_event

def lambda_handler(event, context):
    total_events = 0
    saved_events = 0
    securityhub = boto3.client("securityhub")
    region = boto3.session.Session().region_name
    awsaccountid = boto3.client("sts").get_caller_identity()["Account"]
    if 'Records' in event:
        for e in event['Records']:
            if 'EventSource' in e and e['EventSource'] == 'aws:sns':
                print("Amazon SNS message received")
                if 'Sns' in e:
                    ws_events = None
                    try:
                        ws_events = json.loads(e['Sns']['Message'])
                    except Exception as err:
                        print("Could not extract the Workload Security event(s) from the SNS message. Threw exception:\n{}".format(err))
                    aff_events = []
                    if ws_events:
                        print("Found {} Workload Security events...processing".format(len(ws_events)))
                        for ws_event in ws_events:
                            """if('HostInstanceID' in ws_event):"""
                            total_events += 1
                            if not ws_event["EventType"] == 'SystemEvent' or verify_required_properties(ws_event):
                                aff_event = workload_security_event_to_asff(ws_event=ws_event, region=region, awsaccountid=awsaccountid)
                                aff_events.append(aff_event)
                                print(aff_event)
                            else: print("Specified event does not have the required properties to properly process it")
                    if len(aff_events) > 0:
                        response = securityhub.batch_import_findings(Findings=aff_events)
                        print(json.dumps(response))
        return {
            'total_events': total_events,
            'saved_events': saved_events,
            'issues': (total_events - saved_events)
            }
