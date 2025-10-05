import streamlit as st
from main import create_graph
from utils_kk.misl_function.misl_getData import get_data
from utils_kk.variables.variable_definitions import customGraph

# Page configuration
st.set_page_config(
    page_title="Router Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🤖 Router Chit-Chat & RCA Agent")
st.markdown("---")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    st.markdown("### About")
    st.info("""
    This chatbot helps you:
    - 📊 Analyze router telemetry data
    - 🔍 Diagnose reboot issues
    - 📈 Query router statistics
    - 🛠️ Perform root cause analysis
    """)

# Initialize session state
if 'flow' not in st.session_state:
    with st.spinner("🔄 Initializing agent..."):
        st.session_state.flow = create_graph()
        
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant", 
            "content": "Hello! 👋 I'm your Router Analysis Assistant. I can help you analyze router telemetry data, diagnose reboot issues, and answer questions about router performance. What would you like to know?"
        }
    ]

if "universal_state" not in st.session_state:
    st.session_state.universal_state: customGraph = {
        "question": "",
        "generation_scratchpad": [],
        "chat_history": [],
        "intent_classification": "",
        "bypass_intention": False,
        "intermediate_result": "",
        "final_result": "",
        "verification": None,
        "serialnumber": None,
        "data": get_data()
    }

def update_global_state_streamlit(state: customGraph):

    for key, value in state.items():  

        if key in ('chat_history'):
            for msgs in value:
                if msgs not in st.session_state.universal_state[key]:
                    st.session_state.universal_state[key].append(msgs)

        if (key == 'serialnumber') and (st.session_state.universal_state[key] == None):
            st.session_state.universal_state[key] = value
            
        
    return st.session_state.universal_state

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me about router data, reboots, or performance metrics..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.universal_state['question'] = prompt
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("🔍 Analyzing..."):
            try:
                response = st.session_state.flow.invoke(st.session_state.universal_state)
                st.session_state.universal_state = update_global_state_streamlit(response)
                
                # print("Universal State", st.session_state.universal_state)
                # print("\n\n\n\n")
                # print("-"* 100)
                final_result = response.get("final_result", "No result returned.")
                
                # Display the response
                st.markdown(final_result)
                
                # Add assistant response to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_result
                })
                
            except Exception as e:
                error_message = f"❌ Error: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message
                })