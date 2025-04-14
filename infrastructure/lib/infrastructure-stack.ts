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

    // --- Database (No changes) ---
    const dynamoTable = new dynamodb.Table(this, 'ResumeCoachItemsTable', {
      tableName: 'ResumeCoachItems',
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
      timeToLiveAttribute: 'ttl',
    });

    // --- Backend Lambda (No changes related to domain) ---
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
        TABLE_NAME: dynamoTable.tableName,
        LOG_LEVEL: 'INFO',
        OPENAI_API_KEY: 'CONFIGURE_IN_LAMBDA_CONSOLE', // Remember to set manually
      },
      timeout: Duration.seconds(60),
      memorySize: 256,
      functionName: 'ResumeCoachBackendHandler',
      description: 'Handles ResumeCoach analysis, chat, and default item fetching.',
      architecture: lambda.Architecture.ARM_64,
    });
    dynamoTable.grantReadWriteData(backendLambda);

    // --- API Gateway (No changes related to domain) ---
    const httpApi = new apigwv2.HttpApi(this, 'ResumeCoachHttpApi', {
      apiName: 'ResumeCoachHttpApi',
      description: 'HTTP API for ResumeCoach analysis, chat, and defaults.',
      corsPreflight: {
        allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key', 'X-Amz-Security-Token', 'X-Amz-User-Agent'],
        allowMethods: [
          apigwv2.CorsHttpMethod.OPTIONS, apigwv2.CorsHttpMethod.GET,
          apigwv2.CorsHttpMethod.POST,
        ],
        allowCredentials: false,
        // IMPORTANT: For production, restrict this to your custom domain
        // allowOrigins: [`https://${siteDomain}`],
        allowOrigins: ['*'], // Keep as '*' for now, restrict later if needed
        maxAge: Duration.days(1),
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

    // --- 3. Update CloudFront Distribution ---
    const distribution = new cloudfront.Distribution(this, 'ResumeCoachDistribution', {
      comment: `CloudFront distribution for ${siteDomain}`, // Updated comment
      defaultBehavior: {
        origin: new origins.S3Origin(frontendBucket, { originAccessIdentity }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        cachedMethods: cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
        compress: true,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      defaultRootObject: 'index.html',
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100, // Use cheapest edge locations
       errorResponses:[
         { httpStatus: 403, responseHttpStatus: 200, responsePagePath: '/index.html', ttl: Duration.minutes(0) },
         { httpStatus: 404, responseHttpStatus: 200, responsePagePath: '/index.html', ttl: Duration.minutes(0) }
       ],
       minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021, // Recommended security policy

       // --- Add Custom Domain Configuration ---
       domainNames: [siteDomain], // The custom domain
       certificate: siteCertificate, // Reference the ACM certificate in us-east-1
       // ---------------------------------------
    });
    // -------------------------------------------

    // --- S3 Bucket Deployment (No changes) ---
    // Deploys contents of frontend/dist to the S3 bucket
    new s3deploy.BucketDeployment(this, 'DeployReactApp', {
      sources: [s3deploy.Source.asset(path.join(__dirname, '../../frontend/dist'))],
      destinationBucket: frontendBucket,
      distribution: distribution, // Invalidate CloudFront cache on deployment
      distributionPaths: ['/*'], // Invalidate all paths
      prune: true, // Remove old files
    });

    // --- 4. Create Route 53 Alias Record ---
    // Points coach.aviralgarg.com to the CloudFront distribution
    new route53.ARecord(this, 'SiteAliasRecord', {
      recordName: siteDomain, // coach.aviralgarg.com
      zone: hostedZone,       // Your aviralgarg.com hosted zone
      target: route53.RecordTarget.fromAlias(new targets.CloudFrontTarget(distribution)),
    });
    // AAAA record for IPv6 is implicitly handled by CloudFrontTarget
    // -------------------------------------------

    // --- Stack Outputs ---
    new cdk.CfnOutput(this, 'ApiGatewayUrl', {
      value: httpApi.apiEndpoint,
      description: 'The base URL of the API Gateway endpoint (us-west-2)',
      // exportName: 'ResumeCoachApiEndpoint', // Optional export
    });
    new cdk.CfnOutput(this, 'CloudFrontDomainNameOutput', { // Renamed original output
        value: distribution.distributionDomainName,
        description: 'The *.cloudfront.net domain name of the distribution',
    });
     new cdk.CfnOutput(this, 'FrontendBucketName', {
      value: frontendBucket.bucketName,
      description: 'The name of the S3 bucket hosting the frontend',
    });
    // --- Add Custom Domain Output ---
    new cdk.CfnOutput(this, 'CustomDomainUrlOutput', { // New output
        value: `https://${siteDomain}`,
        description: 'The custom domain URL for the application',
    });
    // --------------------------------
  }
}