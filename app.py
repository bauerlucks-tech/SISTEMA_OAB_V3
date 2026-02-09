<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema OAB - Administração</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <h1 class="mb-4">Sistema OAB - Gerador de Carteirinhas</h1>
        
        <div class="card mb-4">
            <div class="card-header">
                <h4>Status do Sistema</h4>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4">
                        <div class="alert {{ 'alert-success' if frente else 'alert-warning' }}">
                            <strong>PSD Frente:</strong><br>
                            {{ frente if frente else 'Não carregado' }}
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="alert {{ 'alert-success' if verso else 'alert-warning' }}">
                            <strong>PSD Verso:</strong><br>
                            {{ verso if verso else 'Não carregado' }}
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="alert {{ 'alert-success' if area_configurada else 'alert-warning' }}">
                            <strong>Área da Foto:</strong><br>
                            {{ 'Configurada' if area_configurada else 'Não configurada' }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card mb-4">
            <div class="card-header">
                <h4>Upload de PSDs</h4>
            </div>
            <div class="card-body">
                <form action="/upload_psd" method="post" enctype="multipart/form-data">
                    <input type="hidden" name="tipo" value="frente">
                    <div class="mb-3">
                        <label class="form-label">PSD Frente:</label>
                        <input type="file" name="psd" class="form-control" accept=".psd" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Upload PSD Frente</button>
                </form>
                
                <hr>
                
                <form action="/upload_psd" method="post" enctype="multipart/form-data">
                    <input type="hidden" name="tipo" value="verso">
                    <div class="mb-3">
                        <label class="form-label">PSD Verso:</label>
                        <input type="file" name="psd" class="form-control" accept=".psd" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Upload PSD Verso</button>
                </form>
            </div>
        </div>
        
        <div class="card mb-4">
            <div class="card-header">
                <h4>Menu de Navegação</h4>
            </div>
            <div class="card-body">
                <div class="d-grid gap-2 d-md-block">
                    <a href="/configurar" class="btn btn-info">Configurar Campos</a>
                    <a href="/visualizar" class="btn btn-warning">Área da Foto</a>
                    <a href="/gerar" class="btn btn-success">Gerar Carteirinha</a>
                </div>
            </div>
        </div>
        
        {% if total_geracoes > 0 %}
        <div class="card">
            <div class="card-header">
                <h4>Histórico ({{ total_geracoes }} gerações)</h4>
            </div>
            <div class="card-body">
                <ul>
                    {% for geracao in ultimas_geracoes %}
                    <li>{{ geracao[0] }} - {{ geracao[1] }} ({{ geracao[2] }})</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
        {% endif %}
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>