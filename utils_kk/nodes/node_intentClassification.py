import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from utils_kk.variables.variable_definitions import customGraph, IntentClassificationResult, \
                                                    SerialNumberOnlyResult, FeatureValidationResult

from utils_kk.misl_function.misl_loadPrompt import load_prompt
from utils_kk.llm_initializations import llm
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.prompts.prompt import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
import structlog
import json
structlogger = structlog.get_logger(__name__)
load_dotenv(override=True)


def extract_serial_number(state: customGraph):

    serialnumber_extractor_prompt = load_prompt(prompt_name="serialnumber_extractor_prompt", 
                                                filename="prompts_intentClassification.yml")

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
    
    
def feature_validation_extractor(state: customGraph):
    
    feature_validation_template = load_prompt(prompt_name="feature_validation_template", 
                                            filename="prompts_intentClassification.yml")

    prompt = PromptTemplate(template=feature_validation_template,
                            partial_variables={
                                "chat_history": state.get("chat_history", []),
                                "output_parser": PydanticOutputParser(
                                    pydantic_object = FeatureValidationResult).get_format_instructions()
                            })

    chain = prompt | llm | JsonOutputParser()
    
    try:
        query = state.get("question", None)
        for trial in range(int(os.getenv("num_retries", None))):
            response = chain.invoke(input={"user_query": query})
            if isinstance(response, dict):
                if all(k in response for k in ["matched_columns", "status", "explanation", "suggested_response"]):
                    structlogger.debug("-- Feature validation extracted", detail=response)
                    return response
            else:
                structlogger.error("Wrong schema recieved", detail=response)

    except Exception as e:
        structlogger.error("Exception in feature_validation_extractor", detail=e)


def predict_intent(state: customGraph, feature_validation_result: FeatureValidationResult):
    serial_number = state.get("serialnumber", None)
    query = state.get("question", None)

    intent_classification_template = load_prompt(prompt_name="intent_classification_template", 
                                                 filename="prompts_intentClassification.yml")

    matched_columns = feature_validation_result.get("matched_columns", [])
    explanation = feature_validation_result.get("explanation", None)

    output_format = PydanticOutputParser(
        pydantic_object = IntentClassificationResult).get_format_instructions()

    intent_classification_prompt = PromptTemplate(template=intent_classification_template,
                                                    partial_variables={
                                                        "chat_history": state.get("chat_history", []),
                                                        "output_parser": output_format,
                                                        "serial_number": serial_number,
                                                        "matched_columns": matched_columns,
                                                        "explanation": explanation                                                             
                                                    })

    chain = intent_classification_prompt | llm | JsonOutputParser()

    try:
        for trial in range(int(os.getenv("num_retries", None))):
            response = chain.invoke(input={"user_query": query})
            structlogger.debug("-- Intent classification response schema", detail=str(response.keys()))
            if isinstance(response, dict):
                if all(k in response for k in ["intent", "missing_fields", "suggested_question", "matched_columns", "explanation"]):
                    structlogger.debug("-- Intent classification node", detail=response)
                    return response
            else:
                structlogger.error("Wrong schema recieved", detail=response)

    except Exception as e:
        structlogger.error("Exception in predict_intent", detail=e)


def intent_classification_node(state: customGraph):

    query = state.get("question", None)
    serial_number = state.get("serialnumber", None)
    if not serial_number:
        structlogger.debug("Serial number not found in state")
        serial_number = extract_serial_number(state)

    ## Case-1 Serialnumber is not present
        if not serial_number:
            return {
                        "intent_classification": "chit-chat", 
                        "chat_history": [HumanMessage(content=str(query))],
                        "intermediate_result": [AIMessage(content="Respond to the non technical question (if any) and Ask for SerialNumber")],
                    }

    ## Is the question answerable
    structlogger.debug("-- From intent classification node", detail=query)
    feature_validation_result = feature_validation_extractor(state)
    if feature_validation_result["status"] == "UNAVAILABLE":
        return {
                    "intent_classification": "chit-chat", 
                    "chat_history": [HumanMessage(content=str(query))],
                    "intermediate_result": [AIMessage(content="I am not sure, if I have record of this parameter, could you please rephrase your question")],
                    "serialnumber": serial_number
                }
    
    ## Predict Intent
    response = predict_intent(state, feature_validation_result)
    return {
                "intent_classification": response["intent"], 
                "chat_history": [HumanMessage(content=str(query))],
                "intermediate_result": [AIMessage(content=str(response['suggested_question']))],
                "serialnumber": serial_number,
                "matched_columns": response["matched_columns"],
                "explanation": response.get("explanation", None)
            }


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