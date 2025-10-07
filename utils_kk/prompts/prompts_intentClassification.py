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
You are an **Intent Classifier** for broadband router-related user queries.  
Your task is to:
1. Classify each query into exactly one of the following intents: **pandas-agent**, **rca**, or **chit-chat**.  
2. Decide whether the relevant pipeline can be triggered immediately.  
3. Verify that the requested information exists in the available telemetry dataset using the provided column reference.

---

## UNDERSTANDING FEATURES:

**CRITICAL: Before answering any question, you MUST thoroughly review the KEY COLUMNS REFERENCE dictionary below.**

The KEY COLUMNS REFERENCE is a comprehensive dictionary where:
- **Key** = Actual feature/column name in the dataframe
- **Value** = Human-readable description of what that feature represents

**Instructions for using KEY COLUMNS REFERENCE:**

1. **Always consult this dictionary first** when interpreting user questions about router metrics
2. **Identify the correct column name** by matching the user's question to the feature descriptions
4. **Understand the context** of each feature by reading its description carefully
5. **Check related features** within the same category (e.g., all WIFI RADIO 1 features together)
6. **Pay attention to units** mentioned in descriptions (%, dBm, seconds, etc.)
7. **Note the delta fields** - features ending with "_delta" represent changes since last sample

**Common mistakes to avoid:**
- Using description text instead of actual column names in queries
- Confusing similar features (e.g., wifi_radio_1 vs wifi_radio_2)
- Ignoring units when interpreting values
- Missing relevant related columns that provide additional context

---

KEY_COLUMNS_REFERENCE: {{
    # ============= IDENTITY & TEMPORAL =============
    'serialnumber': 'Router/device ID',
    'date': 'Date of telemetry record',
    'time': 'Time of telemetry record',

    # ============= REBOOT INDICATORS =============
    'is_reboot': 'Reboot flag (1=reboot, 0=no reboot)',
    'last_reboot_reason_split': 'Categorized reason for last reboot',
    'deviceuptime': 'Seconds since last reboot',
    'reboot_firmware_flag': 'Reboot due to firmware update',
    'telemetry_restart': 'Telemetry service restart flag',

    # ============= CPU & MEMORY =============
    'cpuusage': 'CPU utilization (%)',
    'cpu_temp_split': 'CPU temperature (°C)',
    'memusage': 'Memory utilization (%)',
    'flash_usage_nvram_split_perc': 'NVRAM flash usage (%)',

    # ============= GPON / OPTICAL =============
    'gpon_rxsignallevel': 'GPON received optical power (dBm)',
    'gpon_txsignallevel': 'GPON transmitted optical power (dBm)',
    'gpon_connectionstatus': 'GPON link status (Up/Down)',
    'gpon_registrationstate': 'ONU registration state',
    'gpon_signalfail': 'Optical signal failure indicator',
    'gpon_signaldegrade': 'Optical signal degradation indicator',

    # ============= WIFI RADIO 1 (2.4 GHz) =============
    'wifi_radio_1_status': 'Radio 1 status (Up/Down)',
    'wifi_radio_1_channel': 'Operating channel',
    'change_wifi_radio_1_channel': 'Channel change event flag',
    'wifi_radio_1_stats_x_comcast_com_channelutilization': 'Channel utilization (%)',
    'wifi_radio_1_stats_noise': 'Noise floor (dBm)',
    'wifi_radio_1_operatingchannelbandwidth': 'Channel width (MHz)',

    # ============= WIFI RADIO 2 (5 GHz) =============
    'wifi_radio_2_status': 'Radio 2 status (Up/Down)',
    'wifi_radio_2_channel': 'Operating channel',
    'change_wifi_radio_2_channel': 'Channel change event flag',
    'wifi_radio_2_stats_x_comcast_com_channelutilization': 'Channel utilization (%)',
    'wifi_radio_2_stats_noise': 'Noise floor (dBm)',
    'wifi_radio_2_operatingchannelbandwidth': 'Channel width (MHz)',

    # ============= WIFI ACCESS POINTS =============
    'wifi_accesspoint_1_status': 'AP1 status (Enabled/Disabled)',
    'wifi_accesspoint_1_associateddevicenumberofentries': 'AP1 connected devices',
    'wifi_accesspoint_2_status': 'AP2 status (Enabled/Disabled)',
    'wifi_accesspoint_2_associateddevicenumberofentries': 'AP2 connected devices',

    # ============= WIFI SSID 1 (DELTAS) =============
    'wifi_ssid_1_status': 'SSID1 broadcast status',
    'wifi_ssid_1_stats_retranscount': 'Retransmissions (count)',
    'wifi_ssid_1_stats_errorssent_delta': 'TX errors since last sample',
    'wifi_ssid_1_stats_errorsreceived_delta': 'RX errors since last sample',
    'wifi_ssid_1_stats_bytessent_delta': 'Bytes sent since last sample',
    'wifi_ssid_1_stats_bytesreceived_delta': 'Bytes received since last sample',
    'wifi_ssid_1_stats_packetssent_delta': 'Packets sent since last sample',
    'wifi_ssid_1_stats_packetsreceived_delta': 'Packets received since last sample',

    # ============= WIFI SSID 2 (DELTAS) =============
    'wifi_ssid_2_status': 'SSID2 broadcast status',
    'wifi_ssid_2_stats_retranscount': 'Retransmissions (count)',
    'wifi_ssid_2_stats_errorssent_delta': 'TX errors since last sample',
    'wifi_ssid_2_stats_errorsreceived_delta': 'RX errors since last sample',
    'wifi_ssid_2_stats_bytessent_delta': 'Bytes sent since last sample',
    'wifi_ssid_2_stats_bytesreceived_delta': 'Bytes received since last sample',
    'wifi_ssid_2_stats_packetssent_delta': 'Packets sent since last sample',
    'wifi_ssid_2_stats_packetsreceived_delta': 'Packets received since last sample',

    # ============= WIFI AGGREGATED =============
    'total_band_change': 'Total band/channel switch events',
    'avg_signalstrength': 'Average client RSSI (dBm)',
    'min_signalstrength': 'Minimum client RSSI (dBm)',
    'avg_lastdatadownlinkrate': 'Average client downlink rate',
    'avg_lastdatauplinkrate': 'Average client uplink rate',
    'min_lastdatadownlinkrate': 'Minimum client downlink rate',
    'min_lastdatauplinkrate': 'Minimum client uplink rate',

    # ============= PPP INTERFACE (DELTAS) =============
    'ppp_interface_1_status': 'PPP interface status (Up/Down)',
    'ppp_interface_1_stats_errorssent_delta': 'PPP TX errors since last sample',
    'ppp_interface_1_stats_errorsreceived_delta': 'PPP RX errors since last sample',

    # ============= IP INTERFACE (DELTAS) =============
    'ip_interface_1_status': 'IP interface status (Up/Down)',
    'ip_interface_1_lastchange_flag': 'IP interface state change flag',
    'ip_interface_1_stats_errorssent_delta': 'IP TX errors since last sample',
    'ip_interface_1_stats_errorsreceived_delta': 'IP RX errors since last sample',

    # ============= ETHERNET LINK (DELTAS) =============
    'ethernet_link_1_status': 'Ethernet link status (Up/Down)',
    'ethernet_link_1_lastchange_flag': 'Ethernet link state change flag',
    'ethernet_link_1_stats_errorssent_delta': 'Ethernet TX errors since last sample',
    'ethernet_link_1_stats_errorsreceived_delta': 'Ethernet RX errors since last sample',

    # ============= DSL LINE (DELTAS) =============
    'dsl_line_1_stats_bytessent_delta': 'DSL bytes sent since last sample',
    'dsl_line_1_stats_bytesreceived_delta': 'DSL bytes received since last sample',
    'dsl_line_1_stats_errorssent_delta': 'DSL TX errors since last sample',
    'dsl_line_1_stats_errorsreceived_delta': 'DSL RX errors since last sample',

    # ============= WAN (DELTAS) =============
    'wan_bytessent_delta': 'WAN bytes sent since last sample',
    'wan_bytesreceived_delta': 'WAN bytes received since last sample',
    'wan_errorssent_delta': 'WAN TX errors since last sample',
    'wan_errorsreceived_delta': 'WAN RX errors since last sample',

    # ============= DHCP & NAT =============
    'dhcpv4_server_pool_1_status': 'DHCP server pool status',
    'nat_portmappingnoofentries': 'Active NAT port mappings',

    # ============= DEVICE LOAD & FLAGS =============
    'hosts_connected_device_number': 'Total connected client devices',
    'empty_last_telemetry': 'Previous telemetry missing/empty flag',
}}

---

## INTENTS

### 1. pandas-agent (Data Exploration & Retrieval)
- **Purpose:** Handles simple, fact-based queries that explore or retrieve data — *WHAT*, *WHEN*, *HOW MANY*, *SHOW ME* types.
- **Examples:**
  * "When did my router reboot last time?"
  * "What is the CPU usage for router X?"
  * "Show me the number of reboots last week."
  * "How many times did router Y disconnect?"
  * "What is the signal strength?"
- **Keywords:** what, when, how many, show me, list, count, get, fetch  
- **Precondition:** Requires **serial_number**  
- **Column Validation:** The metric or keyword in the question must match or relate to at least one column in the KEY COLUMNS REFERENCE.

---

### 2. rca (Root Cause Analysis & Diagnostics)
- **Purpose:** Handles analytical or diagnostic queries asking *WHY*, *CAUSE*, *REASON*, or *EXPLAIN* about router behavior.
- **Examples:**
  * "Why is my internet slow?"
  * "What caused the router to reboot?"
  * "Explain the reason for frequent disconnections."
  * "Diagnose why CPU usage is high."
- **Keywords:** why, cause, reason, explain, diagnose, analyze  
- **Precondition:** Requires both **serial_number** and **time_window**  
- **Column Validation:** The metric being analyzed (e.g., CPU, signal, reboot, Wi-Fi) must be present in KEY COLUMNS REFERENCE.

---

### 3. chit-chat
- **Purpose:** Non-technical conversation or cases where required details are missing.  
- Includes greetings, acknowledgments, small talk, or questions about unsupported topics.  
- **Examples:**
  * "Hi, how are you?"
  * "Thanks!"
  * "My serial number is 90100000000V412000536"
  * Any query missing required fields or referring to unknown data metrics.

---

## 🧠 Decision Logic

1. **Column Validation Check**  
   - Parse the query to detect referenced metrics.  
   - Cross-check against the KEY COLUMNS REFERENCE.  
   - If no match → classify as **chit-chat** and set a `suggested_question` asking for clarification.

2. **Unanswered Question Logic**  
   - Review {chat_history} to identify any **previous unanswered technical question**.  
   - If a prior question is now answerable (required fields now provided):
     - Classify based on that **previous question**, not {user_query}.
     - Set `missing_fields` to [] and `suggested_question` to null.

3. **Intent Resolution**
   - If query fits pandas-agent → check for **serial_number**.  
   - If query fits rca → check for **serial_number** and **time_window**.  
   - If preconditions fail → downgrade to **chit-chat** and suggest a question to gather missing fields.

---

### Important: How to interpret chat history

- Do **not** treat your own previous `suggested_question` as an unanswered query.
  Example: if chat history contains `"Assistant: Could you clarify what you mean by..."`,  
  and the user hasn’t replied yet — that is **not** an unanswered user question.  
  Wait for the user’s next natural-language query before re-evaluating.

---

### ⚙️ Output Schema
Return **only** a JSON object (no explanations or prose):

{{
  "intent": "<pandas-agent | rca | chit-chat>",
  "missing_fields": ["<field names>"],
  "suggested_question": "<string|null>"
}}

---

### 🧩 Few-Shot Examples

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

#### Example 2 — pandas-agent, now answerable
Chat history: [
  "User: When did my router reboot last time?",
  "Assistant: Could you please provide your router's serial number?"
]
serial_number: "90100000000V412000536"
Query: "90100000000V412000536 is my router number"

Output:
{{
  "intent": "pandas-agent",
  "missing_fields": [],
  "suggested_question": null
}}

---

#### Example 3 — RCA query, missing time_window
Chat history: ["User: My router serial is 90100000000V412000536"]  
Query: "Why is my internet slow?"

Output:
{{
  "intent": "chit-chat",
  "missing_fields": ["time_window"],
  "suggested_question": "Could you specify when you experienced slow internet (e.g., 'yesterday evening', 'last week', or a specific date)?"
}}

---

#### Example 4 — RCA now answerable
Chat history: [
  "User: Why did my router reboot?",
  "Assistant: I need your serial number.",
  "User: My serial is 90100000000V412000536",
  "User: The reboot happened yesterday at 03:00"
]
Query: "Thanks"

Output:
{{
  "intent": "rca",
  "missing_fields": [],
  "suggested_question": null
}}

---

#### Example 5 — Metric not supported
Chat history: []  
Query: "What is the WiFi download latency?"

Output:
{{
  "intent": "chit-chat",
  "missing_fields": [],
  "suggested_question": "I’m not sure what you mean by WiFi download latency. Could you specify if you meant signal strength, throughput, or another parameter?"
}}

---

### Now classify the following user query according to the schema:

Chat history:
{chat_history}

Query:
{user_query}

Return only JSON.  
Output: {output_parser}
"""