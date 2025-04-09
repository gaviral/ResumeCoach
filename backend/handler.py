# ResumeCoach/backend/handler.py
import json
import boto3
import os
import uuid
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger()
# Read log level from environment variable, default to INFO
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger.setLevel(log_level)

# Get the DynamoDB table name from environment variables
TABLE_NAME = os.environ.get('TABLE_NAME')
if not TABLE_NAME:
    logger.error("Environment variable TABLE_NAME is not set.")
    # Raise exception to prevent function from proceeding without table name
    raise ValueError("TABLE_NAME environment variable not set.")

# Use default session, credentials will be picked up from Lambda execution role
dynamodb_resource = boto3.resource('dynamodb')
table = dynamodb_resource.Table(TABLE_NAME)
# Get low-level client from resource if needed (e.g., for specific exceptions)
dynamodb_client = dynamodb_resource.meta.client

def create_item(event):
    """Creates a new item in DynamoDB."""
    try:
        # Assuming event body is JSON string from API Gateway HTTP API
        body = json.loads(event.get('body', '{}'))
        item_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        content = body.get('content') # Get content, check if None later

        if content is None:
             logger.warning("Create request missing 'content' field")
             return {
                'statusCode': 400,
                'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
                'body': json.dumps({'error': 'Missing "content" field in request body'})
            }

        item = {
            'id': item_id,
            'content': content,
            'createdAt': timestamp,
            'updatedAt': timestamp
        }

        table.put_item(Item=item)
        logger.info(f"Created item with ID: {item_id}")
        return {
            'statusCode': 201,
            # Required headers for CORS and JSON content type
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps(item)
        }
    except json.JSONDecodeError:
         logger.error("Error decoding JSON body")
         return {
            'statusCode': 400,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'Invalid JSON format in request body'})
        }
    except Exception as e:
        logger.error(f"Error creating item: {e}", exc_info=True) # Log stack trace
        return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'Internal server error during item creation'})
        }

def get_all_items(event):
    """Retrieves all items (limited scan for simplicity)."""
    try:
        # Warning: Scan operations can be inefficient and costly on large tables.
        # Consider using Query with indexes for production scenarios.
        response = table.scan(Limit=20) # Limit results for demo purposes
        items = response.get('Items', [])
        logger.info(f"Retrieved {len(items)} items via scan.")
        return {
            'statusCode': 200,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps(items)
        }
    except Exception as e:
        logger.error(f"Error getting all items: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'Internal server error while fetching items'})
        }

def get_item(event):
    """Retrieves a specific item by ID."""
    item_id = None # Initialize for logging in case of early error
    try:
        # ID comes from path parameters defined in API Gateway route
        item_id = event['pathParameters']['id']
        response = table.get_item(Key={'id': item_id})
        item = response.get('Item')

        if item:
            logger.info(f"Retrieved item with ID: {item_id}")
            return {
                'statusCode': 200,
                'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
                'body': json.dumps(item)
            }
        else:
            logger.warning(f"Item not found with ID: {item_id}")
            return {
                'statusCode': 404,
                'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
                'body': json.dumps({'error': 'Item not found'})
            }
    except KeyError:
         logger.error("Missing 'id' in pathParameters")
         return {
            'statusCode': 400,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': "Missing 'id' in request path"})
        }
    except Exception as e:
        logger.error(f"Error getting item {item_id}: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'Internal server error while fetching item'})
        }

def update_item(event):
    """Updates an existing item."""
    item_id = None
    try:
        item_id = event['pathParameters']['id']
        body = json.loads(event.get('body', '{}'))
        content = body.get('content') # Only update content for simplicity

        if content is None:
             logger.warning(f"Update request for {item_id} missing 'content' field")
             return {
                'statusCode': 400,
                'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
                'body': json.dumps({'error': 'Missing "content" field in request body'})
            }

        timestamp = datetime.utcnow().isoformat()

        # Use update_item with ConditionExpression to ensure item exists
        response = table.update_item(
            Key={'id': item_id},
            UpdateExpression='SET content = :c, updatedAt = :u',
            ConditionExpression='attribute_exists(id)', # Only update if item exists
            ExpressionAttributeValues={
                ':c': content,
                ':u': timestamp
            },
            ReturnValues='UPDATED_NEW' # Return the updated attributes
        )
        logger.info(f"Updated item with ID: {item_id}")
        return {
            'statusCode': 200,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps(response.get('Attributes', {}))
        }
    except KeyError:
         logger.error("Missing 'id' in pathParameters for update")
         return {
            'statusCode': 400,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': "Missing 'id' in request path"})
        }
    except json.JSONDecodeError:
         logger.error("Error decoding JSON body for update")
         return {
            'statusCode': 400,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'Invalid JSON format in request body'})
        }
    # Catch specific exception for item not found during conditional update
    except dynamodb_client.exceptions.ConditionalCheckFailedException:
         logger.warning(f"Update failed, item not found with ID: {item_id}")
         return {
            'statusCode': 404,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'Item not found'})
        }
    except Exception as e:
        logger.error(f"Error updating item {item_id}: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'Internal server error during item update'})
        }

def delete_item(event):
    """Deletes an item by ID."""
    item_id = None
    try:
        item_id = event['pathParameters']['id']
        # Optional: Add ConditionExpression="attribute_exists(id)" to ensure existence
        # This would return 404 if not found via ConditionalCheckFailedException
        table.delete_item(
            Key={'id': item_id}
            # ConditionExpression='attribute_exists(id)' # Uncomment for strict check
        )
        logger.info(f"Deleted item with ID: {item_id}")
        return {
            'statusCode': 200, # Or 204 No Content (adjust frontend if using 204)
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'message': f'Item {item_id} deleted successfully'})
        }
    except KeyError:
         logger.error("Missing 'id' in pathParameters for delete")
         return {
            'statusCode': 400,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': "Missing 'id' in request path"})
        }
    # except dynamodb_client.exceptions.ConditionalCheckFailedException:
    #      logger.warning(f"Delete failed, item not found with ID: {item_id}")
    #      return {
    #         'statusCode': 404,
    #         'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    #         'body': json.dumps({'error': 'Item not found'})
    #     } # Uncomment if using ConditionExpression
    except Exception as e:
        logger.error(f"Error deleting item {item_id}: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'Internal server error during item deletion'})
        }


def handler(event, context):
    """Main Lambda handler function routing requests."""
    # Using API Gateway HTTP API payload format v2.0
    try:
        http_method = event['requestContext']['http']['method']
        path = event['requestContext']['http']['path']

        logger.info(f"Received event: Method={http_method}, Path={path}")
        # Log event structure for debugging if needed (be careful with sensitive data)
        logger.debug(f"Full event: {json.dumps(event)}")

        # Simple routing logic based on method and path pattern
        if path == '/items':
            if http_method == 'POST':
                return create_item(event)
            elif http_method == 'GET':
                return get_all_items(event)
        # Check if path matches /items/{id} pattern
        elif path.startswith('/items/') and len(path.split('/')) == 3:
             # Path parameters are automatically extracted by HTTP API into event['pathParameters']
             if 'pathParameters' in event and 'id' in event['pathParameters']:
                if http_method == 'GET':
                    return get_item(event)
                elif http_method == 'PUT':
                    return update_item(event)
                elif http_method == 'DELETE':
                    return delete_item(event)
             else:
                 # Should not happen if routes are configured correctly, but good to handle
                 logger.error("Path matched /items/{id} but 'id' path parameter missing")
                 return {'statusCode': 400, 'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }, 'body': json.dumps({'error': "Missing 'id' in request path"})}

        # Default response for unhandled routes/methods
        logger.warning(f"Unhandled route: Method={http_method}, Path={path}")
        return {
            'statusCode': 404,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'Not Found'})
        }
    except Exception as e:
        # Catch-all for unexpected errors during routing/event processing
        logger.error(f"Unhandled exception in handler: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'Internal Server Error'})
        }
