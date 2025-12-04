document.addEventListener('DOMContentLoaded', () => {
    const chatHistory = document.getElementById('chat-history');
    const userInput = document.getElementById('user-input');
    const btnSend = document.getElementById('btn-send');
    const typingIndicator = document.getElementById('typing-indicator');

    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    // Função atualizada para renderizar Markdown
    function appendMessage(text, sender) {
        const div = document.createElement('div');
        div.classList.add('message');
        div.classList.add(sender === 'user' ? 'message-user' : 'message-bot');
        
        if (sender === 'bot') {
            // Se for o Robô, converte Markdown -> HTML
            // 'marked.parse' vem da biblioteca que adicionamos no base.html
            div.innerHTML = marked.parse(text);
        } else {
            // Se for usuário, mantém texto puro por segurança (evita XSS)
            div.innerText = text; 
        }
        
        chatHistory.appendChild(div);
        scrollToBottom();
    }

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        appendMessage(text, 'user');
        userInput.value = '';
        userInput.disabled = true; 
        typingIndicator.style.display = 'block';
        scrollToBottom();

        try {
            const response = await fetch('/enviar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();

            typingIndicator.style.display = 'none';
            appendMessage(data.response, 'bot');

        } catch (error) {
            console.error('Erro:', error);
            typingIndicator.style.display = 'none';
            appendMessage("Desculpe, tive um erro de conexão. Tente novamente.", 'bot');
        } finally {
            userInput.disabled = false;
            userInput.focus();
            scrollToBottom();
        }
    }

    btnSend.addEventListener('click', sendMessage);

    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    userInput.focus();
});