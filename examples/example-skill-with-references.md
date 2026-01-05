---
name: lambda-deployer
description: Deploy AWS Lambda functions with IAM roles. Trigger phrases: "deploy lambda", "create lambda function", "lambda deployment", "serverless deploy"
allowed-tools: ["Read", "Write", "Bash"]
---

# Lambda Deployer

Deploy AWS Lambda functions with proper IAM configuration and best practices.

## When to Use

- Deploying new Lambda functions
- Updating Lambda configurations
- Setting up Lambda permissions
- Troubleshooting Lambda deployments

## Core Instructions

1. **Validate function code**: Check handler exists, runtime compatibility, dependencies
2. **Create IAM role**: Use least-privilege principles (see references for templates)
3. **Package function**: Zip code with dependencies, exclude dev dependencies
4. **Deploy function**: Use AWS CLI or SAM, set appropriate timeout and memory
5. **Test deployment**: Invoke function, check CloudWatch logs

See [references/iam-patterns.md](references/iam-patterns.md) for IAM role templates.
See [examples/python-lambda.md](examples/python-lambda.md) for Python example.

## Quick Examples

### Example 1: Basic Python Lambda
**User**: "Deploy a Python Lambda that processes S3 events"
**Assistant**: Creates function with S3 trigger, proper IAM role, error handling

### Example 2: Node.js API Lambda
**User**: "Create Lambda for API Gateway endpoint"
**Assistant**: Sets up Lambda with API Gateway integration, CORS, validation

## Key Principles

- Always use least-privilege IAM roles
- Set appropriate timeout (default 3s often too low)
- Monitor Lambda logs in CloudWatch
- Test locally with SAM before deploying
- Use environment variables for configuration
