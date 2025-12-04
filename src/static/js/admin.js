/*
 * Lógica da Interface Admin (Upload e Gestão)
 * Gerencia Drag & Drop e Filtros Dinâmicos de Segmento.
 * Depende de: DADOS_ESCOLA (definido em dados_escola.js).
 */

document.addEventListener('DOMContentLoaded', () => {
    // === Elementos de Drag & Drop ===
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-upload');
    const filePreview = document.getElementById('file-preview');
    const fileNameDisplay = document.getElementById('file-name-display');
    const fileSizeDisplay = document.getElementById('file-size-display');
    const btnRemoveFile = document.getElementById('btn-remove-file');
    
    // === Elementos de Filtro (Segmentação) ===
    const radiosSegmento = document.querySelectorAll('input[name="segmento"]');
    const containerSeries = document.getElementById('container-series');
    const listaSeries = document.getElementById('lista-series');
    const containerPeriodo = document.getElementById('container-periodo');
    const containerTurma = document.getElementById('container-turma');

    // ------------------------------------------------------------------
    // 1. Lógica de Drag & Drop (Arquivo)
    // ------------------------------------------------------------------
    
    dropZone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault(); e.stopPropagation();
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault(); e.stopPropagation();
            dropZone.classList.remove('dragover');
        }, false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        handleFiles(dt.files);
    });

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    btnRemoveFile.addEventListener('click', (e) => {
        e.preventDefault(); e.stopPropagation();
        fileInput.value = ''; 
        filePreview.style.display = 'none';
        dropZone.style.display = 'block';
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type !== 'application/pdf') {
                alert('Por favor, selecione apenas arquivos PDF.');
                return;
            }
            
            // Hack para input file (read-only em alguns browsers)
            try { fileInput.files = files; } catch(err) {}

            fileNameDisplay.textContent = file.name;
            fileSizeDisplay.textContent = formatBytes(file.size);
            filePreview.style.display = 'flex';
            dropZone.style.display = 'none';
        }
    }

    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals < 0 ? 0 : decimals)) + ' ' + ['Bytes', 'KB', 'MB', 'GB'][i];
    }


    // ------------------------------------------------------------------
    // 2. Lógica Dinâmica de Segmentação (Filtros)
    // ------------------------------------------------------------------
    
    radiosSegmento.forEach(radio => {
        radio.addEventListener('change', (e) => {
            const segmento = e.target.value;
            atualizarInterface(segmento);
        });
    });

    function atualizarInterface(segmento) {
        listaSeries.innerHTML = ''; // Limpa séries anteriores
        
        // Se for "TODOS", esconde todos os sub-filtros
        if (segmento === 'TODOS') {
            containerSeries.style.display = 'none';
            containerPeriodo.style.display = 'none';
            containerTurma.style.display = 'none';
            return;
        }

        // 1. Popula e Mostra Séries (DADOS_ESCOLA)
        const series = DADOS_ESCOLA.series[segmento] || [];
        if (series.length > 0) {
            containerSeries.style.display = 'block';
            criarCheckbox(listaSeries, 'series', 'TODAS', 'Todas as séries');
            series.forEach(s => criarCheckbox(listaSeries, 'series', s, s));
        }

        // 2. Lógica de Período
        // Regra: AF e EM são Integralmente Manhã -> Não precisa filtrar (assume Manhã).
        // EI e AI possuem turmas de Manhã e Tarde -> Precisa filtrar.
        if (['EI', 'AI'].includes(segmento)) {
            containerPeriodo.style.display = 'block';
        } else {
            containerPeriodo.style.display = 'none';
            // Opcional: Limpar checkboxes de período aqui se necessário
        }

        // 3. Mostra Turmas (Sempre disponível se selecionou um segmento específico)
        // Permite enviar um comunicado para "Todos os 6º Anos da Turma A", por exemplo.
        containerTurma.style.display = 'block';
    }

    /**
     * Cria um elemento checkbox estilizado e o adiciona ao container.
     */
    function criarCheckbox(container, name, value, text) {
        const div = document.createElement('div');
        div.className = 'checkbox-card';
        
        // ID único para acessibilidade
        const uniqueId = `${name}-${value.replace(/[^a-zA-Z0-9]/g, '')}`;
        
        div.innerHTML = `
            <input type="checkbox" name="${name}" id="${uniqueId}" value="${value}">
            <label class="checkbox-label" for="${uniqueId}">
                ${text}
            </label>
        `;
        container.appendChild(div);
    }
});