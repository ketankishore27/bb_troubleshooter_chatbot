import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from langchain_experimental.agents import create_pandas_dataframe_agent
from utils_kk.variables.variable_definitions import customGraph
from utils_kk.llm_initializations import llm
import structlog
from utils_kk.misl_function.misl_getData import get_data
from utils_kk.prompts.prompts_rca import rca_classification_template_3
from utils_kk.tool_functions.tool_calling_funcs import *
from langchain.prompts import ChatPromptTemplate
from langchain.prompts import MessagesPlaceholder

structlogger = structlog.get_logger(__name__)
load_dotenv(override=True)

## TO COMMENT AFTER TESTING
#router_data = get_data()
## -- 

def rca_agent(state: customGraph):

    data = state.get("data", None)
    question = state.get("question", None)
    baseline_data = get_baseline_statistics("knowledge_folder/datapoints/DE_baseline_router_data/")
    template = rca_classification_template.format(one_row=data.head[1].to_markdown())
    prompt = ChatPromptTemplate.from_messages([
        ("system", template),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
        ("human", "{question}")
    ])

    tools = [
        Tool(
            name="get_baseline_statistics",
            func=get_baseline_statistics,
            description="Use it when asked for root cause analysis of a hardware reboot *to get baseline statistics* for other routers and compare to current router."
        ),
        Tool(
            name="extract_comparison_data",
            func=extract_comparison_data,
            description="Use it when asked for root cause analysis of a hardware reboot *to get aggregated data* from: 1 hour, 6 hours, 24 hours and a month prior to the reboot."
        )
    ]

    agent = create_pandas_dataframe_agent(llm = llm, prompt = prompt, tools = tools, verbose=True, 
                                          allow_dangerous_code=True, agent_type='tool-calling')

    agent_response = agent.invoke(question)

    return agent_response

if __name__ == "__main__":

    initial_state: customGraph = {
        "question": "What was the root cause of the reboot at 2024-08-02 20:07:00?",
        "data": get_data(),
        "chat_history": [],
        "generation_scratchpad": [],
        "intent_classification": "",
        "bypass_intention": False,
        "final_result": ""
    }
    response = rca_agent(initial_state)
    print(response)
    
