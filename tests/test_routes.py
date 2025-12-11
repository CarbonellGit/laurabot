def test_home_page(client):
    """Teste para verificar se a página inicial carrega (redireciona para login ou mostra home)."""
    response = client.get('/', follow_redirects=True)
    assert response.status_code == 200
    # Verifica se carregou algum conteúdo esperado, ex: título no base.html
    assert b"LauraBot" in response.data

def test_health_check(client):
    """Teste da rota de health check."""
    response = client.get('/health')
    assert response.status_code == 200
    assert b"Servidor LauraBot no ar!" in response.data

def test_404_page(client):
    """Teste para verificar se a página 404 é exibida para rotas inexistentes."""
    response = client.get('/rota-que-nao-existe')
    assert response.status_code == 404
    assert b"404" in response.data
    # Decodifica o conteúdo para verificar a string com acentos
    content = response.data.decode('utf-8')
    assert "Página não encontrada" in content
