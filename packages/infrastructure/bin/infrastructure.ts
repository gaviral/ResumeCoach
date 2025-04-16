#!/usr/bin/env node
// ResumeCoach/infrastructure/bin/infrastructure.ts
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { InfrastructureStack } from '../lib/infrastructure-stack';

const app = new cdk.App();

// Define domain variables used in description/tags if desired
const domainName = 'aviralgarg.com';
const subDomain = 'coach';
const siteDomain = `${subDomain}.${domainName}`;

new InfrastructureStack(app, 'ResumeCoachFoundationStack', { // Use your consistent stack name
  /* Set the environment for the stack deployment */
  env: {
    // Use the account and region from your AWS CLI configuration
    // Ensure your CLI is configured for the correct account
    account: process.env.CDK_DEFAULT_ACCOUNT,
    // Deploy the stack resources (Lambda, DynamoDB, S3, etc.) to us-west-2
    region: 'us-west-2'
  },
  /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */

  description: `Stack for Resume Coach application (${siteDomain}), deployed to us-west-2`, // Updated description
  tags: { // Optional: Add tags to resources
      Project: 'ResumeCoach',
      Environment: 'Development',
      Domain: siteDomain // Add domain tag if useful
  }
});