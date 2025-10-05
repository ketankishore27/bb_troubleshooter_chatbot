import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from utils_kk.variables.variable_definitions import customGraph, IntentClassificationResult, SerialNumberOnlyResult
from utils_kk.prompts.prompts_intentClassification import intent_classification_template, serialnumber_extractor_prompt
from utils_kk.llm_initializations import llm
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.prompts.prompt import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
import structlog
import json
structlogger = structlog.get_logger(__name__)
load_dotenv(override=True)

def extract_serial_number(state: customGraph):

    prompt = PromptTemplate(template=serialnumber_extractor_prompt,
                            partial_variables={
                                "chat_history": state.get("chat_history", []),
                                "output_parser": PydanticOutputParser(
                                    pydantic_object = SerialNumberOnlyResult).get_format_instructions()
                            })

    chain = prompt | llm | JsonOutputParser()
    
    try:

        query = state.get("question", None)
        for trial in range(int(os.getenv("num_retries", None))):
            response = chain.invoke(input={"user_question": query})
            if isinstance(response, dict):
                if "serial_number" in response:
                    structlogger.debug("-- Serial number extracted", detail=response)
                    return response["serial_number"]
            else:
                structlogger.error("Wrong schema recieved", detail=response)

    except Exception as e:
        structlogger.error("Exception in extract_serial_number", detail=e)
    
    
def intent_classification_node(state: customGraph):

    if state.get("bypass_intention", None):
        structlogger.error("ByPassing intent classification")
        #return {"generation_scratchpad": [AIMessage(content=str({"intent": "bypass_intention"}))]}
        return {"intent_classification": "rca"}

    else:
        query = state.get("question", None)
        serial_number = state.get("serialnumber", None)
        if not serial_number:
            structlogger.debug("Serial number not found in state")
            serial_number = extract_serial_number(state)
            #structlogger.debug("Using AI to extract serial number: ", detail=serial_number)
            
        structlogger.debug("-- From intent classification node", detail=query)
        output_format = PydanticOutputParser(
            pydantic_object = IntentClassificationResult).get_format_instructions()
        intent_classification_prompt = PromptTemplate(template=intent_classification_template,
                                                      partial_variables={
                                                            "chat_history": state.get("chat_history", []),
                                                            "output_parser": output_format,
                                                            "serial_number": serial_number                                                              
                                                        })
        chain = intent_classification_prompt | llm | JsonOutputParser()

        try:
            for trial in range(int(os.getenv("num_retries", None))):
                response = chain.invoke(input={"user_query": query})
                if isinstance(response, dict):
                    if "intent" in response:
                        structlogger.debug("-- Intent classification node", detail=response)
                        return {
                            "intent_classification": response["intent"], 
                            "chat_history": [HumanMessage(content=str(query))],
                            "intermediate_result": [AIMessage(content=str(response['suggested_question']))],
                            "serialnumber": serial_number
                        }
                        
                else:
                    structlogger.error("Wrong schema recieved", detail=response)
        except Exception as e:
            print(e)

if __name__ == "__main__":

    initial_state: customGraph = {
        "question": "what was the total byte recieved on accesspoint 2",
        "generation_scratchpad": [],
        "intent_classification": "",
        "bypass_intention": False,
        "final_result": ""
    }
    response = intent_classification_node(initial_state)
    print(initial_state)
    print("\n\n\n\n\n\n")
    print(response)