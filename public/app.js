document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('message');
    const categorySelect = document.getElementById('category');
    const responseDiv = document.getElementById('response');
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
        
    
        btnText.textContent = 'Getting Advice...';
        spinner.classList.remove('d-none');
        submitBtn.disabled = true;
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    category: category
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
       
                responseText.textContent = data.text;
                responseDiv.classList.remove('d-none');
                
                
                if (data.similar_cases && data.similar_cases.length > 0) {
                    casesList.innerHTML = '';
                    data.similar_cases.forEach((caseItem, index) => {
                        const caseDiv = document.createElement('div');
                        caseDiv.className = 'card mb-2 case-card';
                        caseDiv.innerHTML = `
                            <div class="card-body">
                                <h6 class="card-subtitle mb-2 text-muted">Case ${index + 1}</h6>
                                <p class="card-text"><strong>Problem:</strong> ${caseItem.prompt}</p>
                                <p class="card-text"><strong>Solution:</strong> ${caseItem.response.substring(0, 150)}...</p>
                            </div>
                        `;
                        casesList.appendChild(caseDiv);
                    });
                    similarCasesDiv.classList.remove('d-none');
                } else {
                    similarCasesDiv.classList.add('d-none');
                }
                
  
                const historyItem = {
                    message: message,
                    response: data.text,
                    category: category,
                    timestamp: new Date().toLocaleString()
                };
                
                conversationHistory.unshift(historyItem);
                if (conversationHistory.length > 10) {
                    conversationHistory = conversationHistory.slice(0, 10);
                }
                
        
                localStorage.setItem('mechanicHistory', JSON.stringify(conversationHistory));
                
           
                renderHistory();
                
              
                messageInput.value = '';
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        } finally {
           
            btnText.textContent = 'Get Advice';
            spinner.classList.add('d-none');
            submitBtn.disabled = false;
        }
    });
    
    function renderHistory() {
        historyDiv.innerHTML = '';
        
        if (conversationHistory.length === 0) {
            historyDiv.innerHTML = '<p class="text-muted">No conversation history yet.</p>';
            return;
        }
        
        conversationHistory.forEach((item, index) => {
            const historyItem = document.createElement('div');
            historyItem.className = 'list-group-item';
            historyItem.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${item.category.toUpperCase()} - ${item.message.substring(0, 50)}...</h6>
                    <small>${item.timestamp}</small>
                </div>
                <p class="mb-1">${item.response.substring(0, 100)}...</p>
                <button class="btn btn-sm btn-outline-primary mt-2" onclick="viewFullResponse(${index})">
                    View Full
                </button>
            `;
            historyDiv.appendChild(historyItem);
        });
    }
    

    window.viewFullResponse = function(index) {
        const item = conversationHistory[index];
        alert(`Full Response:\n\n${item.response}`);
    };
});