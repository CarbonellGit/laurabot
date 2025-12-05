/*
 * Lógica da Interface Admin (Upload e Gestão)
 * Gerencia Drag & Drop e Filtros Dinâmicos de Segmento.
 * Depende de: DADOS_ESCOLA (definido em dados_escola.js).
 */

document.addEventListener('DOMContentLoaded', () => {
    // === Elementos de Drag & Drop (Pode não existir na tela de edição) ===
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
    // 1. Lógica de Drag & Drop (Só executa se existir na página)
    // ------------------------------------------------------------------
    
    if (dropZone && fileInput) {
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
    }


    // ------------------------------------------------------------------
    // 2. Lógica Dinâmica de Segmentação (Filtros)
    // ------------------------------------------------------------------
    
    // Escuta mudanças no rádio de segmento
    radiosSegmento.forEach(radio => {
        radio.addEventListener('change', (e) => {
            const segmento = e.target.value;
            atualizarInterface(segmento);
        });
    });

    /**
     * Atualiza a visibilidade dos campos com base no Segmento.
     * @param {string} segmento - Ex: 'EI', 'AI', 'TODOS'
     * @param {boolean} manterSelecoes - Se true, não reseta os checkboxes (útil na edição).
     */
    function atualizarInterface(segmento, manterSelecoes = false) {
        // Se for "TODOS", esconde e limpa
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
            
            // Só recria os checkboxes se não estivermos mantendo (Edição) ou se estiver vazio
            if (!manterSelecoes || listaSeries.children.length === 0) {
                 listaSeries.innerHTML = ''; 
                 criarCheckbox(listaSeries, 'series', 'TODAS', 'Todas as séries');
                 series.forEach(s => criarCheckbox(listaSeries, 'series', s, s));
            }
        }

        // 2. Lógica de Período
        if (['EI', 'AI'].includes(segmento)) {
            containerPeriodo.style.display = 'block';
        } else {
            containerPeriodo.style.display = 'none';
        }

        // 3. Mostra Turmas
        containerTurma.style.display = 'block';
    }

    function criarCheckbox(container, name, value, text) {
        // Verifica se já existe para não duplicar na edição
        const idExistente = `${name}-${value.replace(/[^a-zA-Z0-9]/g, '')}`;
        if(document.getElementById(idExistente)) return;

        const div = document.createElement('div');
        div.className = 'checkbox-card';
        
        div.innerHTML = `
            <input type="checkbox" name="${name}" id="${idExistente}" value="${value}">
            <label class="checkbox-label" for="${idExistente}">
                ${text}
            </label>
        `;
        container.appendChild(div);
    }

    // --- AUTO-INICIALIZAÇÃO PARA EDIÇÃO ---
    // Verifica se algum segmento já está marcado ao carregar a página (Edição)
    const segmentoSelecionado = document.querySelector('input[name="segmento"]:checked');
    if (segmentoSelecionado) {
        // Chama a atualização mas PRESERVA os checkboxes que já existem no HTML do server-side
        // Nota: No template 'upload.html', os checkboxes de série são gerados dinamicamente.
        // No template 'editar.html', precisamos garantir que o JS saiba lidar com isso.
        
        // Estratégia Simples: Disparamos a lógica padrão.
        // Se for edição, o HTML virá com os checkboxes já marcados? 
        // Não, o 'lista-series' começa vazio no HTML e é preenchido pelo JS.
        // Precisaremos de um "pulo do gato" no editar.html para remarcar os itens.
        
        atualizarInterface(segmentoSelecionado.value, false);
    }
});