serialnumber_extractor_prompt = """
Extract the router serial number (an alphanumeric identifier) from the provided chat history and the user's current question.

Rules:
- Serial numbers are usually alphanumeric and may be long (examples: 2351ADTRJ, 90100000000V412000536). They can also be long digit-only sequences (>8 digits).
- First look for explicit cues in the text such as "serial", "serial number", "sn", "s/n", "Serial:", "Serial number is", "device id", "deviceid".
- Prefer values that appear immediately after those cues. If none are found, look for alphanumeric tokens of length >= 8.
- If you find exactly one strong candidate, return it. If none found, return null and provide a succinct `suggested_question` to request it.
- If you find multiple plausible candidates, list them and provide a short `suggested_question` asking the user to clarify which one to use.

Input:
Chat history:
{chat_history}

User question:
{user_question}

Output:
{output_parser}

"""

intent_classification_template = """
You are an intent classifier for router-related user queries.  
Your task is to classify each query into exactly one of the following intents and decide whether the relevant pipeline may be triggered immediately.

INTENTS

1. pandas-agent (Data Exploration & Retrieval)  
   - **Purpose**: Simple, fact-based data queries. Asking WHAT/WHEN/HOW MANY/SHOW ME data points.
   - **Examples**: 
     * "When did my router reboot last time?"
     * "What is the CPU usage for router X?"
     * "Show me the number of reboots last week"
     * "How many times did router Y disconnect?"
     * "When was the last reboot?"
   - **Keywords**: what, when, how many, show me, list, count, get, fetch
   - **NOT RCA**: These are NOT asking WHY/CAUSE/REASON
   - **Preconditions**: Requires **serial_number**

2. rca (Root Cause Analysis & Diagnostics)  
   - **Purpose**: Analytical queries asking WHY something happened, CAUSE of issues, REASONS for problems
   - **Examples**: 
     * "Why is my internet slow?"
     * "What caused the router to reboot?"
     * "Explain the reason for frequent disconnections"
     * "Diagnose why CPU is high"
   - **Keywords**: why, cause, reason, explain, diagnose, analyze
   - **Preconditions**: Requires **serial_number** AND **time_window** (specific time/event)

3. chit-chat  
   - **Purpose**: Non-technical conversation, greetings, providing information, or when required fields are missing
   - **Examples**: 
     * "Hi, how are you?"
     * "Thanks!"
     * "My serial is 90100000000V412000536" (providing info)
     * Any query missing required fields
   
---

**CRITICAL: pandas-agent vs RCA distinction:**
- "**WHEN** did X happen?" → pandas-agent (data retrieval)
- "**WHY** did X happen?" → rca (analysis)
- "**HOW MANY** times did X happen?" → pandas-agent
- "**WHAT CAUSED** X?" → rca

---

Chat history so far:
{chat_history}

serial_number:
{serial_number}

Current user query:
{user_query}

---

### Unanswered Question Logic

1. **Check for unanswered technical questions** in `{chat_history}`:
   - A question is "unanswered" if it has NO subsequent assistant reply that resolves it
   
2. **If an unanswered question is now answerable** (all required fields present):
   - **Classify based on that PRIOR question**, not the current `{user_query}`
   - Determine if the prior question is pandas-agent or rca
   - Set `missing_fields` to `[]` and `suggested_question` to `null`

3. **If still missing fields**:
   - Classify as chit-chat
   - Provide `suggested_question` to collect missing info

---

### Output Schema
Return **only** JSON (no extra text):

{{
  "intent": "<pandas-agent | rca | chit-chat>",
  "missing_fields": [ "<field names>" ],
  "suggested_question": "<string|null>"
}}

---

### Few-Shot Examples

#### Example 1 — pandas-agent query, missing serial
Chat history: []  
Query: "When did my router reboot last time?"

Output:
{{
  "intent": "chit-chat",
  "missing_fields": ["serial_number"],
  "suggested_question": "Could you please provide your router's serial number so I can check when it last rebooted?"
}}

---

#### Example 2 — pandas-agent, serial NOW provided (ANSWERS PRIOR QUESTION)
Chat history: [
  "User: When did my router reboot last time?",
  "Assistant: Could you please provide your router's serial number?"
]
serial_number: "90100000000V412000536"
Query: "90100000000V412000536 is my router number"

Explanation: Prior question "When did my router reboot" is pandas-agent query, now answerable with serial.

Output:
{{
  "intent": "pandas-agent",
  "missing_fields": [],
  "suggested_question": null
}}

---

#### Example 3 — Direct pandas-agent with serial
Chat history: ["User: My router serial is 90100000000V412000536"]  
Query: "What was the CPU usage yesterday?"

Output:
{{
  "intent": "pandas-agent",
  "missing_fields": [],
  "suggested_question": null
}}

---

#### Example 4 — RCA query, missing time_window
Chat history: ["User: My router serial is 90100000000V412000536"]  
Query: "Why is my internet slow?"

Output:
{{
  "intent": "chit-chat",
  "missing_fields": ["time_window"],
  "suggested_question": "Could you specify when you experienced slow internet (e.g., 'yesterday evening', 'last week', specific date)?"
}}

---

#### Example 5 — RCA now answerable (serial + time provided)
Chat history: [
  "User: Why did my router reboot?",
  "Assistant: I need your serial number.",
  "User: My serial is 90100000000V412000536",
  "User: The reboot happened yesterday at 03:00"
]  
Query: "Thanks"

Explanation: Prior "Why" question is RCA, now answerable with both serial AND time.

Output:
{{
  "intent": "rca",
  "missing_fields": [],
  "suggested_question": null
}}

---

#### Example 6 — Multiple unanswered, pick most recent answerable pandas-agent
Chat history: [
  "User: What was the CPU usage last week?",
  "Assistant: Please provide serial.",
  "User: When did it last reboot?",
  "Assistant: I still need the serial number."
]
serial_number: "2351ADTRJ"
Query: "My serial is 2351ADTRJ"

Explanation: Both prior questions are pandas-agent and now answerable. Pick most recent: "When did it last reboot?"

Output:
{{
  "intent": "pandas-agent",
  "missing_fields": [],
  "suggested_question": null
}}

---

#### Example 7 — Just greeting/info, no prior unanswered
Chat history: []  
Query: "Hi, how are you?"

Output:
{{
  "intent": "chit-chat",
  "missing_fields": [],
  "suggested_question": null
}}

---

Now classify:

Chat history:
{chat_history}

Query: {user_query}

Return JSON only.  
Output: {output_parser}
"""