// Configuration
const API_BASE_URL = '';  // Same origin, no need for full URL

// Global state
let uploadedDocuments = [];
let currentTheme = 'light';

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    setupEventListeners();
    loadDocuments();
});

// Theme Management
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
}

function toggleTheme() {
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
}

function setTheme(theme) {
    currentTheme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    const themeIcon = document.querySelector('.theme-icon');
    themeIcon.textContent = theme === 'light' ? '🌙' : '☀️';
}

// Event Listeners Setup
function setupEventListeners() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    
    // Drag and drop events
    dropZone.addEventListener('dragover', handleDragOver);
    dropZone.addEventListener('dragleave', handleDragLeave);
    dropZone.addEventListener('drop', handleDrop);
    
    // File input change
    fileInput.addEventListener('change', handleFileSelect);
    
    // Auto-resize textarea
    const messageInput = document.getElementById('messageInput');
    messageInput.addEventListener('input', autoResizeTextarea);
}

// Drag and Drop Handlers
function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    
    const files = Array.from(e.dataTransfer.files);
    uploadFiles(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    uploadFiles(files);
}

// File Upload Functions
async function uploadFiles(files) {
    const validFiles = files.filter(file => {
        const validTypes = ['.pdf', '.docx', '.txt'];
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        return validTypes.includes(extension);
    });
    
    if (validFiles.length === 0) {
        showNotification('Please select valid files (PDF, DOCX, TXT)', 'error');
        return;
    }
    
    for (const file of validFiles) {
        await uploadSingleFile(file);
    }
}

async function uploadSingleFile(file) {
    const progressContainer = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    // Show progress
    progressContainer.style.display = 'block';
    progressText.textContent = `Uploading ${file.name}...`;
    progressFill.style.width = '0%';
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        // Add timeout to prevent hanging
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
        
        const response = await fetch(`${API_BASE_URL}/documents/upload`, {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('Upload response:', result);  // Debug log
        
        if (!result.document_id) {
            throw new Error('Invalid response: missing document_id');
        }
        
        // Simulate progress
        progressFill.style.width = '50%';
        progressText.textContent = 'Processing document...';
        
        // Wait for processing to complete
        await waitForProcessing(result.document_id);
        
        // Complete progress
        progressFill.style.width = '100%';
        progressText.textContent = 'Upload complete!';
        
        // Add to documents list
        await loadDocuments();
        
        showNotification(`${file.name} uploaded successfully!`, 'success');
        
        // Hide progress after delay
        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 2000);
        
    } catch (error) {
        console.error('Upload error:', error);
        showNotification(`Failed to upload ${file.name}: ${error.message}`, 'error');
        progressContainer.style.display = 'none';
    }
}

async function waitForProcessing(documentId) {
    const maxAttempts = 30;
    let attempts = 0;
    
    while (attempts < maxAttempts) {
        try {
            const response = await fetch(`${API_BASE_URL}/documents/${documentId}/status`);
            const status = await response.json();
            
            if (status.status === 'done') {
                return;
            } else if (status.status === 'error') {
                throw new Error(status.error_message || 'Processing failed');
            }
            
            // Wait 2 seconds before next check
            await new Promise(resolve => setTimeout(resolve, 2000));
            attempts++;
            
        } catch (error) {
            console.error('Status check error:', error);
            break;
        }
    }
}

// Document Management
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents/`);
        const documents = await response.json();
        
        uploadedDocuments = documents;
        renderDocumentsList();
        
    } catch (error) {
        console.error('Failed to load documents:', error);
    }
}

function renderDocumentsList() {
    const container = document.getElementById('documentsList');
    
    if (uploadedDocuments.length === 0) {
        container.innerHTML = '<div class="no-documents">No documents uploaded yet</div>';
        return;
    }
    
    container.innerHTML = uploadedDocuments.map(doc => `
        <div class="document-item">
            <div class="document-info">
                <div class="document-name">${doc.filename}</div>
                <div class="document-meta">
                    ${formatFileSize(doc.size)} • ${formatDate(doc.created_at)}
                </div>
            </div>
            <button class="delete-btn" onclick="deleteDocument('${doc.id}')">
                Delete
            </button>
        </div>
    `).join('');
}

async function deleteDocument(documentId) {
    if (!confirm('Are you sure you want to delete this document?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            await loadDocuments();
            showNotification('Document deleted successfully', 'success');
        } else {
            throw new Error('Failed to delete document');
        }
        
    } catch (error) {
        console.error('Delete error:', error);
        showNotification('Failed to delete document', 'error');
    }
}

// Chat Functions
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    if (uploadedDocuments.length === 0) {
        showNotification('Please upload some documents first', 'error');
        return;
    }
    
    // Add user message to chat
    addMessageToChat(message, 'user');
    
    // Clear input
    messageInput.value = '';
    autoResizeTextarea({ target: messageInput });
    
    // Show typing indicator
    const typingId = addTypingIndicator();
    
    try {
        // For now, simulate AI response since we need to implement RAG query endpoint
        await simulateAIResponse(message, typingId);
        
    } catch (error) {
        console.error('Chat error:', error);
        removeTypingIndicator(typingId);
        addMessageToChat('Sorry, I encountered an error processing your question.', 'ai');
    }
}

function addMessageToChat(message, sender) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    
    if (sender === 'user') {
        messageDiv.innerHTML = `
            <div class="user-bubble">
                <div class="bubble-content">
                    <p>${escapeHtml(message)}</p>
                </div>
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="ai-bubble">
                <div class="bubble-content">
                    <p>${escapeHtml(message)}</p>
                </div>
            </div>
        `;
    }
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const typingDiv = document.createElement('div');
    const typingId = 'typing-' + Date.now();
    
    typingDiv.id = typingId;
    typingDiv.innerHTML = `
        <div class="ai-bubble">
            <div class="bubble-content">
                <p>🤔 Thinking...</p>
            </div>
        </div>
    `;
    
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return typingId;
}

function removeTypingIndicator(typingId) {
    const typingElement = document.getElementById(typingId);
    if (typingElement) {
        typingElement.remove();
    }
}

async function simulateAIResponse(question, typingId) {
    try {
        // Call real RAG endpoint
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: question })
        });
        
        const result = await response.json();
        
        removeTypingIndicator(typingId);
        
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        
        // Build sources display
        let sourcesHtml = '';
        if (result.sources && result.sources.length > 0) {
            const topSource = result.sources[0];
            sourcesHtml = `
                <div class="source-info">
                    📄 Source: Document ${topSource.document.substring(0, 8)}...
                    <br>📝 Text: "${topSource.text_preview || 'No preview available'}"
                    <span class="confidence-score">${topSource.score}%</span>
                </div>
            `;
        }
        
        messageDiv.innerHTML = `
            <div class="ai-bubble">
                <div class="bubble-content">
                    <p>${escapeHtml(result.answer)}</p>
                    ${sourcesHtml}
                </div>
            </div>
        `;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
    } catch (error) {
        console.error('RAG query error:', error);
        removeTypingIndicator(typingId);
        addMessageToChat('Sorry, I encountered an error processing your question.', 'ai');
    }
}

function clearChat() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <div class="ai-bubble">
                <div class="bubble-content">
                    <p>👋 Welcome! Upload some documents and ask me questions about them.</p>
                </div>
            </div>
        </div>
    `;
}

// Utility Functions
function autoResizeTextarea(event) {
    const textarea = event.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        animation: slideIn 0.3s ease;
        background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#007bff'};
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);