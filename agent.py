# app.py 
"""
ADRD Care System - FastAPI Backend
Handles medical inquiries and appointment scheduling through specialized AI agents.
Main components:
- Chat routing and processing
- Appointment scheduling and management
- Medical query handling
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging
from datetime import datetime, timedelta
import json
import httpx
from swarm import Swarm
from orchestrator_agent import OrchestratorAgent
from medical_agent import MedicalAgent
from appointment_agent import AppointmentAgent

# Configure logging to track system behavior and errors
# Uses timestamp and logger name for better debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI with CORS enabled for front-end communication
app = FastAPI(title="ADRD Care System")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for specific origins in production if needed like /exmaple.com
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Swarm client for agent communication
client = Swarm()
# External API endpoint for appointment management
APPOINTMENT_API = "https://adrd-doctor-appointment-api.vercel.app/api/v1"

class MessageRequest(BaseModel):
    """
    Incoming message request structure
    message: User's input text
    history: Previous messages for context
    context: Additional metadata or state information
    """
    message: str
    history: Optional[List[dict]] = None
    context: Optional[Dict] = None

class MessageResponse(BaseModel):
    """
    Outgoing message response structure
    response: Agent's response text
    agent: Identifier of responding agent
    context: Updated context data
    suggestions: Optional next actions or suggestions
    """
    response: str
    agent: str
    context: Optional[Dict] = None
    suggestions: Optional[Dict] = None

# Initialize AI agents for different tasks
# Each agent specializes in specific type of user interaction
try:
    orchestrator_agent = OrchestratorAgent()  # Routes requests to appropriate agent
    medical_agent = MedicalAgent()            # Handles medical questions
    appointment_agent = AppointmentAgent()     # Manages scheduling
except Exception as e:
    logger.critical(f"Failed to initialize agents: {e}")
    raise

async def get_doctor_availability(doctor_id: str, date: str) -> Dict:
    """
    Fetch available appointment slots for specified doctor and date
    
    Logic flow:
    1. Query external appointment API
    2. Handle various failure cases (timeout, API errors)
    3. Return normalized availability data
    
    Returns dict with:
    - success: bool indicating if request succeeded
    - data: raw API response
    - available_times: list of available time slots
    - error: error message if request failed
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{APPOINTMENT_API}/doctor/availability",
                params={"doctor_id": doctor_id, "date": date}
            )
            
            response.raise_for_status()
            
            data = response.json()
            return {
                "success": True,
                "data": data,
                "available_times": data.get("available_times", [])
            }
    except httpx.TimeoutException:
        logger.error(f"Timeout while fetching availability for doctor {doctor_id}")
        return {"success": False, "error": "Service temporarily unavailable"}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} while fetching availability")
        return {"success": False, "error": "Unable to fetch availability"}
    except Exception as e:
        logger.error(f"Unexpected error fetching availability: {str(e)}")
        return {"success": False, "error": "An unexpected error occurred"}

async def check_next_available_slots(doctor_id: str, start_date: str, num_days: int = 5) -> List[Dict]:
    """
    Find next available appointment slots if requested date is full
    
    Process:
    1. Start from given date
    2. Check availability for next num_days
    3. Collect all available slots
    4. Track any errors for logging
    
    Returns list of dicts with:
    - date: date string
    - times: list of available times for that date
    """
    available_slots = []
    current_date = datetime.strptime(start_date, "%m/%d/%Y")
    errors = []
    
    # Check each day for availability
    for _ in range(num_days):
        date_str = current_date.strftime("%m/%d/%Y")
        availability = await get_doctor_availability(doctor_id, date_str)
        
        # If successful and slots available, add to results
        if availability.get("success"):
            if availability.get("available_times"):
                available_slots.append({
                    "date": date_str,
                    "times": availability["available_times"]
                })
        else:
            errors.append(f"Error checking {date_str}: {availability.get('error')}")
            
        current_date += timedelta(days=1)
    
    if errors:
        logger.warning(f"Errors while checking availability: {'; '.join(errors)}")
    
    return available_slots

async def book_appointment(details: dict) -> dict:
    """
    Attempt to book appointment with provided details
    
    Flow:
    1. Validate required booking fields
    2. Submit booking request
    3. Handle booking conflicts
    4. Provide alternative times if slot taken
    
    Returns dict with:
    - success: booking status
    - data: booking confirmation if successful
    - error: error message if failed
    - alternatives: alternative times if slot unavailable
    """
    # Validate all required fields present
    required_fields = ['doctor_id', 'preferred_date', 'preferred_time']
    missing_fields = [field for field in required_fields if not details.get(field)]
    
    if missing_fields:
        return {
            "success": False,
            "error": f"Missing required fields: {', '.join(missing_fields)}"
        }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{APPOINTMENT_API}/appointments/book",
                json=details
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully booked appointment for {details['doctor_id']}")
                return {"success": True, "data": response.json()}
            
            response_data = response.json()
            logger.info(f"Booking attempt failed: {response_data}")
            
            # Handle case where time slot was taken
            if response.status_code == 409:
                logger.warning("Requested time slot conflict - fetching alternatives")
                alternative_times = await get_doctor_availability(
                    details['doctor_id'],
                    details['preferred_date']
                )
                return {
                    "success": False,
                    "error": "Time slot no longer available",
                    "alternatives": alternative_times.get("available_times", [])
                }
                
            return {
                "success": False,
                "error": response_data.get("detail", "Booking failed")
            }
            
    except httpx.TimeoutException:
        logger.error("Timeout while booking appointment")
        return {"success": False, "error": "Service temporarily unavailable"}
    except Exception as e:
        logger.error(f"Error booking appointment: {e}")
        return {"success": False, "error": "An unexpected error occurred"}

async def process_message(agent, message: str, history: List[dict]) -> str:
    """
    Process message through specified agent with retry logic
    
    Flow:
    1. Add user message to conversation history
    2. Send to agent for processing
    3. Retry on failure up to max_retries
    4. Return agent's response
    """
    max_retries = 2
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            # Add new message to conversation history
            conversation = history + [{"role": "user", "content": message}]
            response = client.run(agent, conversation)
            return response.messages[-1]['content']
        except Exception as e:
            retry_count += 1
            logger.error(f"Attempt {retry_count} failed: {e}")
            if retry_count > max_retries:
                raise HTTPException(
                    status_code=500,
                    detail=f"Processing error after {max_retries} retries"
                )
            await asyncio.sleep(1)  # Brief delay before retry

@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    """
    Main chat endpoint handling all user interactions
    
    Processing flow:
    1. Route through orchestrator to determine intent
    2. For appointments:
       - Validate booking details
       - Check availability
       - Handle booking or provide alternatives
    3. For medical queries:
       - Route to medical agent
    4. Fall back to orchestrator for unclear intents
    """
    try:
        # Get routing decision from orchestrator
        orchestrator_response = await process_message(
            orchestrator_agent,
            request.message,
            request.history or []
        )

        # Parse orchestrator's decision
        try:
            routing = json.loads(orchestrator_response)
        except json.JSONDecodeError:
            logger.warning(f"Invalid orchestrator response format: {orchestrator_response}")
            routing = {"agent": "orchestrator", "response": orchestrator_response}

        agent_name = routing.get("agent", "orchestrator")
        
        # Handle appointment scheduling flow
        if agent_name == "appointment":
            details = routing.get("details", {})
            missing_fields = routing.get("missing_fields", [])

            # Check for required booking information
            if missing_fields:
                return MessageResponse(
                    response=f"I need these additional details to book your appointment: {', '.join(missing_fields)}. Please provide them.",
                    agent="Appointment Coordinator"
                )

            # Step 1: Check requested time availability
            availability = await get_doctor_availability(
                details["doctor_id"],
                details["preferred_date"]
            )

            if availability.get("success"):
                available_times = availability.get("data", {}).get("available_times", [])
                
                # Step 2: If preferred time available, try to book it
                if details["preferred_time"] in available_times:
                    booking_result = await book_appointment(details)
                    if booking_result.get("success"):
                        return MessageResponse(
                            response=f"Great! Your appointment with Dr. {details.get('doctor_name', details['doctor_id'])} is confirmed for {details['preferred_date']} at {details['preferred_time']}.",
                            agent="Appointment Coordinator"
                        )
                
                # Step 3: If preferred time unavailable, suggest alternatives
                if available_times:
                    response = (
                        f"I see that {details['preferred_time']} isn't available on {details['preferred_date']}. "
                        f"Here are available times:\n"
                    )
                    for time in available_times[:5]:
                        response += f"- {time}\n"
                    response += "\nWould you like me to book any of these times?"
                    
                    return MessageResponse(
                        response=response,
                        agent="Appointment Coordinator",
                        suggestions={"available_times": available_times, "date": details['preferred_date']}
                    )
                
                # Step 4: If no times available today, check next few days
                next_days = await check_next_available_slots(
                    details["doctor_id"],
                    details["preferred_date"]
                )
                
                if next_days:
                    response = (
                        f"I apologize, but there are no appointments available on {details['preferred_date']}. "
                        f"Here are the next available slots:\n\n"
                    )
                    for day in next_days[:3]:
                        response += f"For {day['date']}:\n"
                        for time in day['times'][:3]:
                            response += f"- {time}\n"
                        response += "\n"
                    response += "Would you like to book any of these times?"
                    
                    return MessageResponse(
                        response=response,
                        agent="Appointment Coordinator",
                        suggestions={"available_days": next_days}
                    )
            
            # Step 5: If all booking attempts fail, suggest alternatives
            return MessageResponse(
                response="I'm having trouble finding available appointments. Would you like to try a different date or see other doctors' availability?",
                agent="Appointment Coordinator"
            )

        # Handle medical questions
        elif agent_name == "medical":
            medical_response = await process_message(
                medical_agent,
                request.message,
                request.history or []
            )
            return MessageResponse(response=medical_response, agent="Medical Advisor")
        
        # Default handling for unclear requests
        else:
            return MessageResponse(
                response=routing.get("response", "Could you please clarify what you need help with?"),
                agent="orchestrator"
            )

    except Exception as e:
        # Log full error but return user-friendly message
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        return MessageResponse(
            response="I apologize, but I encountered an error. Please try again or rephrase your request.",
            agent="system"
        )

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring system status
    Returns status of all major system components
    Used by monitoring systems to check service health
    """
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "agents": {
                "orchestrator": True,
                "medical": True,
                "appointment": True
            },
            "version": "1.0.1",
            "api_status": "online"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

if __name__ == "__main__":
    import uvicorn
    import asyncio
    
    logger.info("Starting ADRD Care System server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)