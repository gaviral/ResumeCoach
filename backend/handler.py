# ResumeCoach/backend/handler.py
import json
import boto3
import os
import uuid
from datetime import datetime
import logging

# --- LangChain & OpenAI Imports ---
from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder
)
from langchain.schema import HumanMessage, AIMessage

from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough

# --- Configuration ---

# Configure logging
logger = logging.getLogger()
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger.setLevel(log_level)

# Get DynamoDB table name from environment variables (set by CDK)
TABLE_NAME = os.environ.get('TABLE_NAME')
if not TABLE_NAME:
    logger.error("FATAL: Environment variable TABLE_NAME is not set.")
    raise ValueError("TABLE_NAME environment variable not set.")

# Get OpenAI API Key from environment variables (set manually in Lambda console)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    # Log an error, but allow function to load. Calls will fail later.
    logger.error("WARN: Environment variable OPENAI_API_KEY is not set. LLM calls will fail.")
    # We don't raise an error here to allow fetching defaults even if key is missing

# --- AWS Clients ---
# Use default session, credentials/region picked up from Lambda execution role/environment
dynamodb_resource = boto3.resource('dynamodb')
table = dynamodb_resource.Table(TABLE_NAME)
dynamodb_client = dynamodb_resource.meta.client # For specific exceptions if needed

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


# --- CORS Headers ---
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*', # Adjust in production!
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET,PUT,DELETE' # Include methods used
}

# --- Helper Function for Responses ---
def create_response(status_code, body):
    """Creates a standard API Gateway response."""
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(body)
    }

# --- Default Data Functions (Modified V1 CRUD) ---

def get_all_default_items(event):
    """
    Retrieves metadata (id, name) for all items currently in the DynamoDB table
    by performing a Scan operation.
    WARNING: Scan operations can be inefficient on very large tables.
    This is acceptable here assuming the number of 'default' items remains small.
    Ensure items added manually include both 'id' (String) and 'name' (String) attributes.
    """
    logger.info("Attempting to fetch all items from DynamoDB via Scan.")
    try:
        # Perform a Scan operation.
        # Project only 'id' and 'name' attributes to minimize data transfer.
        # '#nm' is used because 'name' is a reserved keyword in DynamoDB.
        response = table.scan(
            ProjectionExpression='id, #nm',
            ExpressionAttributeNames={'#nm': 'name'}
        )
        items = response.get('Items', [])

        # Handle pagination if the table grows larger (Scan results are limited to 1MB)
        while 'LastEvaluatedKey' in response:
            logger.info("Scan response paginated, fetching next page...")
            response = table.scan(
                ProjectionExpression='id, #nm',
                ExpressionAttributeNames={'#nm': 'name'},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))

        logger.info(f"Successfully scanned and retrieved {len(items)} items.")

        # Filter out items that might be missing 'id' or 'name' (optional, defensive coding)
        valid_items = [item for item in items if 'id' in item and 'name' in item]
        if len(valid_items) != len(items):
            logger.warning("Some scanned items were missing 'id' or 'name' attributes.")

        return create_response(200, valid_items)

    except Exception as e:
        logger.error(f"Error scanning DynamoDB table: {e}", exc_info=True)
        return create_response(500, {'error': 'Internal server error while fetching default items list'})

def get_default_item(event):
    """Retrieves the content of a specific default item by ID."""
    item_id = None
    try:
        item_id = event['pathParameters']['id']
        logger.info(f"Attempting to fetch default item with ID: {item_id}")

        # Basic validation for expected default IDs (optional but good practice)
        # expected_defaults = ["DEFAULT_RESUME_1", "DEFAULT_JOB_DESC_1"]
        # if item_id not in expected_defaults:
        #     logger.warning(f"Requested ID '{item_id}' is not a known default item ID.")
        #     return create_response(404, {'error': f"Default item '{item_id}' not found"})

        response = table.get_item(Key={'id': item_id})
        item = response.get('Item')

        if item:
            logger.info(f"Successfully retrieved default item with ID: {item_id}")
            # Return only necessary fields (e.g., id and content)
            # Ensure 'content' exists before returning
            return create_response(200, {'id': item.get('id'), 'content': item.get('content', 'Error: Content missing')})
        else:
            logger.warning(f"Default item not found in DynamoDB with ID: {item_id}")
            # Even if it's an expected ID, it might not have been added to the table yet
            return create_response(404, {'error': f"Default item content not found for ID: {item_id}"})

    except KeyError:
        logger.error("Missing 'id' in pathParameters for get_default_item")
        return create_response(400, {'error': "Missing 'id' in request path"})
    except Exception as e:
        logger.error(f"Error getting default item {item_id}: {e}", exc_info=True)
        return create_response(500, {'error': 'Internal server error while fetching default item'})

# --- V2 Core Functions ---

def analyze_resume(event):
    """Analyzes resume against job description using LangChain and OpenAI."""
    if not llm:
        logger.error("LLM not available for analysis. Check OPENAI_API_KEY.")
        return create_response(503, {'error': 'LLM service is unavailable. Check API Key configuration.'})

    try:
        body = json.loads(event.get('body', '{}'))
        resume_text = body.get('resume')
        job_description_text = body.get('job_description')

        if not resume_text or not job_description_text:
            logger.warning("Analysis request missing resume or job description.")
            return create_response(400, {'error': 'Both "resume" and "job_description" are required in the request body.'})

        logger.info("Starting resume analysis.")

        # --- LangChain Prompt Template ---
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

        human_template = "{input}" # We'll pass the combined context here, though the system prompt does most work

        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            # HumanMessagePromptTemplate.from_template(human_template) # Not strictly needed if system prompt has all info
        ])

        # --- LangChain Chain ---
        # Using LCEL (LangChain Expression Language)
        chain = (
            # Pass resume and JD directly to the prompt formatting
            RunnablePassthrough()
            | prompt
            | llm
            | StrOutputParser()
        )

        # --- Invoke Chain ---
        logger.info("Invoking LLM chain for analysis...")
        analysis_result = chain.invoke({
            "resume": resume_text,
            "job_description": job_description_text,
            # "input": "" # Not needed if using RunnablePassthrough and system prompt directly
        })
        logger.info("LLM analysis completed successfully.")

        # Return the structured analysis from the LLM
        return create_response(200, {'analysis': analysis_result})

    except json.JSONDecodeError:
         logger.error("Error decoding JSON body for analysis request.")
         return create_response(400, {'error': 'Invalid JSON format in request body'})
    except Exception as e:
        logger.error(f"Error during resume analysis: {e}", exc_info=True)
        return create_response(500, {'error': 'Internal server error during analysis'})

def chat_follow_up(event):
    """Handles follow-up chat questions based on the analysis context AND chat history."""
    if not llm:
        logger.error("LLM not available for chat. Check OPENAI_API_KEY.")
        return create_response(503, {'error': 'LLM service is unavailable. Check API Key configuration.'})

    try:
        body = json.loads(event.get('body', '{}'))
        resume_text = body.get('resume')
        job_description_text = body.get('job_description')
        analysis_context = body.get('analysis_context')
        question = body.get('question')
        chat_history_raw = body.get('chat_history', []) # Default to empty list

        # Basic validation for required fields (excluding history)
        required_fields = {
            "resume": resume_text,
            "job_description": job_description_text,
            "analysis_context": analysis_context,
            "question": question
        }
        if not all(required_fields.values()):
            missing = [k for k, v in required_fields.items() if not v]
            logger.warning(f"Chat request missing required fields: {missing}")
            return create_response(400, {'error': f'Missing required fields: {", ".join(missing)}.'})

        # Validate history format
        if not isinstance(chat_history_raw, list):
             logger.warning(f"Received chat_history is not a list: {type(chat_history_raw)}")
             return create_response(400, {'error': 'Invalid format for chat_history, expected a list.'})

        logger.info(f"Starting chat follow-up for question: '{question}' with {len(chat_history_raw)} history messages.")

        # Convert frontend history to LangChain messages
        langchain_chat_history = []
        for msg in chat_history_raw:
            sender = msg.get('sender')
            text = msg.get('text')
            if sender == 'user' and text:
                langchain_chat_history.append(HumanMessage(content=text))
            elif sender == 'ai' and text:
                langchain_chat_history.append(AIMessage(content=text))
            else:
                # Log and skip malformed messages
                logger.warning(f"Skipping invalid message in chat_history: {msg}")

        # --- LangChain Prompt Template for Chat (Updated for History) ---
        # Updated system prompt and structure
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
        # Note: The actual history will be inserted by MessagesPlaceholder

        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            # This placeholder will insert the history messages correctly formatted
            MessagesPlaceholder(variable_name="chat_history"),
            # This is for the *current* user question
            HumanMessagePromptTemplate.from_template("{question}")
        ])

        # --- LangChain Chain (Structure remains the same) ---
        chain = prompt | llm | StrOutputParser()

        # --- Invoke Chain (Update input dictionary for history) ---
        logger.info("Invoking LLM chain for chat with history...")
        # Pass history to invoke
        answer = chain.invoke({
            # Still needed for the System Prompt context
            "resume": resume_text,
            "job_description": job_description_text,
            "analysis_context": analysis_context,
            # Pass the converted history list
            "chat_history": langchain_chat_history,
            # Pass the current question
            "question": question
        })
        logger.info("LLM chat response generated successfully.")

        return create_response(200, {'answer': answer})

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
        logger.debug(f"Full event: {json.dumps(event)}") # Be careful with sensitive data in production logs

        # --- Routing Logic ---

        # Route for analysis
        if path == '/analyze' and http_method == 'POST':
            return analyze_resume(event)

        # Route for chat follow-up
        elif path == '/chat' and http_method == 'POST':
            return chat_follow_up(event)

        # Routes for default items (repurposed V1 CRUD)
        elif path == '/items':
             if http_method == 'GET':
                 # Get list/metadata of default items
                 return get_all_default_items(event)
             # POST/PUT/DELETE for /items are not implemented for V2 user features
             # Could be added later for admin management of defaults

        elif path.startswith('/items/') and http_method == 'GET':
             # Check if path matches /items/{id} pattern
             path_parts = path.split('/')
             if len(path_parts) == 3 and 'pathParameters' in event and 'id' in event['pathParameters']:
                 # Get content of a specific default item
                 return get_default_item(event)
             else:
                 logger.warning(f"Path matched /items/{{id}} pattern but structure or parameters invalid: {path}")
                 return create_response(400, {'error': "Invalid request path or missing 'id' parameter for default item."})

        # --- Default Not Found ---
        logger.warning(f"Unhandled route: Method={http_method}, Path={path}")
        return create_response(404, {'error': 'Not Found'})

    except Exception as e:
        # Catch-all for unexpected errors during routing/event processing
        logger.error(f"Unhandled exception in handler: {e}", exc_info=True)
        return create_response(500, {'error': 'Internal Server Error'})