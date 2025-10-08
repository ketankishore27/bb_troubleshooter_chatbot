from utils_kk.misl_function.misl_getData import get_data
from langgraph.graph import StateGraph, MessagesState
from langgraph.graph import START, END
from langgraph.checkpoint.memory import MemorySaver
from utils_kk.nodes.node_intentClassification import intent_classification_node
from utils_kk.variables.variable_definitions import customGraph
from utils_kk.nodes.node_pandasProcessing import pandas_agent_processing, validate_pandas_agent, merge_answer
from utils_kk.nodes.node_rca import rca_agent
from utils_kk.nodes.node_chitChat import chitChat_agent
from utils_kk.branching.branch_control import intent_classification_branch, pandas_agent_branch
from dotenv import load_dotenv
load_dotenv(override=True)


def update_global_state(state: customGraph):

    for key, value in state.items():        
        if key in ('chat_history'):
            for msgs in value:
                if msgs not in universal_state[key]:
                    universal_state[key].append(msgs)

        if (key == 'serialnumber') and (universal_state[key] == None):
            universal_state[key] = value
            
        
    return universal_state

def create_graph():
    graph = StateGraph(state_schema=customGraph)
    graph.add_node("intent_classification_node", intent_classification_node)
    graph.add_node("chitChat_node", chitChat_agent)
    graph.add_edge(START, "intent_classification_node")
    graph.add_conditional_edges("intent_classification_node", intent_classification_branch, 
                               {
                                    "rca_processing": "rca", 
                                    "pandas-agent processing": "pandas-agent processing",
                                    "chit-chat processing": "chitChat_node"
                                }
    )

    ## Flow-1
    graph.add_node("pandas-agent processing", pandas_agent_processing)
    graph.add_node("validate_pandas_agent", validate_pandas_agent)
    graph.add_node("merge_answer", merge_answer)
    graph.add_edge("pandas-agent processing", "validate_pandas_agent")
    graph.add_edge("chitChat_node", END)
    graph.add_conditional_edges("validate_pandas_agent", pandas_agent_branch,
                                {
                                    "merge_intermediate_answer": "merge_answer", 
                                    "INVALID Response": "pandas-agent processing"
                                }
    )
    graph.add_edge("merge_answer", END)
    
    ## Flow-2
    graph.add_node("rca", rca_agent)
    graph.add_edge("rca", END)

    store = MemorySaver()
    flow = graph.compile()
    return flow


if __name__ == "__main__":
    flow = create_graph()

    universal_state: customGraph = {
        "question": "",
        "generation_scratchpad": [],
        "chat_history": [],
        "intent_classification": "",
        "serialnumber": None,
        "bypass_intention": False,
        "intermediate_result": "",
        "final_result": "",
        "verification": None,
        "data": get_data()
    }
    
    while True:
        universal_state['question'] = input("User: ")
        response = flow.invoke(universal_state)
        universal_state = update_global_state(response)
    
        print(response['final_result'])




