document.addEventListener('DOMContentLoaded', () => {
    const chatHistory = document.getElementById('chat-history');
    const userInput = document.getElementById('user-input');
    const btnSend = document.getElementById('btn-send');
    const typingIndicator = document.getElementById('typing-indicator');

    // Função para rolar o chat para o final
    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    // Função para criar balão de mensagem
    function appendMessage(text, sender) {
        const div = document.createElement('div');
        div.classList.add('message');
        div.classList.add(sender === 'user' ? 'message-user' : 'message-bot');
        
        // Permite quebra de linha
        div.innerText = text; 
        
        chatHistory.appendChild(div);
        scrollToBottom();
    }

    // Lógica de Envio
    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        // 1. Exibe a mensagem do usuário imediatamente
        appendMessage(text, 'user');
        userInput.value = '';
        userInput.disabled = true; // Bloqueia input enquanto processa
        typingIndicator.style.display = 'block';

        try {
            // 2. Envia para o Backend (Python)
            const response = await fetch('/enviar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();

            // 3. Exibe a resposta do Bot
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

    // Event Listeners
    btnSend.addEventListener('click', sendMessage);

    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // Foco inicial
    userInput.focus();
});