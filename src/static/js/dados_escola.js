/*
 * Matriz Curricular 2026 - Colégio Carbonell
 * Arquivo compartilhado entre Cadastro e Admin para garantir consistência.
 */

const DADOS_ESCOLA = {
    segmentos: {
        'EI': 'Educação Infantil',
        'AI': 'Anos Iniciais',
        'AF': 'Anos Finais',
        'EM': 'Ensino Médio'
    },
    
    // Define quais séries existem em cada segmento
    series: {
        'EI': ['Infantil 1', 'Infantil 2', 'Infantil 3', 'Infantil 4', 'Infantil 5'],
        'AI': ['1º Ano', '2º Ano', '3º Ano', '4º Ano', '5º Ano'],
        'AF': ['6º Ano', '7º Ano', '8º Ano', '9º Ano'],
        'EM': ['1ª Série', '2ª Série', '3ª Série']
    },

    // Define a GRADE DE TURMAS exata (Baseado no Print 2026)
    // Estrutura: 'Serie': { 'Periodo': ['Turmas'] }
    turmas: {
        // === EI (Estimativa padrão: A=Manhã, B=Tarde) ===
        'Infantil 1': { 'Manhã': ['A'], 'Tarde': ['B'] },
        'Infantil 2': { 'Manhã': ['A'], 'Tarde': ['B'] },
        'Infantil 3': { 'Manhã': ['A'], 'Tarde': ['B'] },
        'Infantil 4': { 'Manhã': ['A'], 'Tarde': ['B'] },
        'Infantil 5': { 'Manhã': ['A'], 'Tarde': ['B'] },

        // === AI (Mapeado do Print) ===
        '1º Ano': { 'Manhã': ['A'], 'Tarde': ['B', 'C'] },
        '2º Ano': { 'Manhã': ['A'], 'Tarde': ['B', 'C'] },
        '3º Ano': { 'Manhã': ['A'], 'Tarde': ['B', 'C'] },
        '4º Ano': { 'Manhã': ['A', 'B'], 'Tarde': ['C'] },
        '5º Ano': { 'Manhã': ['A'], 'Tarde': ['B'] },

        // === AF (Tudo Manhã) ===
        '6º Ano': { 'Manhã': ['A', 'B'] },
        '7º Ano': { 'Manhã': ['A', 'B'] },
        '8º Ano': { 'Manhã': ['A', 'B', 'C'] },
        '9º Ano': { 'Manhã': ['A', 'B'] },

        // === EM (Tudo Manhã) ===
        '1ª Série': { 'Manhã': ['A', 'B'] },
        '2ª Série': { 'Manhã': ['A', 'B'] },
        '3ª Série': { 'Manhã': ['A'] }
    }
};