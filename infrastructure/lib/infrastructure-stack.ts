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
      tableName: 'ResumeCoachItems', // Reusing the table name from V1
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING }, // PK for documents, analyses, etc.
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
      timeToLiveAttribute: 'ttl',
    });

    // --- Backend Lambda (Updated for V2) ---
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
        // ** IMPORTANT: OPENAI_API_KEY is NOT set here for security. **
        // ** It must be added manually via the AWS Lambda Console after deployment. **
        // OPENAI_API_KEY: 'dummy-value-to-be-replaced', // Avoid even dummy values if possible
      },
      // ** Increased timeout and memory for LLM calls **
      timeout: Duration.seconds(30), // Increased from 15s
      memorySize: 512, // Increased from 128MB, adjust as needed
      functionName: 'ResumeCoachBackendHandlerV2', // Optional: Update name
      description: 'Handles analysis, chat, and document CRUD for ResumeCoach V2',
      architecture: lambda.Architecture.ARM_64,
    });

    // Grant Lambda permissions to access the DynamoDB table
    dynamoTable.grantReadWriteData(backendLambda);
    // ** NOTE: No extra permissions needed for env vars. If using Secrets Manager, add permissions here. **

    // --- API Gateway (HTTP API - Updated Routes for V2) ---
    const httpApi = new apigwv2.HttpApi(this, 'ResumeCoachHttpApi', {
      apiName: 'ResumeCoachHttpApi', // Keep the same API name
      description: 'HTTP API for ResumeCoach V2',
      corsPreflight: {
        allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key', 'X-Amz-Security-Token', 'X-Amz-User-Agent'],
        allowMethods: [
          apigwv2.CorsHttpMethod.OPTIONS, apigwv2.CorsHttpMethod.GET,
          apigwv2.CorsHttpMethod.POST, // Keep POST
          // apigwv2.CorsHttpMethod.PUT, // Remove if PUT /documents/{id} not implemented yet
          apigwv2.CorsHttpMethod.DELETE, // Keep DELETE
        ],
        allowCredentials: false, // Keep false with allowOrigins: '*'
        allowOrigins: ['*'], // TODO: Restrict in production
        maxAge: Duration.days(1),
      },
    });

    // Create Lambda integration (same as V1)
    const lambdaIntegration = new HttpLambdaIntegration(
      'LambdaIntegration',
      backendLambda
    );

    // --- Define V2 API routes ---
    // Remove V1 routes implicitly by not adding them here

    // Analysis endpoint
    httpApi.addRoutes({
      path: '/analyze',
      methods: [apigwv2.HttpMethod.POST],
      integration: lambdaIntegration,
    });

    // Chat endpoint
    httpApi.addRoutes({
      path: '/chat',
      methods: [apigwv2.HttpMethod.POST],
      integration: lambdaIntegration,
    });

    // Document CRUD endpoints
    httpApi.addRoutes({
      path: '/documents',
      methods: [apigwv2.HttpMethod.POST, apigwv2.HttpMethod.GET], // Create and List
      integration: lambdaIntegration,
    });
    httpApi.addRoutes({
      path: '/documents/{id}',
      methods: [apigwv2.HttpMethod.GET, apigwv2.HttpMethod.DELETE], // Read one and Delete
      integration: lambdaIntegration,
    });
    // Add PUT route here if implementing update

    // --- Frontend Hosting (S3 + CloudFront - No changes needed) ---
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

    // --- S3 Bucket Deployment (No changes needed) ---
    new s3deploy.BucketDeployment(this, 'DeployReactApp', {
      sources: [s3deploy.Source.asset(path.join(__dirname, '../../frontend/dist'))],
      destinationBucket: frontendBucket,
      distribution: distribution,
      distributionPaths: ['/*'],
      prune: true,
    });


    // --- Stack Outputs (No changes needed) ---
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