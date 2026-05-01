# CI/CD para WebHS

* dar commmit e push para remote GitHub
* em [WebHS](https://hosting45.serverhs.org:2083/cpsess7752493317/frontend/jupiter/version_control/index.html#/manage/%252Fhome%252Fobmdatab%252Frepositories%252Forgaos-2/deploy), Git\Pull or Deploy, fazer Ùpdate from Remote`
* em [WebApplication](https://hosting45.serverhs.org:2083/cpsess7752493317/frontend/jupiter/lveversion/python-selector.html.tt#/applications/repositories%2Forgaos-2):
   * executar collect static, 
   * eventualmente run pip install -r requirements.txt se houve novos packages 
   * dar restart da app

# BD
está independente em WebHS. mantém persistentes alterações que se façam


# Catalogo PDF / Word

tenho varios ficheiros word nesta pasta. cada word é de um compositor. Para cada compositor:
* limpar headers do word com o programa `auxiliar/limpa_headers_word.py`
* converter word para HTML com `pandoc catalogo.docx -o catalogo.html --extract-media=imagens`
* cada obra esta identificada pelo OBM na classe Obra. Esse codigo também está no word, marcando o inicio do conteúdo que quero extrair da obra, até ao proximo OBM.
* extrair conteudo de cada obra e colocar o HTML na respetiva obra, num novo atributo "info_catalogo", que usamos com safe para poder renderizar o HTML.


## Processo ETL (Word -> Base de Dados)

### Pré-requisitos

1. Ativar ambiente virtual
   ```bash
   source .venv/bin/activate
   ```

2. Instalar dependências Python (se necessário)
   ```bash
   pip install -r requirements.txt
   ```

3. Instalar pandoc (se necessário)
   ```bash
   sudo apt update
   sudo apt install pandoc
   ```

4. Garantir migrações aplicadas
   ```bash
   python manage.py migrate
   ```

### 1) ETL do OBM

Lê os DOCX em `auxiliar/catalogo`, extrai os códigos OBM e preenche `Obra.obm` com match por `Obra.codigo`.

Teste sem gravar:
```bash
python manage.py import_obm_from_catalogo --dry-run
```

Execução real:
```bash
python manage.py import_obm_from_catalogo
```

### 2) ETL do conteúdo HTML + imagens

Lê os DOCX em `auxiliar/catalogo`, extrai conteúdo por obra, guarda HTML em `Obra.info_catalogo` e imagens de forma persistente em `mediafiles/catalogo/...`.

Teste sem gravar:
```bash
python manage.py import_catalogo_info --dry-run
```

Execução real:
```bash
python manage.py import_catalogo_info
```

Execução real limpando primeiro o campo `info_catalogo`:
```bash
python manage.py import_catalogo_info --clear
```

### Ordem recomendada

```bash
python manage.py import_obm_from_catalogo
python manage.py import_catalogo_info
```

### Notas

* Os dois comandos podem ser reexecutados sempre que houver alterações nos ficheiros Word.
* Ambos mostram no terminal os códigos sem correspondência na BD.
* O comando de catálogo serve imagens por `MEDIA_URL` (pasta persistente em `MEDIA_ROOT`).

## Troubleshooting

### python manage.py runserver falha

1. Confirmar ambiente virtual ativo:
   ```bash
   source .venv/bin/activate
   ```

2. Confirmar dependências instaladas:
   ```bash
   pip install -r requirements.txt
   ```

3. Confirmar migrações:
   ```bash
   python manage.py migrate
   ```

4. Verificar configuração de desenvolvimento no `.env`:
   ```env
   DEBUG=True
   ```

5. Verificar estado geral do projeto:
   ```bash
   python manage.py check
   ```

### import_catalogo_info falha com pandoc

Instalar pandoc no sistema:
```bash
sudo apt update
sudo apt install pandoc
```

Validar instalação:
```bash
pandoc --version
```

### Comandos ETL não atualizam todas as obras

* Os comandos atualizam apenas obras com correspondência por código.
* Códigos sem match são listados no fim da execução.
* Use primeiro dry-run para validar cobertura:
  ```bash
  python manage.py import_obm_from_catalogo --dry-run
  python manage.py import_catalogo_info --dry-run
  ```

### Imagens não aparecem localmente

* Confirmar que `DEBUG=True` no `.env` (em desenvolvimento, o projeto serve `/media/` com DEBUG ativo).
* Reexecutar o ETL de catálogo:
  ```bash
  python manage.py import_catalogo_info
  ```
