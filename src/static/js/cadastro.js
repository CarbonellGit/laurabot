/*
 * Lógica do Cadastro e Edição de Estudantes
 * Agora suporta preenchimento automático (Edição).
 */

document.addEventListener('DOMContentLoaded', () => {
    const listaEstudantes = document.getElementById('lista-estudantes');
    const btnAdicionar = document.getElementById('btn-adicionar');
    const template = document.getElementById('template-estudante');

    // Regra de Negócio: Séries por Segmento
    const seriesPorSegmento = {
        'EI': ['Berçário', 'Grupo 1', 'Grupo 2', 'Grupo 3', 'Grupo 4', 'Grupo 5'],
        'AI': ['1º Ano', '2º Ano', '3º Ano', '4º Ano', '5º Ano'],
        'AF': ['6º Ano', '7º Ano', '8º Ano', '9º Ano'],
        'EM': ['1ª Série', '2ª Série', '3ª Série']
    };

    let estudanteCounter = 0;

    /**
     * Cria um card de estudante.
     * @param {Object|null} dados (Opcional) Objeto com {nome, segmento, serie, periodo} para preencher.
     */
    function adicionarEstudante(dados = null) {
        const index = estudanteCounter++;
        
        const clone = template.content.cloneNode(true);
        const card = clone.querySelector('.estudante-card');
        
        // Configuração visual do card
        card.setAttribute('data-index', index);
        card.querySelector('.numero-estudante').textContent = document.querySelectorAll('.estudante-card').length + 1;
        
        // Ajusta os 'names' dos inputs para o Flask entender (ex: estudantes[0][nome])
        card.querySelectorAll('[name]').forEach(input => {
            const name = input.getAttribute('name').replace('{index}', index);
            input.setAttribute('name', name);
        });

        // Botão de Remover
        card.querySelector('.btn-remove').addEventListener('click', () => {
            // Permite remover se houver mais de 1 card OU se for edição (pode querer limpar tudo?)
            // Vamos manter a regra: Pelo menos 1 estudante para validar.
            if (document.querySelectorAll('.estudante-card').length > 1) {
                card.remove();
                atualizarNumeracao();
            } else {
                alert("Você precisa manter pelo menos um estudante no cadastro.");
            }
        });

        // Lógica dos Selects (Segmento -> Série)
        const selectSegmento = card.querySelector('.select-segmento');
        const selectSerie = card.querySelector('.select-serie');
        const selectPeriodo = card.querySelector('.select-periodo'); // Adicionei classe no HTML abaixo
        const inputNome = card.querySelector('.input-nome');         // Adicionei classe no HTML abaixo

        // Função auxiliar para popular séries
        function popularSeries(segmento, serieSelecionada = null) {
            const opcoes = seriesPorSegmento[segmento] || [];
            selectSerie.innerHTML = '<option value="" disabled selected>Selecione a série...</option>';
            
            opcoes.forEach(serie => {
                const option = document.createElement('option');
                option.value = serie;
                option.textContent = serie;
                if (serie === serieSelecionada) {
                    option.selected = true;
                }
                selectSerie.appendChild(option);
            });
            selectSerie.disabled = false;
        }

        // Evento de mudança no Segmento
        selectSegmento.addEventListener('change', (e) => {
            popularSeries(e.target.value);
        });

        // --- PREENCHIMENTO AUTOMÁTICO (Caso seja Edição) ---
        if (dados) {
            inputNome.value = dados.nome || '';
            
            if (dados.segmento) {
                selectSegmento.value = dados.segmento;
                // Popula as séries baseadas no segmento carregado
                popularSeries(dados.segmento, dados.serie);
            }

            if (dados.periodo) {
                selectPeriodo.value = dados.periodo;
            }
        }

        listaEstudantes.appendChild(card);
    }

    function atualizarNumeracao() {
        document.querySelectorAll('.estudante-card').forEach((card, i) => {
            card.querySelector('.numero-estudante').textContent = i + 1;
        });
    }

    btnAdicionar.addEventListener('click', () => adicionarEstudante());

    // --- INICIALIZAÇÃO ---
    // Verifica se existe a variável global 'DADOS_ESTUDANTES' (injetada pelo Flask)
    if (typeof DADOS_ESTUDANTES !== 'undefined' && DADOS_ESTUDANTES.length > 0) {
        // Modo Edição: Cria cards para cada aluno existente
        DADOS_ESTUDANTES.forEach(estudante => {
            adicionarEstudante(estudante);
        });
    } else {
        // Modo Cadastro Zero: Cria um card vazio
        adicionarEstudante();
    }
});