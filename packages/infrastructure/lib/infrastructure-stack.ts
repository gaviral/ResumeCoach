// ResumeCoach/infrastructure/lib/infrastructure-stack.ts
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigwv2 from 'aws-cdk-lib/aws-apigatewayv2';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as path from 'path';
import { Duration, RemovalPolicy, Stack, StackProps } from 'aws-cdk-lib'; // Ensure Stack and StackProps are imported

// --- Import necessary modules for custom domain ---
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as targets from 'aws-cdk-lib/aws-route53-targets';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
// -------------------------------------------------

export class InfrastructureStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // --- Custom Domain Configuration ---
    const domainName = 'aviralgarg.com'; // Your root domain
    const subDomain = 'coach';
    const siteDomain = `${subDomain}.${domainName}`; // coach.aviralgarg.com
    // -----------------------------------

    // --- 1. Look up your existing Hosted Zone ---
    // Assumes aviralgarg.com is delegated to Route 53 in this AWS account
    const hostedZone = route53.HostedZone.fromLookup(this, 'ExistingHostedZone', {
      domainName: domainName,
    });
    // -------------------------------------------

    // --- 2. Create ACM Certificate (in us-east-1) ---
    // CloudFront requires certificates in us-east-1.
    // DnsValidatedCertificate handles creation and validation record setup.
    const siteCertificate = new acm.DnsValidatedCertificate(this, 'SiteCertificate', {
      domainName: siteDomain, // coach.aviralgarg.com
      hostedZone: hostedZone, // Route 53 zone for validation records
      region: 'us-east-1', // MUST be us-east-1 for CloudFront
    });
    // -------------------------------------------

    // --- Database (Items Table for Defaults) ---
    const itemsTable = new dynamodb.Table(this, 'ResumeCoachItemsTable', {
      tableName: 'ResumeCoachItems', // Keep original name for defaults
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY, // Suitable for dev/demo
      // timeToLiveAttribute: 'ttl', // TTL not strictly needed for defaults unless you want them to expire
    });

    // *** ADDED: Sessions Table ***
    const sessionsTable = new dynamodb.Table(this, 'ResumeCoachSessionsTable', {
        tableName: 'ResumeCoachSessions',
        partitionKey: { name: 'sessionId', type: dynamodb.AttributeType.STRING }, // Use sessionId as PK
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: RemovalPolicy.DESTROY, // Or RETAIN for production
        timeToLiveAttribute: 'ttl', // Add TTL for automatic session cleanup
    });
    // *** END ADDED ***

    // --- Backend Lambda (Update Environment & Permissions) ---
    const backendLambda = new lambda.Function(this, 'ResumeCoachBackendLambda', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../backend'), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c', `
            pip install -r requirements.txt -t /asset-output &&
            cp -au . /asset-output
            `
          ],
        },
      }),
      environment: {
        // *** UPDATED: Rename ITEMS table env var ***
        ITEMS_TABLE_NAME: itemsTable.tableName,
        // *** ADDED: Sessions Table Env Var ***
        SESSIONS_TABLE_NAME: sessionsTable.tableName,
        // *** END ADDED ***
        LOG_LEVEL: 'INFO',
        OPENAI_API_KEY: 'CONFIGURE_IN_LAMBDA_CONSOLE', // Remember to set manually
      },
      timeout: Duration.seconds(60), // Keep timeout reasonable for LLM calls + DDB I/O
      memorySize: 256, // May need increase depending on memory usage with state
      functionName: 'ResumeCoachBackendHandler',
      description: 'Handles ResumeCoach analysis, chat, defaults, and session state.', // Updated description
      architecture: lambda.Architecture.ARM_64,
    });
    // Grant permissions to both tables
    itemsTable.grantReadData(backendLambda); // Only needs read for defaults
    // *** ADDED: Grant R/W to Sessions Table ***
    sessionsTable.grantReadWriteData(backendLambda);
    // *** END ADDED ***

    // --- API Gateway (No changes needed here for session logic) ---
    const httpApi = new apigwv2.HttpApi(this, 'ResumeCoachHttpApi', {
      apiName: 'ResumeCoachHttpApi',
      description: 'HTTP API for ResumeCoach analysis, chat, and defaults.',
      corsPreflight: {
        allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key', 'X-Amz-Security-Token', 'X-Amz-User-Agent', 'X-Session-Id'], // Added X-Session-Id potentially
        allowMethods: [
          apigwv2.CorsHttpMethod.OPTIONS, apigwv2.CorsHttpMethod.GET,
          apigwv2.CorsHttpMethod.POST,
        ],
        allowCredentials: false,
        // IMPORTANT: For production, restrict this to your custom domain
        // allowOrigins: [`https://${siteDomain}`],
        allowOrigins: ['*'], // Keep as '*' for now, restrict later if needed
        maxAge: Duration.days(1),
        // *** ADDED: Expose Session ID Header ***
        exposeHeaders: ['X-Session-Id'],
        // *** END ADDED ***
      },
    });
    const lambdaIntegration = new HttpLambdaIntegration('LambdaIntegration', backendLambda);
    // API Routes (No changes)
    httpApi.addRoutes({ path: '/items', methods: [apigwv2.HttpMethod.GET], integration: lambdaIntegration });
    httpApi.addRoutes({ path: '/items/{id}', methods: [apigwv2.HttpMethod.GET], integration: lambdaIntegration });
    httpApi.addRoutes({ path: '/analyze', methods: [apigwv2.HttpMethod.POST], integration: lambdaIntegration });
    httpApi.addRoutes({ path: '/chat', methods: [apigwv2.HttpMethod.POST], integration: lambdaIntegration });

    // --- Frontend Hosting (S3 Bucket - No changes) ---
    const frontendBucket = new s3.Bucket(this, 'ResumeCoachFrontendBucket', {
      bucketName: `resumecoach-frontend-${this.account}-${this.region}`, // Unique bucket name
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: true, // Good practice
    });
    const originAccessIdentity = new cloudfront.OriginAccessIdentity(this, 'OAI', {
        comment: `OAI for ${siteDomain} frontend bucket`
    });
    frontendBucket.grantRead(originAccessIdentity);

    // --- CloudFront Distribution (No changes needed here for session logic) ---
    const distribution = new cloudfront.Distribution(this, 'ResumeCoachDistribution', {
      comment: `CloudFront distribution for ${siteDomain}`,
      defaultBehavior: {
        origin: new origins.S3Origin(frontendBucket, { originAccessIdentity }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        cachedMethods: cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
        compress: true,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      defaultRootObject: 'index.html',
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
       errorResponses:[
         { httpStatus: 403, responseHttpStatus: 200, responsePagePath: '/index.html', ttl: Duration.minutes(0) },
         { httpStatus: 404, responseHttpStatus: 200, responsePagePath: '/index.html', ttl: Duration.minutes(0) }
       ],
       minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
       domainNames: [siteDomain],
       certificate: siteCertificate,
    });

    // --- S3 Bucket Deployment (No changes) ---
    new s3deploy.BucketDeployment(this, 'DeployReactApp', {
      sources: [s3deploy.Source.asset(path.join(__dirname, '../../frontend/dist'))],
      destinationBucket: frontendBucket,
      distribution: distribution,
      distributionPaths: ['/*'],
      prune: true,
    });

    // --- Route 53 Alias Record (No changes) ---
    new route53.ARecord(this, 'SiteAliasRecord', {
      recordName: siteDomain,
      zone: hostedZone,
      target: route53.RecordTarget.fromAlias(new targets.CloudFrontTarget(distribution)),
    });

    // --- Stack Outputs ---
    new cdk.CfnOutput(this, 'ApiGatewayUrl', {
      value: httpApi.apiEndpoint,
      description: 'The base URL of the API Gateway endpoint (us-west-2)',
    });
    new cdk.CfnOutput(this, 'CloudFrontDomainNameOutput', {
        value: distribution.distributionDomainName,
        description: 'The *.cloudfront.net domain name of the distribution',
    });
     new cdk.CfnOutput(this, 'FrontendBucketName', {
      value: frontendBucket.bucketName,
      description: 'The name of the S3 bucket hosting the frontend',
    });
    new cdk.CfnOutput(this, 'CustomDomainUrlOutput', {
        value: `https://${siteDomain}`,
        description: 'The custom domain URL for the application',
    });
    // *** ADDED: Output Sessions Table Name ***
    new cdk.CfnOutput(this, 'SessionsTableNameOutput', {
        value: sessionsTable.tableName,
        description: 'Name of the DynamoDB table storing session state',
    });
    // *** END ADDED ***
  }
}