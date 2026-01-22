cat > static/app.js << 'EOF'
document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('message');
    const categorySelect = document.getElementById('category');
    const responseDiv = document.getElementById('response');
    const placeholderDiv = document.getElementById('placeholder');
    const responseText = document.getElementById('responseText');
    const similarCasesDiv = document.getElementById('similarCases');
    const casesList = document.getElementById('casesList');
    const historyDiv = document.getElementById('history');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const spinner = document.getElementById('spinner');
    
    let conversationHistory = JSON.parse(localStorage.getItem('mechanicHistory')) || [];
    renderHistory();
    
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const message = messageInput.value.trim();
        const category = categorySelect.value;
        if (!message) return;
        
        btnText.classList.add('d-none');
        spinner.classList.remove('d-none');
        submitBtn.disabled = true;
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message, category: category })
            });
            const data = await response.json();
            
            if (response.ok) {
                placeholderDiv.classList.add('d-none');
                responseDiv.classList.remove('d-none');
                responseDiv.classList.add('show');
                responseText.innerHTML = formatAIResponse(data.text);
                
                if (data.similar_cases && data.similar_cases.length > 0) {
                    casesList.innerHTML = '';
                    data.similar_cases.forEach((caseItem, index) => {
                        const matchScore = caseItem.similarity ? Math.round(caseItem.similarity * 100) : 'N/A';
                        const caseDiv = document.createElement('div');
                        caseDiv.className = 'card mb-2 case-card';
                        caseDiv.innerHTML = `<div class="card-body p-3"><div class="d-flex justify-content-between mb-2"><h6 class="card-subtitle text-accent">Match Found</h6><span class="badge bg-dark border border-secondary">${matchScore}% Match</span></div><p class="card-text small text-light mb-1"><strong>Issue:</strong> ${caseItem.prompt}</p><p class="card-text small text-muted text-truncate">${caseItem.response}</p></div>`;
                        casesList.appendChild(caseDiv);
                    });
                    similarCasesDiv.classList.remove('d-none');
                } else {
                    similarCasesDiv.classList.add('d-none');
                }
                
                const historyItem = { message: message, response: data.text, category: category, timestamp: new Date().toLocaleString() };
                conversationHistory.unshift(historyItem);
                if (conversationHistory.length > 10) conversationHistory = conversationHistory.slice(0, 10);
                localStorage.setItem('mechanicHistory', JSON.stringify(conversationHistory));
                renderHistory();
                messageInput.value = '';
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        } finally {
            btnText.classList.remove('d-none');
            spinner.classList.add('d-none');
            submitBtn.disabled = false;
        }
    });
    
    function formatAIResponse(text) {
        let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>');
        formatted = formatted.replace(/- /g, '• ');
        return formatted;
    }
    
    function renderHistory() {
        historyDiv.innerHTML = '';
        if (conversationHistory.length === 0) {
            historyDiv.innerHTML = '<p class="text-muted text-center py-3">No diagnostic history found.</p>';
            return;
        }
        conversationHistory.forEach((item, index) => {
            const historyItem = document.createElement('div');
            historyItem.className = 'list-group-item';
            historyItem.innerHTML = `<div class="d-flex w-100 justify-content-between align-items-center mb-2"><span class="badge bg-secondary">${item.category.toUpperCase()}</span><small class="text-muted">${item.timestamp}</small></div><p class="mb-2 text-white">${item.message}</p><button class="btn btn-sm btn-outline-warning w-100" onclick="viewFullResponse(${index})"><i class="fa-solid fa-eye me-1"></i> View Advice</button>`;
            historyDiv.appendChild(historyItem);
        });
    }
    
    window.viewFullResponse = function(index) {
        const item = conversationHistory[index];
        placeholderDiv.classList.add('d-none');
        responseDiv.classList.remove('d-none');
        responseText.innerHTML = formatAIResponse(item.response);
        similarCasesDiv.classList.add('d-none');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };
});
EOF