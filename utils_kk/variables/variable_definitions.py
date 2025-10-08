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

    matched_columns: List[str] = Field(
        default_factory=list,
        description=(
            "List of telemetry dataset column names matching the user’s request. "
            "Should be empty if `status` is UNAVAILABLE."
        ),
    )

    explanation: str = Field(
        description=(
            "Concise explanation of availability determination. "
            "Should specify what metrics exist and how they relate to the user's question."
        ),
        examples=["CPU utilization (%) and memory utilization (%) are directly available."]
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
    generation_scratchpad: Annotated[Sequence[BaseMessage], add_messages]
    chat_history: Annotated[Sequence[BaseMessage], add_messages]
    intent_classification: IntentClassificationResult
    bypass_intention: bool
    intermediate_result: str
    final_result: str
    verification: Verification
    data: pd.DataFrame
    serialnumber: Optional[str]
    matched_columns: Optional[List[str]]
    explanation: str
    

class FeatureValidationResult(BaseModel):
    """
    Represents the result of validating whether specific router telemetry features
    (requested by the user) exist in the available dataset.

    This model is used by the Feature Validation Assistant to determine
    if user-requested metrics can be directly queried from the router telemetry data.

    """

    status: Literal["AVAILABLE", "PARTIALLY_AVAILABLE", "UNAVAILABLE"] = Field(
        description=(
            "Indicates overall feature availability in the dataset.\n"
            "- AVAILABLE: All metrics are found\n"
            "- PARTIALLY_AVAILABLE: Some found, some missing\n"
            "- UNAVAILABLE: None found"
        )
    )

    matched_columns: List[str] = Field(
        default_factory=list,
        description=(
            "List of telemetry dataset column names matching the user’s request. "
            "Should be empty if `status` is UNAVAILABLE."
        ),
    )

    explanation: str = Field(
        description=(
            "Concise explanation of availability determination. "
            "Should specify what metrics exist and how they relate to the user's question."
        ),
        examples=["CPU utilization (%) and memory utilization (%) are directly available."]
    )

    suggested_response: Optional[str] = Field(
        default=None,
        description=(
            "Optional clarification or guidance message to return to the user. "
            "Only populated when status is UNAVAILABLE or clarification is helpful."
        ),
        examples=[None, "Ping latency data is unavailable, but I can analyze signal levels instead."]
    )

