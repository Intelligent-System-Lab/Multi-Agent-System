
const API_URL = 'http://localhost:8000';
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const typingIndicator = document.getElementById('typing-indicator');
const errorMessage = document.getElementById('error-message');
const currentAgent = document.getElementById('current-agent');

let messageHistory = [
    {
        role: "assistant",
        content: "Hello! I'm your ADRD Care Assistant. How can I help you today?",
        // agent: "Medical Advisor"
        agent: "Help Desk",
    }
];

function renderInitialMessage() {
    const initialMessage = messageHistory[0];
    addMessage(initialMessage.content, false, initialMessage.agent);
}

function adjustTextareaHeight() {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 150) + 'px';
}

userInput.addEventListener('input', adjustTextareaHeight);

userInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendButton.addEventListener('click', sendMessage);

function showTypingIndicator() {
    typingIndicator.style.display = 'flex';
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
    typingIndicator.style.display = 'none';
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

function addMessage(content, isUser, agentName = '') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = content;
    
    const messageMeta = document.createElement('div');
    messageMeta.className = 'message-meta';
    
    if (isUser) {
        messageMeta.innerHTML = `<i class="fas fa-user"></i>You`;
    } else {
        messageMeta.innerHTML = `<i class="fas fa-robot"></i>${agentName}`;
        if (agentName) {
            currentAgent.textContent = agentName;
        }
    }
    
    messageDiv.appendChild(messageContent);
    messageDiv.appendChild(messageMeta);
    
    chatMessages.insertBefore(messageDiv, typingIndicator);
    
    setTimeout(() => {
        messageDiv.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }, 100);
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    userInput.disabled = true;
    sendButton.disabled = true;

    try {
        addMessage(message, true);
        messageHistory.push({
            role: "user",
            content: message
        });

        userInput.value = '';
        userInput.style.height = '60px';
        showTypingIndicator();

        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                history: messageHistory
            })
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();
        hideTypingIndicator();

        addMessage(data.response, false, data.agent);
        messageHistory.push({
            role: "assistant",
            content: data.response,
            agent: data.agent
        });

    } catch (error) {
        hideTypingIndicator();
        showError('Failed to send message. Please try again.');
        console.error('Error:', error);
    } finally {
        userInput.disabled = false;
        sendButton.disabled = false;
        userInput.focus();
    }
}

renderInitialMessage();
