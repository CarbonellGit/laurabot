document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-upload');
    const filePreview = document.getElementById('file-preview');
    const fileNameDisplay = document.getElementById('file-name-display');
    const fileSizeDisplay = document.getElementById('file-size-display');
    
    // Elementos de Segmento/Série
    const radiosSegmento = document.querySelectorAll('input[name="segmento"]');
    const containerSeries = document.getElementById('container-series');
    const listaSeries = document.getElementById('lista-series');

    // Dados de Séries (Mesma lógica do Cadastro)
    const seriesPorSegmento = {
        'EI': ['Berçário', 'Grupo 1', 'Grupo 2', 'Grupo 3', 'Grupo 4', 'Grupo 5'],
        'AI': ['1º Ano', '2º Ano', '3º Ano', '4º Ano', '5º Ano'],
        'AF': ['6º Ano', '7º Ano', '8º Ano', '9º Ano'],
        'EM': ['1ª Série', '2ª Série', '3ª Série']
    };

    // --- 1. Lógica de Drag & Drop ---
    
    // Clique na zona abre o seletor de arquivo
    dropZone.addEventListener('click', () => fileInput.click());

    // Efeitos visuais ao arrastar
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('dragover');
        }, false);
    });

    // Soltar o arquivo
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    // Selecionar pelo input padrão
    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            
            // Validação simples de PDF
            if (file.type !== 'application/pdf') {
                alert('Por favor, selecione apenas arquivos PDF.');
                return;
            }

            // Atualiza input (caso tenha vindo do drop)
            if (fileInput.files.length === 0 || fileInput.files[0] !== file) {
               // Nota: input file é read-only por segurança em alguns browsers, 
               // mas para envio via form normal, o ideal é usar o input change.
               // Se veio do drop, vamos atribuir ao input.files (modern browsers only)
               try {
                   fileInput.files = files;
               } catch(err) {
                   console.log("Browser não suporta atribuição direta de files.");
               }
            }

            // Mostra prévia
            fileNameDisplay.textContent = file.name;
            fileSizeDisplay.textContent = formatBytes(file.size);
            filePreview.style.display = 'flex';
            dropZone.style.display = 'none'; // Esconde a zona de drop para ficar limpo
        }
    }

    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    // Botão de remover arquivo (X)
    document.getElementById('btn-remove-file').addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation(); // Evita reabrir o dropzone
        fileInput.value = ''; // Limpa input
        filePreview.style.display = 'none';
        dropZone.style.display = 'block';
    });


    // --- 2. Lógica Dinâmica de Séries ---
    
    radiosSegmento.forEach(radio => {
        radio.addEventListener('change', (e) => {
            const segmento = e.target.value;
            atualizarSeries(segmento);
        });
    });

    function atualizarSeries(segmento) {
        listaSeries.innerHTML = ''; // Limpa
        
        if (segmento === 'TODOS') {
            containerSeries.style.display = 'none';
            return;
        }

        const series = seriesPorSegmento[segmento] || [];
        
        if (series.length > 0) {
            containerSeries.style.display = 'block';
            
            // Adiciona opção "Todas as séries deste segmento"
            criarCheckboxSerie('TODAS', 'Todas as séries');

            series.forEach(serie => {
                criarCheckboxSerie(serie, serie);
            });
        } else {
            containerSeries.style.display = 'none';
        }
    }

    function criarCheckboxSerie(valor, texto) {
        const wrapper = document.createElement('div');
        wrapper.className = 'checkbox-card';
        
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.name = 'series'; // Flask receberá lista de 'series'
        input.value = valor;
        input.id = `serie-${valor.replace(/\s/g, '')}`;

        const label = document.createElement('label');
        label.className = 'checkbox-label';
        label.setAttribute('for', input.id);
        label.textContent = texto;
        // Ajuste de estilo para séries (menor que segmento)
        label.style.padding = '0.5rem';
        label.style.fontSize = '0.9rem';

        wrapper.appendChild(input);
        wrapper.appendChild(label);
        listaSeries.appendChild(wrapper);
    }
});