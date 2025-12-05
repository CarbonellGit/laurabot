/*
 * Lógica da Interface Admin (Upload e Gestão)
 */

document.addEventListener('DOMContentLoaded', () => {
    // === Elementos de Drag & Drop ===
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-upload');
    const filePreview = document.getElementById('file-preview');
    const fileNameDisplay = document.getElementById('file-name-display');
    const fileSizeDisplay = document.getElementById('file-size-display');
    const btnRemoveFile = document.getElementById('btn-remove-file');
    
    // === Elementos de Filtro ===
    const radiosSegmento = document.querySelectorAll('input[name="segmento"]');
    const containerSeries = document.getElementById('container-series');
    const listaSeries = document.getElementById('lista-series');
    const containerPeriodo = document.getElementById('container-periodo');
    const containerTurma = document.getElementById('container-turma');
    const containerIntegral = document.getElementById('container-integral'); // NOVO

    // ------------------------------------------------------------------
    // 1. Lógica de Drag & Drop
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
    
    radiosSegmento.forEach(radio => {
        radio.addEventListener('change', (e) => {
            const segmento = e.target.value;
            atualizarInterface(segmento);
        });
    });

    /**
     * Atualiza a visibilidade dos campos com base no Segmento.
     */
    function atualizarInterface(segmento, manterSelecoes = false) {
        // Se for "TODOS", esconde tudo
        if (segmento === 'TODOS') {
            containerSeries.style.display = 'none';
            containerPeriodo.style.display = 'none';
            containerTurma.style.display = 'none';
            if(containerIntegral) containerIntegral.style.display = 'none';
            return;
        }

        // 1. Popula Séries
        const series = DADOS_ESCOLA.series[segmento] || [];
        if (series.length > 0) {
            containerSeries.style.display = 'block';
            if (!manterSelecoes || listaSeries.children.length === 0) {
                 listaSeries.innerHTML = ''; 
                 criarCheckbox(listaSeries, 'series', 'TODAS', 'Todas as séries');
                 series.forEach(s => criarCheckbox(listaSeries, 'series', s, s));
            }
        }

        // 2. Lógica de Período e INTEGRAL (Modificada)
        // Regra: EI e AI mostram Período e Integral. AF e EM não.
        if (['EI', 'AI'].includes(segmento)) {
            containerPeriodo.style.display = 'block';
            if(containerIntegral) containerIntegral.style.display = 'block'; // Mostra Integral
        } else {
            containerPeriodo.style.display = 'none';
            if(containerIntegral) {
                containerIntegral.style.display = 'none'; // Esconde Integral
                // Opcional: Desmarcar o switch se mudar de segmento
                const chk = document.getElementById('check-integral');
                if(chk && !manterSelecoes) chk.checked = false;
            }
        }

        // 3. Mostra Turmas
        containerTurma.style.display = 'block';
    }

    function criarCheckbox(container, name, value, text) {
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
    const segmentoSelecionado = document.querySelector('input[name="segmento"]:checked');
    if (segmentoSelecionado) {
        // Passamos true para não limpar os valores que vieram do servidor
        atualizarInterface(segmentoSelecionado.value, true);
    }
});