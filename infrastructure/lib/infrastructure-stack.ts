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
import { Duration, RemovalPolicy } from 'aws-cdk-lib';

export class InfrastructureStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // --- Database (Schema remains simple PK, but usage changes) ---
    const dynamoTable = new dynamodb.Table(this, 'ResumeCoachItemsTable', {
      tableName: 'ResumeCoachItems',
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
      timeToLiveAttribute: 'ttl',
    });

    // --- Backend Lambda (Update Environment Placeholder) ---
    const backendLambda = new lambda.Function(this, 'ResumeCoachBackendLambda', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../backend'), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage, // Match runtime
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
        // Add placeholder for OpenAI API Key.
        // IMPORTANT: The actual key will be set manually in the AWS Lambda Console
        // after deployment for security reasons. Do NOT commit your real key here.
        OPENAI_API_KEY: 'CONFIGURE_IN_LAMBDA_CONSOLE', // Placeholder value
      },
      timeout: Duration.seconds(60), // Increase timeout for potentially longer LLM calls
      memorySize: 256, // Increase memory slightly for LangChain/OpenAI libs if needed
      functionName: 'ResumeCoachBackendHandler',
      description: 'Handles ResumeCoach analysis, chat, and default item fetching.',
      architecture: lambda.Architecture.ARM_64,
    });

    // Grant Lambda permissions to access DynamoDB
    dynamoTable.grantReadWriteData(backendLambda); // Read needed for defaults, Write might be needed if adding defaults via API later

    // --- API Gateway (HTTP API Routes) ---
    const httpApi = new apigwv2.HttpApi(this, 'ResumeCoachHttpApi', {
      apiName: 'ResumeCoachHttpApi',
      description: 'HTTP API for ResumeCoach analysis, chat, and defaults.',
      corsPreflight: {
        allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key', 'X-Amz-Security-Token', 'X-Amz-User-Agent'],
        allowMethods: [
          apigwv2.CorsHttpMethod.OPTIONS, apigwv2.CorsHttpMethod.GET,
          apigwv2.CorsHttpMethod.POST, // Ensure POST is allowed for analyze/chat
          // PUT/DELETE might not be needed by frontend V2 unless managing defaults
          // apigwv2.CorsHttpMethod.PUT, apigwv2.CorsHttpMethod.DELETE,
        ],
        allowCredentials: false,
        allowOrigins: ['*'], // TODO: Restrict in production to CloudFront domain
        maxAge: Duration.days(1),
      },
    });

    // Create Lambda integration
    const lambdaIntegration = new HttpLambdaIntegration(
      'LambdaIntegration',
      backendLambda
    );

    // --- Define API routes ---

    // V1 Routes (Repurposed for Defaults)
    httpApi.addRoutes({
      path: '/items',
      methods: [apigwv2.HttpMethod.GET], // Only GET needed by frontend V2
      integration: lambdaIntegration,
    });
    httpApi.addRoutes({
      path: '/items/{id}',
      methods: [apigwv2.HttpMethod.GET], // Only GET needed by frontend V2
      integration: lambdaIntegration,
    });

    // V2 New Routes
    httpApi.addRoutes({
      path: '/analyze',
      methods: [apigwv2.HttpMethod.POST], // Analyze endpoint
      integration: lambdaIntegration,
    });
    httpApi.addRoutes({
      path: '/chat',
      methods: [apigwv2.HttpMethod.POST], // Chat endpoint
      integration: lambdaIntegration,
    });


    // --- Frontend Hosting (S3 + CloudFront) ---
    const frontendBucket = new s3.Bucket(this, 'ResumeCoachFrontendBucket', {
      bucketName: `resumecoach-frontend-${this.account}-${this.region}`,
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: true,
    });

    const originAccessIdentity = new cloudfront.OriginAccessIdentity(this, 'OAI', {
        comment: `OAI for ResumeCoach frontend bucket (us-west-2)`
    });
    frontendBucket.grantRead(originAccessIdentity);

    const distribution = new cloudfront.Distribution(this, 'ResumeCoachDistribution', {
      comment: 'CloudFront distribution for ResumeCoach frontend (Origin: us-west-2)',
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
    });

    // --- S3 Bucket Deployment (deploys frontend/dist) ---
    new s3deploy.BucketDeployment(this, 'DeployReactApp', {
      sources: [s3deploy.Source.asset(path.join(__dirname, '../../frontend/dist'))],
      destinationBucket: frontendBucket,
      distribution: distribution,
      distributionPaths: ['/*'],
      prune: true,
    });


    // --- Stack Outputs ---
    new cdk.CfnOutput(this, 'ApiGatewayUrl', {
      value: httpApi.apiEndpoint,
      description: 'The base URL of the API Gateway endpoint (us-west-2)',
      exportName: 'ResumeCoachApiEndpoint',
    });

    new cdk.CfnOutput(this, 'CloudFrontDomainName', {
      value: distribution.distributionDomainName,
      description: 'The domain name of the CloudFront distribution',
      exportName: 'ResumeCoachCloudFrontDomain',
    });

     new cdk.CfnOutput(this, 'FrontendBucketName', {
      value: frontendBucket.bucketName,
      description: 'The name of the S3 bucket hosting the frontend (us-west-2)',
    });
  }
}