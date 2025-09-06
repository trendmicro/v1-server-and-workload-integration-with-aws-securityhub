import boto3

securityhub = boto3.client('securityhub')

findings = [
    {
        "SchemaVersion": "2018-10-08",
        "Id": "arn:aws:securityhub:us-east-1:442042542614:finding/custom/example-finding-id-001",
        "ProductArn": "arn:aws:securityhub:us-east-1:442042542614:product/custom/my-security-tool",
        "GeneratorId": "my-security-tool-detector-001",
        "AwsAccountId": "442042542614",
        "CreatedAt": "2025-09-05T10:00:00Z",
        "UpdatedAt": "2025-09-05T10:00:00Z",
        "Severity": {
            "Product": 60,
            "Normalized": 60
        },
        "Title": "Custom finding: Unencrypted S3 bucket detected",
        "Description": "An S3 bucket named 'my-unencrypted-bucket' was found without server-side encryption enabled.",
        "Resources": [
            {
            "Type": "AwsEc2Instance",
            "Id": "i-05c41c2994791f0fe",
            "Partition": "aws",
            "Region": "us-east-1"
            },
            {
            "Type": "Other",
            "Id": "file:///home/ec2-user/MalwareSourceCode/Linux/Backdoors/Backdoor.Linux.Rootin.a",
            "Details": {
                "Other": {
                "FileSha1": "1BE086157DC97CDD63C1C8CDA095F090F1BC600C",
                "ProcessImagePath": "/usr/bin/git",
                "ProcessPid": "48363"
                }
            }
            }
        ],
        "Compliance": {
            "Status": "FAILED"
        },
        "Workflow": {
            "Status": "NEW"
        },
        "RecordState": "ACTIVE"
    }
]
response = securityhub.batch_import_findings(Findings=findings)
print(response)