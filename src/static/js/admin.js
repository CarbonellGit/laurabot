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

        fileInput.addEventListener('change', function () {
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
                try { fileInput.files = files; } catch (err) { }
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
            if (containerIntegral) containerIntegral.style.display = 'none';
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
            if (containerIntegral) containerIntegral.style.display = 'block'; // Mostra Integral
        } else {
            containerPeriodo.style.display = 'none';
            if (containerIntegral) {
                containerIntegral.style.display = 'none'; // Esconde Integral
                // Opcional: Desmarcar o switch se mudar de segmento
                const chk = document.getElementById('check-integral');
                if (chk && !manterSelecoes) chk.checked = false;
            }
        }

        // 3. Mostra Turmas
        containerTurma.style.display = 'block';
    }

    function criarCheckbox(container, name, value, text) {
        const idExistente = `${name}-${value.replace(/[^a-zA-Z0-9]/g, '')}`;
        if (document.getElementById(idExistente)) return;

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

/*
 * Lógica de Filtros da Biblioteca (Fase 6)
 */
document.addEventListener('DOMContentLoaded', () => {
    const filterNome = document.getElementById('filter-nome');
    const filterSegmento = document.getElementById('filter-segmento');
    const filterData = document.getElementById('filter-data');
    const btnReset = document.getElementById('btn-reset-filters');
    const fileGrid = document.getElementById('file-grid');
    const noResults = document.getElementById('no-results');
    const countVisible = document.getElementById('count-visible');

    if (!filterNome || !fileGrid) return; // Só executa na página de gerenciar

    const cards = Array.from(document.querySelectorAll('.file-card'));

    // Atualiza o contador inicial
    if (countVisible) countVisible.textContent = cards.length;

    function aplicarFiltros() {
        const termoNome = filterNome.value.toLowerCase();
        const segSelecionado = filterSegmento.value;
        const dataSelecionada = filterData.value; // Formato YYYY-MM-DD

        let visiveis = 0;

        cards.forEach(card => {
            const nomeArquivo = card.getAttribute('data-nome') || '';
            const segmentoArquivo = card.getAttribute('data-segmento');
            const isIntegral = card.getAttribute('data-integral') === 'true';
            const dataArquivo = card.getAttribute('data-date');

            // 1. Filtro de Nome (Contém)
            const matchNome = nomeArquivo.includes(termoNome);

            // 2. Filtro de Segmento (Lógica Especial para INT)
            let matchSegmento = true;
            if (segSelecionado !== 'TODOS') {
                if (segSelecionado === 'INT') {
                    // Se filtro for INT, verifica se a flag integral é true
                    matchSegmento = isIntegral;
                } else {
                    // Senão, verifica match exato do segmento (EI, AI, etc)
                    matchSegmento = (segmentoArquivo === segSelecionado);
                }
            }

            // 3. Filtro de Data (Match exato da data de upload)
            let matchData = true;
            if (dataSelecionada) {
                matchData = (dataArquivo === dataSelecionada);
            }

            // Decide visibilidade
            if (matchNome && matchSegmento && matchData) {
                card.style.display = 'flex'; // ou 'block' dependendo do CSS do card
                visiveis++;
            } else {
                card.style.display = 'none';
            }
        });

        // Feedback Visual
        if (countVisible) countVisible.textContent = visiveis;

        if (visiveis === 0) {
            fileGrid.style.display = 'none';
            if (noResults) noResults.style.display = 'block';
        } else {
            fileGrid.style.display = 'grid';
            if (noResults) noResults.style.display = 'none';
        }
    }

    // Event Listeners para feedback em tempo real
    filterNome.addEventListener('input', aplicarFiltros);
    filterSegmento.addEventListener('change', aplicarFiltros);
    filterData.addEventListener('change', aplicarFiltros);

    // Botão de Limpar
    if (btnReset) {
        btnReset.addEventListener('click', () => {
            filterNome.value = '';
            filterSegmento.value = 'TODOS';
            filterData.value = '';
            aplicarFiltros();
        });
    }
});

/*
 * 3. Polling de Status & Modal
 */
document.addEventListener('DOMContentLoaded', () => {
    // === Polling ===
    setInterval(() => {
        const itensProcessando = document.querySelectorAll('.status-polling');
        if (itensProcessando.length === 0) return;

        itensProcessando.forEach(icon => {
            const docId = icon.getAttribute('data-id');
            fetch(`/admin/status/${docId}`)
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'concluido') {
                        icon.textContent = 'check_circle';
                        icon.style.color = 'var(--carbonell-verde)';
                        icon.classList.remove('status-polling');
                        icon.title = "Concluído";
                    } else if (data.status === 'erro') {
                        icon.textContent = 'error';
                        icon.style.color = 'var(--carbonell-vermelho)';
                        icon.classList.remove('status-polling');
                        icon.title = "Erro: " + data.msg;
                    }
                })
                .catch(console.error);
        });
    }, 5000); // 5 segundos
});

// === Função Global para Modal ===
window.abrirModal = function (url) {
    const modal = document.getElementById('pdfModal');
    const iframe = document.getElementById('pdfFrame');
    if (modal && iframe) {
        iframe.src = url;
        modal.style.display = 'flex';
    }
}