/*
 * Script Global (main.js)
 * Gerencia comportamentos comuns a todas as páginas, como o Loader.
 */

document.addEventListener('DOMContentLoaded', () => {
    const loader = document.getElementById('global-loader');

    // Função para mostrar o loader
    window.showLoader = () => {
        if (loader) {
            loader.style.display = 'flex';
        }
    };

    // Função para esconder o loader
    window.hideLoader = () => {
        if (loader) {
            loader.style.display = 'none';
        }
    };

    // 1. Intercepta cliques em links
    document.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', (e) => {
            const href = link.getAttribute('href');
            const target = link.getAttribute('target');

            // Só mostra loader se:
            // - Tiver href
            // - Não for âncora (#)
            // - Não for javascript:
            // - Não abrir em nova aba (_blank)
            if (href && 
                href !== '#' && 
                !href.startsWith('#') && 
                !href.startsWith('javascript:') && 
                target !== '_blank') {
                
                window.showLoader();
            }
        });
    });

    // 2. Intercepta submissões de formulário
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', () => {
            // Se o form for válido (HTML5 validation), mostra o loader
            if (form.checkValidity()) {
                window.showLoader();
            }
        });
    });

    // 3. Segurança: Esconde o loader se o usuário voltar pelo botão "Voltar" do navegador
    // (O navegador pode carregar a página do cache com o loader ainda visível)
    window.addEventListener('pageshow', (event) => {
        if (event.persisted) {
            window.hideLoader();
        }
    });
});