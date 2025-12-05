/*
 * Lógica do Cadastro e Edição de Estudantes (cadastro.js)
 */

document.addEventListener('DOMContentLoaded', () => {
    const listaEstudantes = document.getElementById('lista-estudantes');
    const btnAdicionar = document.getElementById('btn-adicionar');
    const template = document.getElementById('template-estudante');

    let estudanteCounter = 0;

    /**
     * Adiciona um novo card de estudante ao formulário.
     */
    function adicionarEstudante(dados = null) {
        const index = estudanteCounter++;
        
        const clone = template.content.cloneNode(true);
        const card = clone.querySelector('.estudante-card');
        
        card.setAttribute('data-index', index);
        card.querySelector('.numero-estudante').textContent = document.querySelectorAll('.estudante-card').length + 1;
        
        // Ajusta names
        card.querySelectorAll('[name]').forEach(input => {
            const name = input.getAttribute('name').replace('{index}', index);
            input.setAttribute('name', name);
        });

        // Botão remover
        card.querySelector('.btn-remove').addEventListener('click', () => {
            if (document.querySelectorAll('.estudante-card').length > 1) {
                card.remove();
                atualizarNumeracao();
            } else {
                alert("É necessário manter pelo menos um estudante no cadastro.");
            }
        });

        // Elementos
        const selSegmento = card.querySelector('.select-segmento');
        const selSerie = card.querySelector('.select-serie');
        const selPeriodo = card.querySelector('.select-periodo');
        const selTurma = card.querySelector('.select-turma');
        const divIntegral = card.querySelector('.integral-section'); // Novo
        const chkIntegral = card.querySelector('.check-integral');   // Novo
        const inpNome = card.querySelector('.input-nome');

        // --- LÓGICA DE CASCATA ---

        // 1. Mudança no Segmento
        selSegmento.addEventListener('change', (e) => {
            const seg = e.target.value;
            
            // Lógica do Integral (NOVO)
            // Só exibe se for EI ou AI
            if (['EI', 'AI'].includes(seg)) {
                divIntegral.style.display = 'flex';
            } else {
                divIntegral.style.display = 'none';
                chkIntegral.checked = false; // Reseta se mudar para AF/EM
            }

            // Reseta dependentes
            resetSelect(selSerie, 'Selecione a série...');
            resetSelect(selPeriodo, 'Selecione a série primeiro...');
            resetSelect(selTurma, 'Selecione o período primeiro...');
            selPeriodo.disabled = true;
            selTurma.disabled = true;

            const series = DADOS_ESCOLA.series[seg] || [];
            series.forEach(s => selSerie.add(new Option(s, s)));
            selSerie.disabled = false;
        });

        // 2. Mudança na Série
        selSerie.addEventListener('change', (e) => {
            const serie = e.target.value;
            
            resetSelect(selPeriodo, 'Selecione o período...');
            resetSelect(selTurma, 'Selecione o período primeiro...');
            selTurma.disabled = true;

            const dadosSerie = DADOS_ESCOLA.turmas[serie] || {};
            const periodos = Object.keys(dadosSerie);

            periodos.forEach(p => selPeriodo.add(new Option(p, p)));
            selPeriodo.disabled = false;
        });

        // 3. Mudança no Período
        selPeriodo.addEventListener('change', (e) => {
            const periodo = e.target.value;
            const serie = selSerie.value;
            
            resetSelect(selTurma, 'Selecione a turma...');
            
            const turmas = DADOS_ESCOLA.turmas[serie]?.[periodo] || [];
            turmas.forEach(t => selTurma.add(new Option(t, t)));
            selTurma.disabled = false;
        });

        // --- MODO EDIÇÃO ---
        if (dados) {
            if (inpNome) inpNome.value = dados.nome || '';
            
            // Preenche Integral (NOVO)
            if (dados.integral === true || dados.integral === 'on') {
                chkIntegral.checked = true;
            }

            if (dados.segmento) {
                selSegmento.value = dados.segmento;
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

    function resetSelect(selectElement, defaultText) {
        selectElement.innerHTML = '';
        const opt = document.createElement('option');
        opt.value = "";
        opt.disabled = true;
        opt.selected = true;
        opt.textContent = defaultText;
        selectElement.add(opt);
    }

    function atualizarNumeracao() {
        document.querySelectorAll('.estudante-card').forEach((card, i) => {
            card.querySelector('.numero-estudante').textContent = i + 1;
        });
    }

    if (btnAdicionar) btnAdicionar.addEventListener('click', () => adicionarEstudante());

    if (typeof DADOS_ESTUDANTES !== 'undefined' && DADOS_ESTUDANTES.length > 0) {
        DADOS_ESTUDANTES.forEach(adicionarEstudante);
    } else {
        adicionarEstudante();
    }
});