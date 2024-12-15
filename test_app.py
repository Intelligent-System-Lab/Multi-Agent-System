import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from app import app, get_doctor_availability, check_next_available_slots, book_appointment

client = TestClient(app)

# Mock data for tests
MOCK_AVAILABILITY = {
    "success": True,
    "data": {
        "doctor_id": "dr_001",
        "date": "12/15/2024",
        "available_times": ["09:00", "10:00", "14:00"]
    },
    "available_times": ["09:00", "10:00", "14:00"]
}

MOCK_BOOKING_SUCCESS = {
    "success": True,
    "data": {
        "appointment_id": "apt123",
        "doctor_id": "doc123",
        "date": "12/15/2024",
        "time": "09:00"
    }
}

@pytest.fixture
def mock_swarm():
    with patch('app.Swarm') as mock:
        yield mock

@pytest.fixture
def mock_httpx():
    with patch('httpx.AsyncClient') as mock:
        yield mock

@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint returns correct status"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert all(data["agents"].values())

@pytest.mark.asyncio
async def test_get_doctor_availability(mock_httpx):
    """Test fetching doctor availability"""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = MOCK_AVAILABILITY["data"]
    mock_response.raise_for_status.return_value = None
    
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_httpx.return_value.__aenter__.return_value = mock_client

    # Test successful availability fetch
    result = await get_doctor_availability("dr_002", "12/15/2024")
    assert result["success"] == True
    assert "available_times" in result
    assert len(result["available_times"]) == 3

@pytest.mark.asyncio
async def test_check_next_available_slots(mock_httpx):
    """Test checking multiple days for availability"""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = MOCK_AVAILABILITY["data"]
    mock_response.raise_for_status.return_value = None
    
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_httpx.return_value.__aenter__.return_value = mock_client

    # Test checking next 3 days
    result = await check_next_available_slots("dr_002", "12/15/2024", num_days=3)
    assert len(result) == 3
    assert all("date" in day and "times" in day for day in result)

@pytest.mark.asyncio
async def test_book_appointment(mock_httpx):
    """Test appointment booking process"""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_BOOKING_SUCCESS["data"]
    
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_httpx.return_value.__aenter__.return_value = mock_client

    # Test successful booking
    booking_details = {
        "doctor_id": "dr_001",
        "preferred_date": "12/15/2024",
        "preferred_time": "09:00"
    }
    result = await book_appointment(booking_details)
    assert result["success"] == True
    assert "appointment_id" in result["data"]

@pytest.mark.asyncio
async def test_chat_endpoint_medical(mock_swarm):
    """Test chat endpoint with medical query"""
    # Setup mock agent response
    mock_medical_response = '{"response": "This is a medical response", "agent": "medical"}'
    mock_swarm_instance = MagicMock()
    mock_swarm_instance.run.return_value.messages = [{"content": mock_medical_response}]
    mock_swarm.return_value = mock_swarm_instance

    # Test medical query
    response = client.post("/chat", json={
        "message": "What are the symptoms of ADRD?",
        "history": []
    })
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "medical" or data["agent"] == "Medical Advisor"

@pytest.mark.asyncio
async def test_chat_endpoint_appointment(mock_swarm, mock_httpx):
    """Test chat endpoint with appointment request"""
    # Setup mock responses
    mock_orchestrator_response = '{"agent": "appointment", "details": {"doctor_id": "dr_003", "preferred_date": "12/15/2024", "preferred_time": "09:00"}}'
    mock_swarm_instance = MagicMock()
    mock_swarm_instance.run.return_value.messages = [{"content": mock_orchestrator_response}]
    mock_swarm.return_value = mock_swarm_instance

    # Setup mock http response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_AVAILABILITY["data"]
    mock_response.raise_for_status.return_value = None
    
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.post.return_value = mock_response
    mock_httpx.return_value.__aenter__.return_value = mock_client

    # Test appointment request
    response = client.post("/chat", json={
        "message": "I need to schedule an appointment",
        "history": []
    })
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "Appointment Coordinator"

@pytest.mark.asyncio
async def test_error_handling(mock_httpx):
    """Test error handling in availability check"""
    # Setup mock error response
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("API Error")
    mock_httpx.return_value.__aenter__.return_value = mock_client

    # Test error handling
    result = await get_doctor_availability("dr_003", "12/15/2024")
    assert result["success"] == False
    assert "error" in result

if __name__ == "__main__":
    pytest.main(["-v"])