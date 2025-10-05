import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from langchain_experimental.agents import create_pandas_dataframe_agent
from utils_kk.variables.variable_definitions import customGraph, Verification
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from utils_kk.prompts.prompts_pandasAgent import pandas_agent_verification_template, pandas_agent_revisor_prompt, pandas_agent_prompt
from utils_kk.llm_initializations import llm
import structlog
from utils_kk.misl_function.misl_getData import get_data
from langchain_core.messages import AIMessage
from langchain_core.prompts.prompt import PromptTemplate
import pandas as pd
structlogger = structlog.get_logger(__name__)
load_dotenv(override=True)

## TO COMMENT AFTER TESTING
#router_data = get_data()


def pandas_agent_processing(state: customGraph):
    """
    This function is a langchain agent that takes in a customGraph object containing user query and router data.
    It uses the pandas dataframe agent to answer the user query and returns the result along with the intermediate steps.
    The pandas dataframe agent is configured to use the llm model and allow dangerous code.
    The agent is also configured to return intermediate steps and use the tool-calling functionality.
    The tools available to the agent are the get_reboots_data function which retrieves the timestamp of all reboots.
    The function is called with a RebootsData object containing the serial number of the router and the dataframe of router data.
    """


    #data = pd.DataFrame.from_records(state.get("data", None))
    data = state.get("data", None)
    serial_number = state.get("serialnumber", None)
    chat_history = state.get("chat_history", [])

    prompt = PromptTemplate(template=pandas_agent_prompt,
                            partial_variables={
                                "onerow": data.iloc[0].to_dict(),
                                "chat_history": chat_history,
                                "serial_number": serial_number
                            })

    agent = create_pandas_dataframe_agent(llm, data, verbose=True, 
    allow_dangerous_code=True, agent_type='tool-calling', 
    return_intermediate_steps=True, prefix=prompt.template)

    if state.get("verification", None) == "INVALID":
        query = pandas_agent_revisor_prompt.format(question=state.get("question", None))
    else:
        query = state.get("question", None)

    structlogger.debug("-- From chitchat node", detail=query)
    result = agent.invoke(query)

    intermediate_steps = []
    for action, observation in result.get("intermediate_steps", None):    
        intermediate_steps.append(AIMessage(content=str(
            f"Action: {action}\nObservation: {observation}\n"
        )))

    intermediate_steps.append(AIMessage(content=str(result.get("output", None))))

    return {
        "intermediate_result": result.get("output", None), 
        "chat_history": [AIMessage(content=str(result.get("output", None)))],
        "generation_scratchpad": intermediate_steps,
        "verification": None
    }


def validate_pandas_agent(state: customGraph):
    
    data = state.get("data", None)
    question = state.get("question", None)
    intermediate_result = state.get("intermediate_result", None)
    intermediate_steps = state.get("generation_scratchpad", None)

    
    output_format = PydanticOutputParser(
        pydantic_object = Verification).get_format_instructions()
    verification_prompt = PromptTemplate(template=pandas_agent_verification_template,
                                         partial_variables={
        "output_parser": output_format                                                                 
    })
    chain = verification_prompt | llm | JsonOutputParser()
    
    # try:
    #     for trial in range(int(os.getenv("num_retries", None))):
    #         response = chain.invoke(input={"question": question,
    #                                       "intermediate_steps": intermediate_steps,
    #                                       "data": data,
    #                                       "intermediate_result": intermediate_result})
    #         if isinstance(response, dict):
    #             if "verification" in response:
    #                 structlogger.debug("-- Verification node", detail=response)
    #                 return {
    #                     "verification": response.get("verification", None)
    #                 }
                    
    #         else:
    #             structlogger.error("Wrong schema recieved", detail=response)
    # except Exception as e:
    #     print(e)
    return {"verification": "VALID"}

def merge_answer(state: customGraph):
    
    verification_state = state.get("verification", None)
    if verification_state == "VALID":
        return {"final_result": state.get("intermediate_result", None)}

    else:
        raise ValueError("Verification state is not VALID")


if __name__ == "__main__":
    initial_state: customGraph = {
        "question": "Give me the most recent timestamp of reboots for 90100000000V412000536?",
        "data": get_data(),
        "generation_scratchpad": [],
        "intent_classification": "",
        "bypass_intention": False,
        "final_result": "",
        "chat_history": []
    }
    response = pandas_agent_processing(initial_state)
    print(response)
    
