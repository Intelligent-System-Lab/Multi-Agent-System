
# 1

User: "make appointment with dr_001 for November 15 2024 at 9am for new patient John Smith"
Expected Response Format:
{
    "agent": "appointment",
    "intent": "book_appointment", 
    "details": {
        "patient_name": "John Smith",
        "doctor_id": "dr_001",
        "preferred_date": "11/15/2024",
        "preferred_time": "09:00 AM",
        "request_type": "new_patient"
    },
    "missing_fields": []
}

# 2

User: "need to schedule with dr_002"
Expected: System asks for patient name, date, time, and appointment type

User: "it's for James Doe, next Tuesday"
Expected: System asks for time and appointment type

User: "10am follow-up"
Expected Response Format:
{
    "agent": "appointment",
    "intent": "book_appointment",
    "details": {
        "patient_name": "James Doe",
        "doctor_id": "dr_002",
        "preferred_date": "11/12/2024",
        "preferred_time": "10:00 AM",
        "request_type": "follow-up"
    },
    "missing_fields": []
}


# 3

User: "need appointment dr_003 at 11am"
Expected: System asks for:
- Patient name
- Preferred date
- Appointment type


# 4 
User: "need to book with dr_001"
Expected: System asks for patient name, date, time, and appointment type

User: "for Mike Brown consultation"
Expected: System asks for preferred date and time

User: "November 13 2024 3pm"
Expected Response Format:
{
    "agent": "appointment",
    "intent": "book_appointment",
    "details": {
        "patient_name": "Mike Brown",
        "doctor_id": "dr_001",
        "preferred_date": "11/13/2024",
        "preferred_time": "03:00 PM",
        "request_type": "consultation"
    },
    "missing_fields": []
}


User: "I need two appointments please"
Expected Interaction:
System: "I'll help you book those appointments. Let's start with the first one. Which doctor would you like to see?"

User: "First one with dr_002 for Tommy - follow up"
Expected Interaction:
System: "When would you like to schedule Tommy's follow-up appointment with dr_002?"

User: "Thursday at 11am"
Expected Interaction:
System: Books first appointment and says "Great, I've booked Tommy's appointment for Thursday at 11:00 AM. Now, let's book the second appointment. Which doctor would you like to see?"

User: "dr_001 for Lisa, new patient"
Expected Interaction:
System: "When would you like to schedule Lisa's appointment with dr_001?"




