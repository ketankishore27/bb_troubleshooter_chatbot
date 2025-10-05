import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from utils_kk.variables.variable_definitions import customGraph
from utils_kk.prompts.prompts_chitChat import chit_chat_template
from utils_kk.llm_initializations import llm
import structlog
from langchain.prompts import ChatPromptTemplate
from langchain.prompts import MessagesPlaceholder
from langchain_core.messages import AIMessage

structlogger = structlog.get_logger(__name__)
load_dotenv(override=True)

## TO COMMENT AFTER TESTING
#router_data = get_data()
## -- 

def chitChat_agent(state: customGraph):

    prompt = ChatPromptTemplate.from_messages([
        ("system", chit_chat_template),
        MessagesPlaceholder(variable_name="chat_history"),
        MessagesPlaceholder(variable_name="chat_suggestions"),
        ("ai", f"Serial Number for the customer: {state.get('serialnumber', None)}"),
        ("human", "{question}")
    ])

    # final_prompt = prompt.format({
    #                                 "question": state.get("question", None), 
    #                                 "chat_history": state.get("chat_history", [])
    #                             })

    chain = prompt | llm

    agent_response = chain.invoke({
                                    "question": state.get("question", None), 
                                    "chat_history": state.get("chat_history", []),
                                    "chat_suggestions": state.get("intermediate_result", []),
                                    "serial_number": state.get("serialnumber", None)
                                })

    return {
                "chat_history": [agent_response],
                "final_result": agent_response.content,
                "serialnumber": state.get("serialnumber", None)
            }

if __name__ == "__main__":

    initial_state: customGraph = {
        "question": "Hey there, How are you?",
        "chat_history": [],
        "generation_scratchpad": [],
        "intent_classification": "",
        "bypass_intention": False,
        "final_result": "",
        "intermediate_result": [AIMessage(content="Could you please provide your router's serial number so I can offer more precise assistance in the future?")]
    }
    response = chitChat_agent(initial_state)
    print(response)
    
