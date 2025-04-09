#!/usr/bin/env node
// ResumeCoach/infrastructure/bin/infrastructure.ts
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { InfrastructureStack } from '../lib/infrastructure-stack';

const app = new cdk.App();
new InfrastructureStack(app, 'ResumeCoachFoundationStack', {
  /* If you don't specify 'env', this stack will be environment-agnostic.
   * Account/Region-dependent features and context lookups will not work,
   * but a single synthesized template can be deployed anywhere. */

  /* **MODIFICATION START** */
  /* Uncomment the next line to specialize this stack for the AWS Account
   * and Region that are implied by the current CLI configuration. */
  // env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION },

  /* Specify the AWS Account and Region directly for us-west-2 deployment. */
  /* Uses the account configured in your AWS CLI/environment */
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'us-west-2' // Explicitly set region to us-west-2
  },
  /* **MODIFICATION END** */

  /* Uncomment the next line if you know exactly what Account and Region you
   * want to deploy the stack to. */
  // env: { account: '123456789012', region: 'us-west-2' },

  /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
  description: 'Foundation stack for ResumeCoach application (CDK + Python + React) - Deployed to us-west-2', // Updated description
  tags: { // Optional: Add tags to resources
      Project: 'ResumeCoach',
      Environment: 'Development',
      Region: 'us-west-2' // Add region tag
  }
});