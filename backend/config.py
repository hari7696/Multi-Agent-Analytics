from dotenv import load_dotenv
import os
import litellm
import logging
import sys
import warnings
from google.adk.models.lite_llm import LiteLlm

warnings.filterwarnings("ignore", message=".*config_type.*shadows an attribute.*", category=UserWarning)

load_dotenv()

# Azure Storage Configuration
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "mtfinance-agent-container")
AZURE_STATICDATA_CONTAINER_NAME = os.getenv("AZURE_STATICDATA_CONTAINER_NAME", "mtfinancial-agent-staticdata-container")
DATA_ENCRYPTION_KEY = os.getenv("DATA_ENCRYPTION_KEY")

def setup_logging(log_level=logging.INFO):
    """Setup logging configuration for the project"""
    logger = logging.getLogger("fin_agent")
    logger.setLevel(log_level)
    
    logger.handlers.clear()
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
    logging.getLogger('azure.cosmos').setLevel(logging.WARNING)
    logging.getLogger('azure').setLevel(logging.WARNING)
    
    logging.getLogger('watchfiles.main').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    return logger

logger = setup_logging()

api_base = os.getenv("LLM_API_BASE")
api_key = os.getenv("LLM_API_KEY")
api_version = os.getenv("LLM_API_VERSION")

litellm.api_key = api_key
litellm.api_base = api_base
litellm.api_version = api_version

litellm.request_timeout = 120
litellm.num_retries = 2
litellm.retry_delay = 5

MODEL = LiteLlm(model="azure/gpt-4.1")

MAX_ITERATIONS = 4