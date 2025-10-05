from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Any
from typing_extensions import Annotated, TypedDict
from typing import Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing import Optional
import pandas as pd


class SerialNumberOnlyResult(BaseModel):
    """
    Represents the output of the serial number extraction step.
    Only the best identified serial number is returned.

    Notes:
    - A router serial number is typically an alphanumeric string (letters + digits).
    - It may also be a long numeric identifier (>= 8 digits).
    - If no serial number can be confidently identified, the field should be null.
    """

    serial_number: Optional[str] = Field(
        None,
        description=(
            "The best identified router serial number, if available.\n"
            "- Example: '2351ADTRJ' or '90100000000V412000536'.\n"
            "- Must be alphanumeric or digit-only (length >= 8).\n"
            "- Set to null if no serial number could be extracted."
        )
    )


class IntentClassificationResult(BaseModel):
    """
    Represents the output of the intent classification pipeline.
    The classifier decides what type of user query it is (pandas-agent, rca, or chit-chat),
    whether a pipeline can be triggered, and what additional information may be needed.
    """

    intent: str = Field(
        ...,
        description=(
            "The classified intent of the user query. "
            "Must be one of: 'pandas-agent', 'rca', or 'chit-chat'.\n"
            "- pandas-agent: Simple, exploratory, fact-based queries (metrics, counts, logs).\n"
            "- rca: Diagnostic/troubleshooting queries (why/reason/cause).\n"
            "- chit-chat: Non-technical, conversational, or when required fields are missing."
        )
    )

    missing_fields: Optional[List[str]] = Field(
        default_factory=list,
        description=(
            "List of required fields that are missing to trigger the pipeline.\n"
            "Examples:\n"
            "- ['serial_number'] if serial number is not yet provided.\n"
            "- ['time_window'] if RCA query lacks a timeframe.\n"
            "- [] if no fields are missing and the pipeline can be triggered."
        )
    )

    suggested_question: Optional[str] = Field(
        None,
        description=(
            "A concise, polite follow-up question to request missing information from the user.\n"
            "Examples:\n"
            "- 'Could you please provide your router's serial number?'\n"
            "- 'Could you specify the time window when the issue occurred (e.g., yesterday, last week)?'\n"
            "- null if no follow-up question is necessary."
        )
    )


class Verification(BaseModel):
    verification: Literal["VALID", "INVALID"] = Field(description="Verification result")

class RouterData(BaseModel):
    serial_number: str

class RebootsData(BaseModel):
    
    router_data: List[Dict] = Field(
        default=None,
        description="This is a dataframe containing all the router data"
    )
    serial_number: str = Field(description="Serial number of the router")
    


class customGraph(TypedDict):
    """
    Represents the state of the graph

    Attributes:
        question: Question
        generation_scratchpad: All intermediate steps of the LLM
        chat_history: All messages exchanged with the LLM
        intent_classification: Intent classification result
        bypass_intention: temporary variable to bypass intent classification during testing
        intermediate_result: intermediate result of the LLM
        final_result: final result of the LLM
        data: Dataframe of the router data
    """

    question: str
    serial_number: str
    generation_scratchpad: Annotated[Sequence[BaseMessage], add_messages]
    chat_history: Annotated[Sequence[BaseMessage], add_messages]
    intent_classification: IntentClassificationResult
    bypass_intention: bool
    intermediate_result: str
    final_result: str
    verification: Verification
    data: pd.DataFrame
    serialnumber: Optional[str]
    

