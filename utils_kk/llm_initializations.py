import os
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
load_dotenv(override=True)


llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_API_BASE"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
    temperature=0,
    deployment_name=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME'),
    model_name=os.getenv('AZURE_OPENAI_ASSISTANT_MODEL'),
)
