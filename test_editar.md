# Teste de Edição de Órgãos

## Implementação Completa

### O que foi implementado:

1. **View `editar_obra_view`**:
   - Adicionada linha para deletar órgãos existentes antes de criar novos: `obra.orgaos.all().delete()`
   - Adicionado código para serializar órgãos existentes com suas registações em JSON
   - Passado `orgaos_json` no contexto para o template

2. **Template `editar_obra.html`**:
   - Adicionada variável JavaScript `orgaosExistentes` com dados JSON do Django
   - Adicionado event listener `DOMContentLoaded` para carregar órgãos ao abrir a página
   - Modificada função `addOrgao()` para aceitar parâmetro `orgaoData` opcional
   - Quando `orgaoData` existe, preenche os campos de extensão e ordem
   - Carrega registações existentes automaticamente
   - Modificada função `addRegistacao()` para aceitar `regData` opcional
   - Quando `regData` existe, preenche os campos de registos

### Como testar:

1. Inicie o servidor: `python manage.py runserver`
2. Faça login: http://127.0.0.1:8000/login (admin/Admin6Orgaos)
3. Crie uma obra com órgãos e registações
4. Clique em "Editar obra"
5. Verifique se os órgãos e registações aparecem automaticamente
6. Modifique/adicione/remova órgãos
7. Salve e verifique se as alterações foram aplicadas

### Fluxo de edição:

1. **Carregamento da página**:
   - Django busca órgãos e registações da obra
   - Serializa para JSON
   - JavaScript carrega automaticamente ao abrir a página

2. **Durante edição**:
   - Usuário pode adicionar novos órgãos (+Adicionar Órgão)
   - Pode remover órgãos existentes (✕ Remover)
   - Pode modificar extensões e registações

3. **Ao salvar**:
   - Todos os órgãos antigos são deletados
   - Novos órgãos são criados com os dados do formulário
   - Registações são criadas automaticamente
