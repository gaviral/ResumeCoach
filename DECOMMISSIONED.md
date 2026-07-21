# Resume Coach — Decommissioned

**Date:** 2026-07-20  
**Domain:** `coach.aviralgarg.com`  
**Stack:** `ResumeCoachFoundationStack` (`us-west-2`)  
**Frozen deployable SHA:** `2f4323d0775bb913bd265ba3d3be712b8bd138d1`

## Decision

This project is retired. Automatic AWS deployment is disabled. No data export
was performed: the four DynamoDB demo records, empty sessions table, generated
site-bucket versions, and Lambda logs will be permanently deleted during AWS
teardown. There is no Cognito login state.

## Recreation limits

Checkout the frozen SHA above and redeploy with CDK only if a deliberate
restore is approved. Recreation requires a new OpenAI SSM parameter and a new
API URL. The four demo item contents are not in Git and cannot be restored
without a prior export.

## Protected dependencies

Do not touch `aviralgarg.com` / `www`, RAF (including Cognito/data/secrets/push),
Max production, the Route 53 hosted zone, CDK/SST bootstraps, unrelated AWS
resources, or any underlying IAM access key.
