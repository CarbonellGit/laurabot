/*
 * Lógica do Cadastro de Estudantes
 * Gerencia adição dinâmica de formulários e dependência Segmento -> Série.
 */

document.addEventListener('DOMContentLoaded', () => {
    const listaEstudantes = document.getElementById('lista-estudantes');
    const btnAdicionar = document.getElementById('btn-adicionar');
    const template = document.getElementById('template-estudante');

    const seriesPorSegmento = {
        'EI': ['Berçário', 'Grupo 1', 'Grupo 2', 'Grupo 3', 'Grupo 4', 'Grupo 5'],
        'AI': ['1º Ano', '2º Ano', '3º Ano', '4º Ano', '5º Ano'],
        'AF': ['6º Ano', '7º Ano', '8º Ano', '9º Ano'],
        'EM': ['1ª Série', '2ª Série', '3ª Série']
    };

    let estudanteCounter = 0;

    function adicionarEstudante() {
        const index = estudanteCounter++;
        
        const clone = template.content.cloneNode(true);
        const card = clone.querySelector('.estudante-card');
        
        card.setAttribute('data-index', index);
        card.querySelector('.numero-estudante').textContent = document.querySelectorAll('.estudante-card').length + 1;
        
        // Atualiza names para: estudantes[0][nome]
        card.querySelectorAll('[name]').forEach(input => {
            const name = input.getAttribute('name').replace('{index}', index);
            input.setAttribute('name', name);
        });

        card.querySelector('.btn-remove').addEventListener('click', () => {
            if (document.querySelectorAll('.estudante-card').length > 1) {
                card.remove();
                atualizarNumeracao();
            } else {
                alert("Você precisa cadastrar pelo menos um estudante.");
            }
        });

        const selectSegmento = card.querySelector('.select-segmento');
        const selectSerie = card.querySelector('.select-serie');

        selectSegmento.addEventListener('change', (e) => {
            const segmento = e.target.value;
            const opcoes = seriesPorSegmento[segmento] || [];
            
            selectSerie.innerHTML = '<option value="" disabled selected>Selecione a série...</option>';
            
            opcoes.forEach(serie => {
                const option = document.createElement('option');
                option.value = serie;
                option.textContent = serie;
                selectSerie.appendChild(option);
            });

            selectSerie.disabled = false;
        });

        listaEstudantes.appendChild(card);
    }

    function atualizarNumeracao() {
        document.querySelectorAll('.estudante-card').forEach((card, i) => {
            card.querySelector('.numero-estudante').textContent = i + 1;
        });
    }

    btnAdicionar.addEventListener('click', adicionarEstudante);

    // Inicializa com 1
    adicionarEstudante();
});