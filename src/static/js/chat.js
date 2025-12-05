document.addEventListener('DOMContentLoaded', () => {
    const chatHistory = document.getElementById('chat-history');
    const userInput = document.getElementById('user-input');
    const btnSend = document.getElementById('btn-send');
    const typingIndicator = document.getElementById('typing-indicator');

    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function createMessageElement(sender) {
        const div = document.createElement('div');
        div.classList.add('message');
        div.classList.add(sender === 'user' ? 'message-user' : 'message-bot');
        chatHistory.appendChild(div);
        return div;
    }

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        // 1. Mostra msg do usuário
        const userMsgDiv = createMessageElement('user');
        userMsgDiv.innerText = text;
        
        userInput.value = '';
        userInput.disabled = true;
        scrollToBottom();

        try {
            // 2. Prepara o container da resposta do Bot (Vazio por enquanto)
            const botMsgDiv = createMessageElement('bot');
            let botTextAcumulado = "";
            
            // 3. Inicia o Request
            const response = await fetch('/enviar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            if (!response.ok) throw new Error('Erro na requisição');

            // 4. Lê o Stream
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                // Decodifica o pedaço (chunk) recebido
                const chunk = decoder.decode(value, { stream: true });
                botTextAcumulado += chunk;

                // Renderiza Markdown em tempo real
                // (Isso permite que negritos e listas apareçam conforme o texto chega)
                botMsgDiv.innerHTML = marked.parse(botTextAcumulado);
                
                scrollToBottom();
            }

        } catch (error) {
            console.error('Erro:', error);
            const errorDiv = createMessageElement('bot');
            errorDiv.innerText = "Desculpe, tive um erro de conexão.";
        } finally {
            userInput.disabled = false;
            userInput.focus();
            scrollToBottom();
        }
    }

    btnSend.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // Renderiza markdown das mensagens antigas (se houver) ao carregar
    document.querySelectorAll('.message-bot').forEach(el => {
        // Verifica se já não foi renderizado (para evitar duplo parse)
        if (!el.querySelector('p') && !el.querySelector('ul')) {
             el.innerHTML = marked.parse(el.innerText);
        }
    });
    
    scrollToBottom();
});