from utils_kk.variables.variable_definitions import customGraph

def intent_classification_branch(state: customGraph):

    intent = state["intent_classification"]
    if intent == "rca":
        return "rca_processing"

    elif intent == "pandas-agent":
        return "pandas-agent processing"

    elif intent == "chit-chat":
        return "chit-chat processing"


def pandas_agent_branch(state: customGraph):
    
    verification = state["verification"]
    if verification == "VALID":
        return "merge_intermediate_answer"

    elif verification == "INVALID":
        return "INVALID Response"