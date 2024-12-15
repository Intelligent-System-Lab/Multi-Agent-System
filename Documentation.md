# ADRD Care System Architecture Documentation

## 1. System Overview

The ADRD Care System is a multi-agent conversation system that handles medical inquiries and appointment bookings. Here's how the components interact:

```
User Message → FastAPI → Orchestrator Agent → Specialized Agents → Response Generation → User
```

## 2. Key Components

### 2.1 Swarm Framework
- Base layer that handles AI model interactions
- Provides the `client.run()` method for executing agent prompts
- Manages conversation history and context

```python
client = Swarm() # Initialize Swarm client this framework is developing by openAI 
# When running an agent:
response = client.run(agent, conversation)
# Returns: structured response with messages array
```

### 2.2 Agent Classes

#### Base Agent Structure
```python
class Agent:
    def __init__(self):
        self.name = "Agent Name"
        self.instructions = "Agent Instructions"
        self.model = "gpt-4o-mini"
```

#### A. Orchestrator Agent
```python
class OrchestratorAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Orchestrator",
            instructions=ORCHESTRATOR_INSTRUCTIONS,
            model="gpt-4o-mini"
        )
```

Purpose:
- First point of contact for all messages
- Analyzes user intent
- Routes to appropriate specialized agent
- Returns JSON with routing information

Example Orchestrator Response:
```json
{
   "agent": "appointment",
   "intent": "book_appointment",
   "details": {
       "patient_name": "James Doe",
       "doctor_id": "dr_001",
       "preferred_date": "11/12/2024",
       "preferred_time": "09:00 AM",
       "request_type": "follow-up"
   },
   "missing_fields": []
}
```

#### B. Appointment Agent
```python
class AppointmentAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Appointment Coordinator",
            instructions=APPOINTMENT_AGENT_INSTRUCTIONS,
            model="gpt-4o-mini"
        )
```

Purpose:
- Handles appointment booking logic
- Manages scheduling workflow
- Interacts with appointment API
- Provides availability information

#### C. Medical Agent
```python
class MedicalAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Medical Advisor",
            instructions=MEDICAL_AGENT_INSTRUCTIONS,
            model="gpt-4o-mini"
        )
```

Purpose:
- Handles medical queries
- Provides health information
- Manages symptom discussions

## 3. Message Flow Process

### 3.1 Step-by-Step Flow

1. **User Input Reception**
```python
@app.post("/chat")
async def chat(request: MessageRequest):
    # Message enters system here
```

2. **Orchestrator Processing**
```python
# Process through orchestrator
orchestrator_response = await process_message(
    orchestrator_agent,
    request.message,
    request.history or []
)
```

3. **Intent Analysis**
The orchestrator analyzes the message and determines:
- Is it an appointment request?
- Is it a medical question?
- Is it unclear/needs clarification?

4. **Routing Decision**
Based on the analysis, routes to:
- Appointment Agent
- Medical Agent
- Stays with Orchestrator

5. **Specialized Agent Processing**
The chosen agent processes the request:
```python
if agent_name == "appointment":
    # Handle appointment logic
elif agent_name == "medical":
    # Handle medical query
```

6. **Response Generation**
```python
return MessageResponse(
    response=agent_response,
    agent=agent_name,
    context=context,
    suggestions=suggestions
)
```

### 3.2 Example Flow: Appointment Booking

1. User: "I need an appointment"

2. Orchestrator Analysis:
```json
{
   "agent": "appointment",
   "intent": "book_appointment",
   "details": {},
   "missing_fields": ["doctor_id", "preferred_date", "preferred_time"]
}
```

3. Appointment Agent Response:
"Which doctor would you like to see?"

4. User: "Dr. Smith on Monday"

5. Orchestrator Analysis:
```json
{
   "agent": "appointment",
   "intent": "book_appointment",
   "details": {
       "doctor_id": "dr_smith",
       "preferred_date": "Monday"
   },
   "missing_fields": ["preferred_time"]
}
```

6. Appointment Agent:
- Checks availability
- Responds with available times

## 4. Common Issues and Solutions

### 4.1 Agent Transition Issues
Problem: Losing context between agent transitions
Solution: Maintain conversation context in the state:
```python
conversation_states = {
    "conversation_id": {
        "current_agent": "appointment",
        "appointment_details": {...},
        "history": [...]
    }
}
```

### 4.2 Response Format Issues
Problem: Raw JSON visible to users
Solution: Always process agent responses:
```python
try:
    routing = json.loads(orchestrator_response)
    # Convert to user-friendly response
    response = format_response(routing)
except json.JSONDecodeError:
    response = "Could you please rephrase that?"
```

## 5. Testing and Validation

### 5.1 Agent Response Testing
```python
def test_orchestrator_response(message: str) -> bool:
    response = orchestrator_agent.process(message)
    return validate_response_format(response)
```

### 5.2 Flow Testing
```python
def test_appointment_flow():
    # Test complete appointment booking flow
    messages = [
        "I need an appointment",
        "with dr_001",
        "tomorrow at 9am"
    ]
    for msg in messages:
        response = process_message(msg)
        validate_response(response)
```

## 6. Best Practices

1. Always maintain conversation context
2. Never expose internal JSON to users
3. Handle partial information gracefully
4. Provide clear, user-friendly responses
5. Maintain consistent agent personas
6. Log all transitions and errors
7. Validate all API responses