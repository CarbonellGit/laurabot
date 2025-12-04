/*
 * Lógica do Cadastro e Edição de Estudantes (cadastro.js)
 * * Gerencia a adição dinâmica de cards de estudantes e a lógica de
 * dependência entre os campos (Segmento -> Série -> Período -> Turma).
 * Depende de: DADOS_ESCOLA (definido em dados_escola.js).
 */

document.addEventListener('DOMContentLoaded', () => {
    const listaEstudantes = document.getElementById('lista-estudantes');
    const btnAdicionar = document.getElementById('btn-adicionar');
    const template = document.getElementById('template-estudante');

    let estudanteCounter = 0;

    /**
     * Adiciona um novo card de estudante ao formulário.
     * @param {Object|null} dados - Dados para preenchimento automático (Edição).
     */
    function adicionarEstudante(dados = null) {
        const index = estudanteCounter++;
        
        // Clona o template HTML
        const clone = template.content.cloneNode(true);
        const card = clone.querySelector('.estudante-card');
        
        // Configuração inicial do card (índices e visual)
        card.setAttribute('data-index', index);
        card.querySelector('.numero-estudante').textContent = document.querySelectorAll('.estudante-card').length + 1;
        
        // Ajusta os atributos 'name' para o formato do Flask: estudantes[0][nome]
        card.querySelectorAll('[name]').forEach(input => {
            const name = input.getAttribute('name').replace('{index}', index);
            input.setAttribute('name', name);
        });

        // Configura o botão de remoção
        card.querySelector('.btn-remove').addEventListener('click', () => {
            if (document.querySelectorAll('.estudante-card').length > 1) {
                card.remove();
                atualizarNumeracao();
            } else {
                alert("É necessário manter pelo menos um estudante no cadastro.");
            }
        });

        // Referências aos elementos do formulário dentro do card
        const selSegmento = card.querySelector('.select-segmento');
        const selSerie = card.querySelector('.select-serie');
        const selPeriodo = card.querySelector('.select-periodo');
        const selTurma = card.querySelector('.select-turma');
        const inpNome = card.querySelector('.input-nome');

        // --- LÓGICA DE CASCATA (DEPENDÊNCIAS) ---

        // 1. Mudança no Segmento -> Libera Série
        selSegmento.addEventListener('change', (e) => {
            const seg = e.target.value;
            
            // Reseta os campos dependentes
            resetSelect(selSerie, 'Selecione a série...');
            resetSelect(selPeriodo, 'Selecione a série primeiro...');
            resetSelect(selTurma, 'Selecione o período primeiro...');
            selPeriodo.disabled = true;
            selTurma.disabled = true;

            // Popula Séries baseadas no Segmento (DADOS_ESCOLA)
            const series = DADOS_ESCOLA.series[seg] || [];
            series.forEach(s => selSerie.add(new Option(s, s)));
            
            selSerie.disabled = false;
        });

        // 2. Mudança na Série -> Libera Período
        selSerie.addEventListener('change', (e) => {
            const serie = e.target.value;
            
            resetSelect(selPeriodo, 'Selecione o período...');
            resetSelect(selTurma, 'Selecione o período primeiro...');
            selTurma.disabled = true;

            // Busca os períodos disponíveis para esta série na matriz
            // Ex: '1º Ano': { 'Manhã': [...], 'Tarde': [...] }
            const dadosSerie = DADOS_ESCOLA.turmas[serie] || {};
            const periodos = Object.keys(dadosSerie);

            periodos.forEach(p => selPeriodo.add(new Option(p, p)));
            
            selPeriodo.disabled = false;
        });

        // 3. Mudança no Período -> Libera Turma
        selPeriodo.addEventListener('change', (e) => {
            const periodo = e.target.value;
            const serie = selSerie.value;
            
            resetSelect(selTurma, 'Selecione a turma...');
            
            // Busca as turmas específicas (ex: ['A', 'B'])
            const turmas = DADOS_ESCOLA.turmas[serie]?.[periodo] || [];
            turmas.forEach(t => selTurma.add(new Option(t, t)));
            
            selTurma.disabled = false;
        });

        // --- PREENCHIMENTO AUTOMÁTICO (MODO EDIÇÃO) ---
        if (dados) {
            if (inpNome) inpNome.value = dados.nome || '';
            
            if (dados.segmento) {
                selSegmento.value = dados.segmento;
                // Dispara eventos manuais para popular e selecionar os próximos
                selSegmento.dispatchEvent(new Event('change'));
                
                if (dados.serie) {
                    selSerie.value = dados.serie;
                    selSerie.dispatchEvent(new Event('change'));
                    
                    if (dados.periodo) {
                        selPeriodo.value = dados.periodo;
                        selPeriodo.dispatchEvent(new Event('change'));
                        
                        if (dados.turma) {
                            selTurma.value = dados.turma;
                        }
                    }
                }
            }
        }

        listaEstudantes.appendChild(card);
    }

    /**
     * Helper para limpar um select e adicionar a opção default.
     */
    function resetSelect(selectElement, defaultText) {
        selectElement.innerHTML = '';
        const opt = document.createElement('option');
        opt.value = "";
        opt.disabled = true;
        opt.selected = true;
        opt.textContent = defaultText;
        selectElement.add(opt);
    }

    /**
     * Atualiza a numeração visual dos cards (#1, #2, #3...) após remoção.
     */
    function atualizarNumeracao() {
        document.querySelectorAll('.estudante-card').forEach((card, i) => {
            card.querySelector('.numero-estudante').textContent = i + 1;
        });
    }

    // Event Listeners Globais
    if (btnAdicionar) btnAdicionar.addEventListener('click', () => adicionarEstudante());

    // Inicialização: Verifica se há dados vindos do Backend (Edição) ou inicia vazio
    if (typeof DADOS_ESTUDANTES !== 'undefined' && DADOS_ESTUDANTES.length > 0) {
        DADOS_ESTUDANTES.forEach(adicionarEstudante);
    } else {
        adicionarEstudante();
    }
});