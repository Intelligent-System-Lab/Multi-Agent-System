# Multi-Agent System for Healthcare Interactions

A practical implementation of a multi-agent system handling medical queries and appointment scheduling. This system demonstrates how specialized agents can work together to handle complex user interactions while maintaining context and ensuring appropriate task routing.

## System Architecture

### Agent Structure
The system uses three specialized agents working in coordination:

1. **Orchestrator Agent**
   - Acts as the primary router for all incoming queries
   - Analyzes user intent to determine appropriate specialist agent
   - Maintains conversation context across agent handoffs
   - Routes conversations based on intent classification

2. **Medical Agent**
   - Handles medical queries and health-related information
   - Provides responses within proper medical context
   - Maintains conversation history for contextual understanding

3. **Appointment Agent**
   - Manages scheduling logic
   - Handles availability checks and conflict resolution
   - Implements booking workflow with fallback options

### Inter-Agent Communication
The system uses the open-source Swarm library for agent orchestration:
```python
from swarm import Swarm
client = Swarm()

# Example of agent interaction
response = client.run(agent, conversation_history)
```

## Implementation Details

### Message Routing
```python
async def process_message(agent, message: str, history: List[dict]) -> str:
    conversation = history + [{"role": "user", "content": message}]
    response = client.run(agent, conversation)
    return response.messages[-1]['content']
```

The orchestrator uses this pattern to:
1. Maintain conversation history
2. Route to appropriate specialist
3. Handle agent responses

### Conversation Flow
1. User message comes in
2. Orchestrator analyzes intent
3. Routes to specialist (Medical/Appointment)
4. Specialist processes and responds
5. Context maintained throughout

## Local Development

### Setup
```bash
git clone [repo-url]
cd multi-agent-healthcare

python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

pip install -r requirements.txt
```

### Running the System
```bash
uvicorn app:app --reload --port 8001
```

### Environment Configuration
```bash
APPOINTMENT_API="your_api_endpoint"
```

## Testing

Written with pytest, focusing on agent interactions and routing logic:
```bash
pytest tests/
```

## Common Implementation Patterns

### Agent Routing Logic
```python
if agent_name == "medical":
    response = await process_message(medical_agent, message, history)
elif agent_name == "appointment":
    response = await appointment_flow(details, history)
```

### Error Handling
- Retry logic for agent communication
- Fallback responses for unclear intents
- Context preservation during errors

## Contributing

If you're working on extending the agent system:

1. Follow the existing agent patterns
2. Maintain conversation context
3. Add tests for new agent interactions
4. Document agent communication patterns
5. Note: I'm currently working on changing the framework we're using.
## Known Limitations

- Agent context is session-based
- No permanent memory between sessions
- Sequential agent processing only


## Questions?

Check the `#lab` Slack channel or raise an issue.