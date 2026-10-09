"""The deployed stack's resources, looked up at run time so nothing is typed in or stored."""

import boto3

STACK, REGION = "nirmaldhara", "ap-south-1"


def session():
    return boto3.Session(region_name=REGION)


def resources(aws=None):
    """{logical name: physical id} for every resource in the stack."""
    client = (aws or session()).client("cloudformation")
    out, token = {}, None
    while True:
        page = client.list_stack_resources(StackName=STACK, **({"NextToken": token} if token else {}))
        out.update({r["LogicalResourceId"]: r["PhysicalResourceId"] for r in page["StackResourceSummaries"]})
        token = page.get("NextToken")
        if not token:
            return out


def outputs(aws=None):
    stacks = (aws or session()).client("cloudformation").describe_stacks(StackName=STACK)["Stacks"]
    return {o["OutputKey"]: o["OutputValue"] for o in stacks[0].get("Outputs", [])}
