# ResumeCoach/backend/handler.py
import json
import boto3
import os
import uuid
from datetime import datetime, timedelta # Import timedelta for TTL
import logging
import pickle # To serialize/deserialize message history
import base64 # To store pickled data in DynamoDB

# --- LangChain & OpenAI Imports ---
from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate, SystemMessagePromptTemplate,
    HumanMessagePromptTemplate, MessagesPlaceholder
)
from langchain.schema import HumanMessage, AIMessage
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
# Memory imports will be added later if needed for specific memory strategies

# --- Configuration ---
logger = logging.getLogger()
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger.setLevel(log_level)

# Get DynamoDB table names from environment variables (set by CDK)
ITEMS_TABLE_NAME = os.environ.get('ITEMS_TABLE_NAME')
SESSIONS_TABLE_NAME = os.environ.get('SESSIONS_TABLE_NAME')
if not ITEMS_TABLE_NAME or not SESSIONS_TABLE_NAME:
    fatal_error = "FATAL: Environment variable ITEMS_TABLE_NAME or SESSIONS_TABLE_NAME is not set."
    logger.error(fatal_error)
    raise ValueError(fatal_error)

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    # Log an error, but allow function to load. Calls will fail later.
    logger.error("WARN: Environment variable OPENAI_API_KEY is not set. LLM calls will fail.")
    # We don't raise an error here to allow fetching defaults even if key is missing

# --- LLM Setup (Conditional) ---

llm = None
if OPENAI_API_KEY:
    try:
        # Initialize the ChatOpenAI model (using gpt-4o-mini as requested)
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=OPENAI_API_KEY,
            temperature=0.3, # Adjust temperature for creativity vs consistency
            max_tokens=1500  # Adjust based on expected output length
        )
        logger.info("ChatOpenAI model initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize ChatOpenAI model: {e}", exc_info=True)
        # llm remains None, API calls requiring it will fail gracefully later
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
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Id', # Allow Session ID header
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET', # Only allow needed methods
    'Access-Control-Expose-Headers': 'X-Session-Id' # Expose Session ID header to frontend
}

# --- Helper Function for Responses ---
def create_response(status_code, body, session_id=None):
    """Creates a standard API Gateway response, optionally including session ID."""
    response_headers = CORS_HEADERS.copy()
    # Add session ID to body AND headers if provided
    if session_id:
        if isinstance(body, dict):
            body['sessionId'] = session_id
        response_headers['X-Session-Id'] = session_id

    return {
        'statusCode': status_code,
        'headers': response_headers,
        'body': json.dumps(body)
    }

# --- Session Helper Functions ---
SESSION_TTL_HOURS = 24 # Sessions expire after 24 hours of inactivity

def get_session(session_id):
    """Loads session data from DynamoDB."""
    if not session_id:
        return None
    try:
        response = sessions_table.get_item(Key={'sessionId': session_id})
        item = response.get('Item')
        if item:
            # Deserialize message history
            if 'chat_history_blob' in item:
                try:
                    pickled_history = base64.b64decode(item['chat_history_blob'])
                    # Ensure compatibility with LangChain message objects
                    deserialized_history = pickle.loads(pickled_history)
                    # Basic check if it looks like LangChain messages
                    if isinstance(deserialized_history, list) and all(isinstance(m, (HumanMessage, AIMessage)) for m in deserialized_history):
                         item['chat_history'] = deserialized_history
                    else:
                         logger.warning(f"Deserialized history for {session_id} is not a list of LangChain messages. Resetting.")
                         item['chat_history'] = []
                except (pickle.UnpicklingError, TypeError, base64.binascii.Error, AttributeError) as e:
                    logger.error(f"Error deserializing chat history for session {session_id}: {e}", exc_info=True)
                    item['chat_history'] = [] # Recover by resetting history
            else:
                 item['chat_history'] = [] # Initialize if blob doesn't exist

            # Remove blob from returned dict to avoid confusion
            if 'chat_history_blob' in item:
                del item['chat_history_blob']

            logger.info(f"Loaded session {session_id}")
            return item
        else:
            logger.info(f"Session {session_id} not found.")
            return None
    except Exception as e:
        logger.error(f"Error loading session {session_id}: {e}", exc_info=True)
        return None # Treat error as session not found

def save_session(session_data):
    """Saves session data to DynamoDB, including TTL."""
    if not session_data or 'sessionId' not in session_data:
        logger.error("Attempted to save invalid session data.")
        return

    session_id = session_data['sessionId']
    try:
        # Calculate TTL timestamp (Unix epoch seconds)
        ttl_timestamp = int((datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)).timestamp())
        item_to_save = session_data.copy() # Avoid modifying original dict
        item_to_save['ttl'] = ttl_timestamp
        item_to_save['lastUpdated'] = datetime.utcnow().isoformat()

        # Serialize message history using pickle and base64
        if 'chat_history' in item_to_save:
            # Ensure history contains serializable LangChain messages
            if isinstance(item_to_save['chat_history'], list) and all(isinstance(m, (HumanMessage, AIMessage)) for m in item_to_save['chat_history']):
                try:
                    pickled_history = pickle.dumps(item_to_save['chat_history'])
                    item_to_save['chat_history_blob'] = base64.b64encode(pickled_history).decode('utf-8')
                except pickle.PicklingError as e:
                    logger.error(f"Error serializing chat history for session {session_id}: {e}", exc_info=True)
                    # Decide how to handle: maybe save without history or raise error?
                    if 'chat_history_blob' in item_to_save: del item_to_save['chat_history_blob']
            else:
                 logger.warning(f"Chat history for session {session_id} is not in expected format for serialization. Skipping history save.")
                 if 'chat_history_blob' in item_to_save: del item_to_save['chat_history_blob'] # Ensure no partial state

            # Remove the raw list before saving to DDB
            del item_to_save['chat_history']

        sessions_table.put_item(Item=item_to_save)
        logger.info(f"Saved session {session_id}")
    except Exception as e:
        logger.error(f"Error saving session {session_id}: {e}", exc_info=True)
        # Decide if frontend needs notification of save failure

# --- Default Data Functions (Use items_table) ---
def get_all_default_items(event):
    """Retrieves metadata (id, name) for default items."""
    logger.info("Attempting to fetch all default items from DynamoDB via Scan.")
    try:
        # Perform a Scan operation.
        # Project only 'id' and 'name' attributes to minimize data transfer.
        # '#nm' is used because 'name' is a reserved keyword in DynamoDB.
        response = items_table.scan(
            ProjectionExpression='id, #nm',
            ExpressionAttributeNames={'#nm': 'name'}
        )
        items = response.get('Items', [])

        # Handle pagination if the table grows larger (Scan results are limited to 1MB)
        while 'LastEvaluatedKey' in response:
            logger.info("Default items scan paginated, fetching next page...")
            response = items_table.scan(
                ProjectionExpression='id, #nm',
                ExpressionAttributeNames={'#nm': 'name'},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))
        logger.info(f"Successfully scanned and retrieved {len(items)} default items.")
        valid_items = [item for item in items if 'id' in item and 'name' in item]
        if len(valid_items) != len(items):
            logger.warning("Some scanned default items were missing 'id' or 'name'.")
        return create_response(200, valid_items)
    except Exception as e:
        logger.error(f"Error scanning default items table: {e}", exc_info=True)
        return create_response(500, {'error': 'Internal server error while fetching default items list'})

def get_default_item(event):
    """Retrieves the content of a specific default item by ID."""
    item_id = None
    try:
        item_id = event['pathParameters']['id']
        logger.info(f"Attempting to fetch default item content with ID: {item_id}")
        response = items_table.get_item(Key={'id': item_id})
        item = response.get('Item')
        if item:
            logger.info(f"Successfully retrieved default item content with ID: {item_id}")
            return create_response(200, {'id': item.get('id'), 'content': item.get('content', 'Error: Content missing')})
        else:
            logger.warning(f"Default item content not found in DynamoDB with ID: {item_id}")
            return create_response(404, {'error': f"Default item content not found for ID: {item_id}"})
    except KeyError:
        logger.error("Missing 'id' in pathParameters for get_default_item")
        return create_response(400, {'error': "Missing 'id' in request path"})
    except Exception as e:
        logger.error(f"Error getting default item {item_id}: {e}", exc_info=True)
        return create_response(500, {'error': 'Internal server error while fetching default item'})

# --- V2 Core Functions (Updated for Sessions) ---

def analyze_resume(event):
    """
    Analyzes resume against job description and creates a NEW session.
    """
    if not llm:
        logger.error("LLM not available for analysis. Check OPENAI_API_KEY.")
        return create_response(503, {'error': 'LLM service is unavailable. Check API Key configuration.'})

    try:
        body = json.loads(event.get('body', '{}'))
        resume_text = body.get('resume')
        job_description_text = body.get('job_description')

        if not resume_text or not job_description_text:
            logger.warning("Analysis request missing resume or job description.")
            return create_response(400, {'error': 'Both "resume" and "job_description" are required.'})

        logger.info("Starting resume analysis and creating new session.")

        # --- LangChain Analysis ---
        system_template = """You are an expert Resume Coach AI. Your task is to analyze a provided resume against a job description.
        Provide clear, concise, and actionable feedback structured in three sections:
        1.  **Qualification Assessment:** Briefly state how well the resume aligns with the job description (e.g., Highly Qualified, Qualified, Partially Qualified, Not Qualified) and provide a 1-2 sentence explanation referencing specific resume points and job requirements.
        2.  **Missing Skills/Experience:** List the key skills or experiences mentioned in the job description that are *not* clearly present in the resume. Be specific. If nothing significant is missing, state that clearly.
        3.  **Key Strengths:** Highlight 2-3 key strengths or experiences from the resume that *directly* match important requirements in the job description. Quote or reference specific parts of the resume and job description.

        Analyze the following:
        Job Description:
        {job_description}

        Resume:
        {resume}

        Provide only the structured analysis as described above."""
        prompt = ChatPromptTemplate.from_messages([SystemMessagePromptTemplate.from_template(system_template)])
        chain = (RunnablePassthrough() | prompt | llm | StrOutputParser())
        logger.info("Invoking LLM chain for analysis...")
        analysis_result = chain.invoke({
            "resume": resume_text,
            "job_description": job_description_text,
        })
        logger.info("LLM analysis completed successfully.")

        # --- Create and save new session ---
        new_session_id = str(uuid.uuid4())
        session_data = {
            'sessionId': new_session_id,
            'resume': resume_text,
            'jobDescription': job_description_text,
            'initialAnalysis': analysis_result,
            'chat_history': [], # Initialize empty history (as LangChain messages)
            'createdAt': datetime.utcnow().isoformat()
        }
        save_session(session_data) # Saves serialized history

        # Return analysis and the NEW session ID
        # create_response handles adding sessionId to body/headers
        return create_response(200, {'analysis': analysis_result}, session_id=new_session_id)

    except json.JSONDecodeError:
         logger.error("Error decoding JSON body for analysis request.")
         return create_response(400, {'error': 'Invalid JSON format in request body'})
    except Exception as e:
        logger.error(f"Error during resume analysis: {e}", exc_info=True)
        return create_response(500, {'error': 'Internal server error during analysis'})

def chat_follow_up(event):
    """Handles follow-up chat questions using session state from DynamoDB."""
    if not llm:
        logger.error("LLM not available for chat. Check OPENAI_API_KEY.")
        return create_response(503, {'error': 'LLM service is unavailable. Check API Key configuration.'})

    try:
        body = json.loads(event.get('body', '{}'))
        question = body.get('question')
        session_id = body.get('sessionId')

        if not question or not session_id:
            logger.warning("Chat request missing question or sessionId.")
            return create_response(400, {'error': 'Missing required fields: "question", "sessionId".'})

        # --- Load session data ---
        session_data = get_session(session_id)
        if not session_data:
            logger.warning(f"Session not found for ID: {session_id}")
            return create_response(404, {'error': f"Session not found or expired for ID: {session_id}. Please start a new analysis."})

        # Extract context from loaded session
        resume_text = session_data.get('resume')
        job_description_text = session_data.get('jobDescription')
        analysis_context = session_data.get('initialAnalysis')
        # History is deserialized by get_session into LangChain messages
        langchain_chat_history = session_data.get('chat_history', [])

        if not all([resume_text, job_description_text, analysis_context]):
             logger.error(f"Session {session_id} is missing core context (resume, jd, or analysis).")
             # Maybe try to recover or inform user
             return create_response(500, {'error': 'Session data is corrupted. Please start a new analysis.'})

        logger.info(f"Processing chat for session {session_id} with {len(langchain_chat_history)} history messages.")

        # --- Prepare for LLM call ---
        current_user_message = HumanMessage(content=question)

        # --- LangChain Prompt Template ---
        # This template assumes the history is passed correctly.
        # Memory management (windowing/summarization) would modify the `langchain_chat_history`
        # list *before* it's passed to invoke, if implemented.
        system_template = """You are the Resume Coach AI, continuing a conversation with a user about their resume and a job description.
You have already provided an initial analysis. Now, answer the user's current follow-up question based on the information contained within the resume, the job description, your previous analysis, AND the preceding chat history provided below.
Do not invent new information or make assumptions beyond this context. Keep your answer concise and directly related to the current question.

Static Context:
--- Job Description ---
{job_description}
--- Resume ---
{resume}
--- Initial Analysis You Provided ---
{analysis_context}
--- End Static Context ---

Chat History (User questions and your previous answers):"""

        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{current_question}") # Pass current question separately
        ])

        # --- LangChain Chain ---
        chain = prompt | llm | StrOutputParser()

        # --- Invoke Chain ---
        # NOTE: If implementing memory (window/summary), the `langchain_chat_history`
        # variable would be modified by the memory logic before this point.
        logger.info(f"Invoking LLM chain for chat in session {session_id}...")
        answer_text = chain.invoke({
            # Static context from session
            "resume": resume_text,
            "job_description": job_description_text,
            "analysis_context": analysis_context,
            # History from session (potentially modified by memory logic later)
            "chat_history": langchain_chat_history,
             # Current question
            "current_question": question
        })
        logger.info("LLM chat response generated successfully.")

        # --- Update history and save session ---
        current_ai_message = AIMessage(content=answer_text)
        # Update the history list IN the session_data dictionary
        session_data['chat_history'].append(current_user_message)
        session_data['chat_history'].append(current_ai_message)
        save_session(session_data) # Saves the updated session_data (incl. serialized history)

        # Return only the answer
        return create_response(200, {'answer': answer_text}) # No need to send session_id back here

    except json.JSONDecodeError:
         logger.error("Error decoding JSON body for chat request.")
         return create_response(400, {'error': 'Invalid JSON format in request body'})
    except Exception as e:
        logger.error(f"Error during chat follow-up: {e}", exc_info=True)
        return create_response(500, {'error': 'Internal server error during chat'})


# --- Main Handler ---
def handler(event, context):
    """Main Lambda handler function routing requests."""
    try:
        http_method = event['requestContext']['http']['method']
        path = event['requestContext']['http']['path']

        logger.info(f"Received event: Method={http_method}, Path={path}")
        # Avoid logging full event body in production if it contains sensitive data
        # logger.debug(f"Full event: {json.dumps(event)}")

        # --- Routing Logic ---
        if path == '/analyze' and http_method == 'POST':
            return analyze_resume(event)
        elif path == '/chat' and http_method == 'POST':
            return chat_follow_up(event)
        elif path == '/items' and http_method == 'GET':
            return get_all_default_items(event)
        elif path.startswith('/items/') and http_method == 'GET':
             path_parts = path.split('/')
             # Basic check for /items/{id} structure
             if len(path_parts) == 3 and event.get('pathParameters', {}).get('id'):
                 return get_default_item(event)
             else:
                 logger.warning(f"Invalid path for get default item: {path}")
                 return create_response(400, {'error': "Invalid request path for default item."})
        else:
            logger.warning(f"Unhandled route: Method={http_method}, Path={path}")
            return create_response(404, {'error': 'Not Found'})

    except Exception as e:
        # Catch-all for unexpected errors during routing/event processing
        logger.error(f"Unhandled exception in handler: {e}", exc_info=True)
        return create_response(500, {'error': 'Internal Server Error'})