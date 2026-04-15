// --- DOM Elements ---
const chatHistory = document.getElementById('chat-history');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// --- Core Functions ---

// Function to add a message bubble to the chat window
function addMessage(text, sender) {
    // Create a new div element for the message
    const messageDiv = document.createElement('div');
    
    // Add the base class and the sender-specific class (user-msg or ai-msg)
    messageDiv.classList.add('message');
    messageDiv.classList.add(sender === 'user' ? 'user-msg' : 'ai-msg');
    
    // Set the text content
    messageDiv.innerText = text;
    
    // Append it to the chat history container
    chatHistory.appendChild(messageDiv);
    
    // Auto-scroll to the bottom so the newest message is always visible
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Global variable to keep track of the current chat file
let currentSessionId = ""; 

// Function to handle sending a message to the Flask API
async function handleSend() {
    const text = userInput.value.trim();
    if (text === '') return;
    
    // 1. Add User's message to UI and clear input
    addMessage(text, 'user');
    userInput.value = '';
    
    try {
        // 2. Send the message to your Flask backend
        const response = await fetch('http://localhost:5000/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: text,
                session_id: currentSessionId // Send the current ID to the server
            }) 
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const data = await response.json();
        
        // 3. Handle the AI's response
        if (data.response) {
            addMessage(data.response, 'ai');
            
            // --- THE LIVE UPDATE MAGIC ---
            // Check if the backend auto-renamed the session or created a new one
            if (data.session_id && data.session_id !== currentSessionId) {
                currentSessionId = data.session_id; // Update our tracker
                
                // 1. Refresh the sidebar history list instantly!
                fetchHistory();
                
                // 2. Clean up the ID to make a pretty title (e.g., "Exam_Anxiety_1245" -> "Exam Anxiety")
                const displayName = currentSessionId.replace(/_\d{4}$/, '').replace(/_/g, ' ');
                
                // 3. Update the chat header title live!
                currentSessionTitle.innerText = displayName;
            }

        } else if (data.error) {
            addMessage("Error: " + data.error, 'ai');
        }

    } catch (error) {
        console.error('Error:', error);
        addMessage("Sorry, I'm having trouble connecting to my backend.", 'ai');
    }
}

// --- Event Listeners ---

// Listen for a click on the Send button
sendBtn.addEventListener('click', handleSend);

// Listen for the "Enter" key in the text area
userInput.addEventListener('keypress', function(event) {
    // If Enter is pressed without the Shift key, send the message
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault(); // Prevents a new line from being added
        handleSend();
    }
});

// --- SIDEBAR: HISTORY LOGIC ---
const historyList = document.getElementById('history-list');
const currentSessionTitle = document.getElementById('current-session-title');

// Fetch all past sessions and populate the sidebar
async function fetchHistory() {
    const res = await fetch('http://localhost:5000/api/sessions');
    const sessions = await res.json();
    
    historyList.innerHTML = '';
    sessions.forEach(session => {
        const li = document.createElement('li');
        li.innerText = session.name;
        // When clicked, load that specific chat
        li.onclick = () => loadSession(session.id, session.name);
        historyList.appendChild(li);
    });
}

// Load a specific past session into the chat window
async function loadSession(sessionId, displayName) {
    currentSessionId = sessionId;
    currentSessionTitle.innerText = displayName;
    
    const res = await fetch(`http://localhost:5000/api/session/${sessionId}`);
    const data = await res.json();
    
    chatHistory.innerHTML = ''; // Clear the screen
    data.messages.forEach(msg => {
        addMessage(msg.content, msg.role === 'user' ? 'user' : 'ai');
    });
}

// Wire up the "+ New Chat" button
document.querySelector('.new-chat-btn').addEventListener('click', () => {
    currentSessionId = "";
    currentSessionTitle.innerText = "New Session";
    chatHistory.innerHTML = '<div class="welcome-message"><p>Hello. I am Thera-RAG. How are you feeling today?</p></div>';
});

// --- SIDEBAR: MOOD TRACKER LOGIC ---
const moodSlider = document.getElementById('mood-slider');
const moodVal = document.getElementById('mood-value');
const logMoodBtn = document.getElementById('log-mood-btn');
let moodChartInstance = null;

// Update the number text when the slider moves
moodSlider.oninput = () => { moodVal.innerText = moodSlider.value; }

// Save the mood when the button is clicked
logMoodBtn.onclick = async () => {
    await fetch('http://localhost:5000/api/mood', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ score: parseInt(moodSlider.value) })
    });
    logMoodBtn.innerText = "Saved!";
    setTimeout(() => logMoodBtn.innerText = "Log Mood", 2000);
    renderChart(); // Refresh the chart
};

// Draw the Chart.js line graph
async function renderChart() {
    const res = await fetch('http://localhost:5000/api/mood');
    const data = await res.json();
    const ctx = document.getElementById('moodChart');
    
    if (moodChartInstance) moodChartInstance.destroy(); // Destroy old chart before drawing new one
    
    // Format the dates to just show MM-DD for cleaner viewing
    const labels = data.dates.map(d => d.split(' ')[0].substring(5)); 

    moodChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Mood Score',
                data: data.scores,
                borderColor: '#2B6CB0',
                backgroundColor: 'rgba(43, 108, 176, 0.1)',
                fill: true,
                tension: 0.3 // Adds a slight curve to the line
            }]
        },
        options: {
            scales: { y: { min: 1, max: 10 } },
            plugins: { legend: { display: false } } // Hides the legend for a cleaner look
        }
    });
}

// Call these functions immediately when the page loads
fetchHistory();
renderChart();

// --- CRISIS SOS LOGIC ---
const sosBtn = document.getElementById('sos-btn');

sosBtn.addEventListener('click', () => {
    // Drop the emergency info directly into the chat as an AI message
    const crisisMsg = `🚨 **CRISIS RESOURCES** 🚨\n\nIf you are in immediate danger, please reach out to humans who can help right now:\n\n• **988** (Lifeline)\n• **112** (Emergency)\n• **1860-266-2345** (India)\n\nI am an AI and cannot provide emergency support. Please make the call.`;
    
    addMessage(crisisMsg, 'ai');
});

// --- SUMMARIZE SESSION LOGIC ---
const summarizeBtn = document.getElementById('summarize-btn');
const summaryDisplay = document.getElementById('summary-display');

summarizeBtn.addEventListener('click', async () => {
    // Prevent summarizing if they haven't started a chat
    if (!currentSessionId) {
        alert("There is no active session to summarize yet!");
        return;
    }
    
    // Change button text to show it's "Thinking..."
    summarizeBtn.innerText = "Generating Note...";
    
    try {
        const res = await fetch('http://localhost:5000/api/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId })
        });
        
        const data = await res.json();
        
        if (data.summary) {
            // Show the hidden box and format the text
            summaryDisplay.style.display = 'block';
            // Replace newlines with <br> tags so HTML renders the bullet points correctly
            summaryDisplay.innerHTML = data.summary.replace(/\n/g, '<br>'); 
            
            summarizeBtn.innerText = "Note Saved!";
            setTimeout(() => summarizeBtn.innerText = "End & Summarize", 3000);
        } else {
            alert("Error: " + data.error);
            summarizeBtn.innerText = "End & Summarize";
        }
    } catch (error) {
        console.error("Summary error:", error);
        alert("Sorry, I couldn't reach the backend to summarize this.");
        summarizeBtn.innerText = "End & Summarize";
    }
});