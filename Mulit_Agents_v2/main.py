from __future__ import annotations

import os
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, field_validator
from fastapi import FastAPI, HTTPException, Body
from pydantic_ai import Agent
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Models
class RequestType(str, Enum):
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    NEW_PATIENT = "new_patient"

class AppointmentDetails(BaseModel):
    patient_name: str
    doctor_id: str
    preferred_date: str = Field(..., description="Date in MM/DD/YYYY format")
    preferred_time: str = Field(..., description="Time in HH:MM AM/PM format")
    request_type: RequestType

    @field_validator('preferred_date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, '%m/%d/%Y')
        except ValueError:
            raise ValueError('Date must be in MM/DD/YYYY format')
        return v

    @field_validator('preferred_time')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, '%I:%M %p')
        except ValueError:
            raise ValueError('Time must be in HH:MM AM/PM format')
        return v

class AgentResponse(BaseModel):
    agent: Literal["appointment", "medical", "greeting"]
    response: str

class MedicalQuery(BaseModel):
    query: str
    recommendations: Optional[List[str]] = None

# Chat API Models
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

# Agents
orchestrator_agent = Agent(
    "openai:gpt-4",
    system_prompt="""You are the ADRD care system orchestrator. 
    For any message, determine the type and respond appropriately.
    Maintain conversation context and guide users naturally.""",
    result_type=AgentResponse,
    retries=3
)

appointment_agent = Agent(
    "openai:gpt-4",
    system_prompt="""You are an appointment scheduling assistant for the ADRD care system.
    Guide the conversation naturally to gather appointment details.""",
    result_type=AppointmentDetails,
    retries=3
)

medical_agent = Agent(
    "openai:gpt-4",
    system_prompt="""You are a medical advisory assistant for ADRD patients.
    Provide clear medical information and recommendations.""",
    result_type=MedicalQuery,
    retries=3
)

# FastAPI App
app = FastAPI(title="ADRD Care System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
async def chat(request: ChatRequest = Body(...)):
    """Process a chat message and provide an appropriate response"""
    try:
        result = await orchestrator_agent.run(request.message)
        print(f"Orchestrator response: {result.data}")
        
        if result.data.agent == "appointment":
            details = await appointment_agent.run(request.message)
            return {"response": result.data.response, "details": details.data.dict()}
        
        elif result.data.agent == "medical":
            query = await medical_agent.run(request.message)
            print("agent name is")
            return {"response": result.data.response, "details": query.data.dict(), 'agent': result.data.agent.capitalize or "Orchestrator"}
        
        else:
            return {"response": result.data.response}
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)