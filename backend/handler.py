# ResumeCoach/backend/handler.py
import json
import boto3
import os
import uuid
from datetime import datetime, timedelta
import logging
import pickle
import base64
import pathlib

from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate, SystemMessagePromptTemplate,
    HumanMessagePromptTemplate, MessagesPlaceholder
)
from langchain.schema import HumanMessage, AIMessage
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough

# --- Configuration ---
logger = logging.getLogger()
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger.setLevel(log_level)

ITEMS_TABLE_NAME = os.environ.get('ITEMS_TABLE_NAME')
SESSIONS_TABLE_NAME = os.environ.get('SESSIONS_TABLE_NAME')
if not ITEMS_TABLE_NAME or not SESSIONS_TABLE_NAME:
    logger.error("FATAL: Environment variable ITEMS_TABLE_NAME or SESSIONS_TABLE_NAME is not set.")
    raise ValueError("FATAL: ITEMS_TABLE_NAME or SESSIONS_TABLE_NAME not set.")

ssm = boto3.client('ssm')
param_name = os.environ.get('OPENAI_API_PARAM_NAME')

OPENAI_API_KEY = None
if param_name:
    try:
        OPENAI_API_KEY = ssm.get_parameter(
            Name=param_name,
            WithDecryption=True
        )['Parameter']['Value']
        logger.info("Fetched OpenAI API key from SSM Parameter Store.")
    except Exception as e:
        logger.error(f"Could not retrieve OpenAI key from SSM ({param_name}): {e}")
# fallback for local/dev where you might still export OPENAI_API_KEY
OPENAI_API_KEY = OPENAI_API_KEY or os.environ.get('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    logger.error("WARN: Environment variable OPENAI_API_KEY is not set. LLM calls will fail.")

# --- LLM Setup ---
llm = None
if OPENAI_API_KEY:
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=OPENAI_API_KEY,
            temperature=0.3,
            max_tokens=1500
        )
        logger.info("ChatOpenAI model initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize ChatOpenAI model: {e}", exc_info=True)
else:
    logger.warning("LLM not initialized because OPENAI_API_KEY is missing.")

# --- AWS Clients ---
dynamodb_resource = boto3.resource('dynamodb')
items_table = dynamodb_resource.Table(ITEMS_TABLE_NAME)
sessions_table = dynamodb_resource.Table(SESSIONS_TABLE_NAME)

# --- CORS Headers ---
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*', # Adjust in production!
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Id',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
    'Access-Control-Expose-Headers': 'X-Session-Id'
}

# --- Prompt Loading ---
backend_dir = pathlib.Path(__file__).parent
prompts_dir = backend_dir / 'prompts'

def load_prompt_template(filename: str) -> str:
    """Loads a prompt template string from the prompts directory."""
    try:
        prompt_path = prompts_dir / filename
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {prompt_path}")
        return "Error: Prompt template missing."
    except Exception as e:
        logger.error(f"Error loading prompt {filename}: {e}", exc_info=True)
        return "Error: Could not load prompt template."

ANALYSIS_SYSTEM_PROMPT_TEMPLATE = load_prompt_template("analysis_system_prompt.txt")
CHAT_SYSTEM_PROMPT_TEMPLATE = load_prompt_template("chat_system_prompt.txt")


# --- Helper Functions ---
def create_api_gateway_response(status_code: int, body: dict, session_id: str | None = None) -> dict:
    """Creates a standard API Gateway v2 HTTP response."""
    response_headers = CORS_HEADERS.copy()
    if session_id:
        if isinstance(body, dict):
            body['sessionId'] = session_id # Include sessionId in body if dict
        response_headers['X-Session-Id'] = session_id # Expose via header

    return {
        'statusCode': status_code,
        'headers': response_headers,
        'body': json.dumps(body)
    }

# --- Session Management ---
SESSION_TTL_HOURS = 24

def get_session_data(session_id: str) -> dict | None:
    """Loads session data from DynamoDB, deserializing chat history."""
    if not session_id:
        return None
    try:
        response = sessions_table.get_item(Key={'sessionId': session_id})
        item = response.get('Item')
        if item:
            if 'chat_history_blob' in item:
                try:
                    pickled_history = base64.b64decode(item['chat_history_blob'])
                    deserialized_history = pickle.loads(pickled_history)
                    # Verify structure after unpickling
                    if isinstance(deserialized_history, list) and all(isinstance(m, (HumanMessage, AIMessage)) for m in deserialized_history):
                        item['chat_history'] = deserialized_history
                    else:
                        logger.warning(f"Deserialized history for {session_id} is not a list of LangChain messages. Resetting.")
                        item['chat_history'] = []
                except (pickle.UnpicklingError, TypeError, base64.binascii.Error, AttributeError, EOFError) as e:
                    logger.error(f"Error deserializing chat history for session {session_id}: {e}", exc_info=True)
                    item['chat_history'] = [] # Recover by resetting history
                del item['chat_history_blob'] # Remove blob regardless of success
            else:
                item['chat_history'] = [] # Initialize if blob doesn't exist

            logger.info(f"Loaded session {session_id}")
            return item
        else:
            logger.info(f"Session {session_id} not found.")
            return None
    except Exception as e:
        logger.error(f"Error loading session {session_id}: {e}", exc_info=True)
        return None

def save_session_data(session_data: dict):
    """Saves session data to DynamoDB, serializing chat history and setting TTL."""
    if not session_data or 'sessionId' not in session_data:
        logger.error("Attempted to save invalid session data (missing sessionId).")
        return

    session_id = session_data['sessionId']
    try:
        ttl_timestamp = int((datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)).timestamp())
        item_to_save = session_data.copy()
        item_to_save['ttl'] = ttl_timestamp
        item_to_save['lastUpdated'] = datetime.utcnow().isoformat()

        if 'chat_history' in item_to_save:
            chat_history_list = item_to_save['chat_history']
            # Serialize only if it's a valid list of LangChain messages
            if isinstance(chat_history_list, list) and all(isinstance(m, (HumanMessage, AIMessage)) for m in chat_history_list):
                try:
                    pickled_history = pickle.dumps(chat_history_list)
                    item_to_save['chat_history_blob'] = base64.b64encode(pickled_history).decode('utf-8')
                except pickle.PicklingError as e:
                    logger.error(f"Error serializing chat history for session {session_id}: {e}", exc_info=True)
                    # Avoid saving potentially corrupted state by removing the blob if pickling fails
                    if 'chat_history_blob' in item_to_save: del item_to_save['chat_history_blob']
            else:
                 logger.warning(f"Chat history for session {session_id} is not in expected format for serialization. Skipping history save.")
                 if 'chat_history_blob' in item_to_save: del item_to_save['chat_history_blob'] # Ensure no partial state

            del item_to_save['chat_history'] # Always remove the raw list before saving

        sessions_table.put_item(Item=item_to_save)
        logger.info(f"Saved session {session_id}")
    except Exception as e:
        logger.error(f"Error saving session {session_id}: {e}", exc_info=True)

# --- Default Items Endpoints ---
def get_all_default_item_metadata(event):
    """Retrieves metadata (id, name) for all default items from the items table."""
    logger.info("Attempting to fetch all default items metadata via Scan.")
    try:
        # Project only 'id' and 'name' attributes. '#nm' aliases 'name' (reserved keyword).
        response = items_table.scan(
            ProjectionExpression='id, #nm',
            ExpressionAttributeNames={'#nm': 'name'}
        )
        items = response.get('Items', [])
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            logger.info("Default items scan paginated, fetching next page...")
            response = items_table.scan(
                ProjectionExpression='id, #nm',
                ExpressionAttributeNames={'#nm': 'name'},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))

        logger.info(f"Successfully scanned and retrieved metadata for {len(items)} default items.")
        # Filter out any malformed items just in case
        valid_items = [item for item in items if 'id' in item and 'name' in item]
        if len(valid_items) != len(items):
            logger.warning("Some scanned default items were missing 'id' or 'name'.")
        return create_api_gateway_response(200, valid_items)
    except Exception as e:
        logger.error(f"Error scanning default items table: {e}", exc_info=True)
        return create_api_gateway_response(500, {'error': 'Internal server error while fetching default items list'})

def get_default_item_content(event):
    """Retrieves the full content of a specific default item by ID."""
    item_id = None
    try:
        item_id = event['pathParameters']['id']
        logger.info(f"Attempting to fetch default item content with ID: {item_id}")
        response = items_table.get_item(Key={'id': item_id})
        item = response.get('Item')
        if item:
            logger.info(f"Successfully retrieved default item content for ID: {item_id}")
            # Return only essential fields
            return create_api_gateway_response(200, {'id': item.get('id'), 'content': item.get('content', 'Error: Content missing')})
        else:
            logger.warning(f"Default item content not found in DynamoDB with ID: {item_id}")
            return create_api_gateway_response(404, {'error': f"Default item content not found for ID: {item_id}"})
    except KeyError:
        logger.error("Missing 'id' in pathParameters for get_default_item")
        return create_api_gateway_response(400, {'error': "Missing 'id' in request path"})
    except Exception as e:
        logger.error(f"Error getting default item {item_id}: {e}", exc_info=True)
        return create_api_gateway_response(500, {'error': 'Internal server error while fetching default item'})

# --- Core Application Logic ---
def perform_resume_analysis(event):
    """
    Analyzes resume against job description using the LLM and creates a new session.
    Returns the analysis result and the new session ID.
    """
    if not llm:
        logger.error("LLM not available for analysis. Check OPENAI_API_KEY.")
        return create_api_gateway_response(503, {'error': 'LLM service is unavailable. Check API Key configuration.'})
    if "Error:" in ANALYSIS_SYSTEM_PROMPT_TEMPLATE:
         logger.error("Analysis cannot proceed because the prompt template is missing or failed to load.")
         return create_api_gateway_response(500, {'error': 'Internal configuration error: Analysis template unavailable.'})

    try:
        body = json.loads(event.get('body', '{}'))
        resume_text = body.get('resume')
        job_description_text = body.get('job_description')

        if not resume_text or not job_description_text:
            logger.warning("Analysis request missing resume or job description.")
            return create_api_gateway_response(400, {'error': 'Both "resume" and "job_description" are required.'})

        logger.info("Starting resume analysis and creating new session.")

        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(ANALYSIS_SYSTEM_PROMPT_TEMPLATE)
        ])
        chain = (RunnablePassthrough() | prompt | llm | StrOutputParser())

        logger.info("Invoking LLM chain for analysis...")
        analysis_result = chain.invoke({
            "resume": resume_text,
            "job_description": job_description_text,
        })
        logger.info("LLM analysis completed successfully.")

        new_session_id = str(uuid.uuid4())
        session_data = {
            'sessionId': new_session_id,
            'resume': resume_text,
            'jobDescription': job_description_text,
            'initialAnalysis': analysis_result,
            'chat_history': [], # Initial history is empty list of messages
            'createdAt': datetime.utcnow().isoformat()
        }
        save_session_data(session_data)

        return create_api_gateway_response(200, {'analysis': analysis_result}, session_id=new_session_id)

    except json.JSONDecodeError:
         logger.error("Error decoding JSON body for analysis request.")
         return create_api_gateway_response(400, {'error': 'Invalid JSON format in request body'})
    except Exception as e:
        logger.error(f"Error during resume analysis: {e}", exc_info=True)
        return create_api_gateway_response(500, {'error': 'Internal server error during analysis'})

def handle_chat_follow_up(event):
    """
    Handles follow-up chat questions using context and history from an existing session.
    Returns the LLM's answer.
    """
    if not llm:
        logger.error("LLM not available for chat. Check OPENAI_API_KEY.")
        return create_api_gateway_response(503, {'error': 'LLM service is unavailable. Check API Key configuration.'})
    if "Error:" in CHAT_SYSTEM_PROMPT_TEMPLATE:
         logger.error("Chat cannot proceed because the prompt template is missing or failed to load.")
         return create_api_gateway_response(500, {'error': 'Internal configuration error: Chat template unavailable.'})

    try:
        body = json.loads(event.get('body', '{}'))
        question = body.get('question')
        session_id = body.get('sessionId')

        if not question or not session_id:
            logger.warning("Chat request missing question or sessionId.")
            return create_api_gateway_response(400, {'error': 'Missing required fields: "question", "sessionId".'})

        session_data = get_session_data(session_id)
        if not session_data:
            logger.warning(f"Session not found for ID: {session_id}")
            return create_api_gateway_response(404, {'error': f"Session not found or expired for ID: {session_id}. Please start a new analysis."})

        resume_text = session_data.get('resume')
        job_description_text = session_data.get('jobDescription')
        initial_analysis = session_data.get('initialAnalysis')
        chat_history = session_data.get('chat_history', []) # Deserialized by get_session_data

        if not all([resume_text, job_description_text, initial_analysis]):
             logger.error(f"Session {session_id} is missing core context (resume, jd, or analysis).")
             return create_api_gateway_response(500, {'error': 'Session data is corrupted or incomplete. Please start a new analysis.'})

        logger.info(f"Processing chat for session {session_id} with {len(chat_history)} history messages.")

        current_user_message = HumanMessage(content=question)

        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(CHAT_SYSTEM_PROMPT_TEMPLATE),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{current_question}")
        ])
        chain = prompt | llm | StrOutputParser()

        logger.info(f"Invoking LLM chain for chat in session {session_id}...")
        answer_text = chain.invoke({
            "resume": resume_text,
            "job_description": job_description_text,
            "analysis_context": initial_analysis, # Renamed variable for clarity
            "chat_history": chat_history,
            "current_question": question
        })
        logger.info("LLM chat response generated successfully.")

        current_ai_message = AIMessage(content=answer_text)
        # Update the history list within the retrieved session_data dictionary
        session_data['chat_history'].append(current_user_message)
        session_data['chat_history'].append(current_ai_message)
        save_session_data(session_data) # Saves updated session including new history

        return create_api_gateway_response(200, {'answer': answer_text})

    except json.JSONDecodeError:
         logger.error("Error decoding JSON body for chat request.")
         return create_api_gateway_response(400, {'error': 'Invalid JSON format in request body'})
    except Exception as e:
        logger.error(f"Error during chat follow-up: {e}", exc_info=True)
        return create_api_gateway_response(500, {'error': 'Internal server error during chat'})


# --- Main Lambda Handler ---
def handler(event, context):
    """
    Main AWS Lambda handler function. Routes incoming API Gateway requests
    to the appropriate function based on HTTP method and path.
    """
    try:
        http_method = event['requestContext']['http']['method']
        path = event['requestContext']['http']['path']

        logger.info(f"Received event: Method={http_method}, Path={path}")
        # Consider logging event['rawQueryString'] or specific headers if needed for debugging

        # --- Routing Logic ---
        if path == '/analyze' and http_method == 'POST':
            return perform_resume_analysis(event)
        elif path == '/chat' and http_method == 'POST':
            return handle_chat_follow_up(event)
        elif path == '/items' and http_method == 'GET':
            return get_all_default_item_metadata(event)
        elif path.startswith('/items/') and http_method == 'GET':
             # Basic check for /items/{id} structure using path parameters
             if event.get('pathParameters', {}).get('id'):
                 return get_default_item_content(event)
             else:
                 logger.warning(f"Invalid path for get default item content: {path}")
                 return create_api_gateway_response(400, {'error': "Invalid request path for default item content. Expected /items/{id}."})
        else:
            logger.warning(f"Unhandled route: Method={http_method}, Path={path}")
            return create_api_gateway_response(404, {'error': 'Not Found'})

    except Exception as e:
        # Catch-all for unexpected errors during request processing or routing
        logger.error(f"Unhandled exception in handler: {e}", exc_info=True)
        return create_api_gateway_response(500, {'error': 'Internal Server Error'})