# CI/CD para WebHS

# Localização dos Dados

Para carregar dados na base de dados, este projeto usa duas origens distintas:

* Excel do catálogo: por omissão em `auxiliar/catalogo_todas_as_obras.xlsx`.
* Ficheiros Word do catálogo: por omissão em `auxiliar/catalogo`, mas podem estar noutra pasta. No cenário atual, por exemplo, podem estar em `C:\Users\lucio\Downloads\catalogo\catalogo`.

## Como configurar

Não é preciso alterar código para mudar a localização destes ficheiros. Os caminhos podem ser passados diretamente nos commands.

### ETL Excel ➡️ BD

Por omissão carrega Excel de `auxiliar/`:
```parse
> python .\manage.py gera_json
```

Com outro ficheiro Excel:
```parse
> python .\manage.py gera_json --excel-file "C:\Users\lucio\Downloads\catalogo\catalogo_todas_as_obras.xlsx"
```

Também é possível escolher explicitamente onde gravar o JSON gerado:
```parse
> python .\manage.py gera_json --excel-file "C:\Users\lucio\Downloads\catalogo\catalogo_todas_as_obras.xlsx" --output auxiliar\short.json
```

### ETL Catalogos em Word ➡️ BR

Por omissão, carrega words da pasta `auxiliar/catalogo`:
```parse
> python .\manage.py import_catalogo_info
```

Com outra pasta de DOCX:
```parse
> python .\manage.py import_catalogo_info --source-dir "C:\Users\lucio\Downloads\catalogo\catalogo"
```

Se também estiveres a usar o command que extrai OBM a partir dos DOCX, a configuração é feita da mesma forma:
```parse
> python .\manage.py import_obm_from_catalogo --source-dir "C:\Users\lucio\Downloads\catalogo\catalogo"
```

## Recomendação prática

* Se quiseres zero configuração, coloca o Excel em `auxiliar/catalogo_todas_as_obras.xlsx` e os DOCX em `auxiliar/catalogo`.
* Se preferires manter os dados fora do repositório, usa `--excel-file` e `--source-dir` nos commands.
* O ponto importante é que os commands devem ser executados a partir da raiz do projeto.

* dar commmit e push para remote GitHub
* em [WebHS](https://hosting45.serverhs.org:2083/cpsess7752493317/frontend/jupiter/version_control/index.html#/manage/%252Fhome%252Fobmdatab%252Frepositories%252Forgaos-2/deploy), Git\Pull or Deploy, fazer Ùpdate from Remote`
* em [WebApplication](https://hosting45.serverhs.org:2083/cpsess7752493317/frontend/jupiter/lveversion/python-selector.html.tt#/applications/repositories%2Forgaos-2):
   * executar collect static, 
   * eventualmente run pip install -r requirements.txt se houve novos packages 
   * dar restart da app



# BD
está independente em WebHS. mantém persistentes alterações que se façam


# Processo ETL Excel -> BD

Converter para JSON:
```parse
> python .\manage.py gera_json
```

Com caminhos explícitos:
```parse
> python .\manage.py gera_json --excel-file auxiliar\catalogo_todas_as_obras.xlsx --output auxiliar\short.json
```

criar base de dados:
```parse
> python .\manage.py migrate
```

carregar obras:
```parse
> python .\manage.py carrega_obras
```

Com caminho explícito para o JSON:
```parse
> python .\manage.py carrega_obras --ficheiro auxiliar\short.json
```

Notas:
* `gera_json` lê por omissão `auxiliar/catalogo_todas_as_obras.xlsx` e escreve `auxiliar/short.json`.
* `carrega_obras` lê por omissão `auxiliar/short.json`.
* O fluxo oficial deve ser feito via `manage.py`, usando os commands `gera_json` e `carrega_obras`.

# Catalogo PDF / Word

## Rationale
Ha varios ficheiros word com info de obras. Para cada compositor:
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

### 1) Remover Headers de DOCX

remover os headers dos ficheirois DOCX com
```bash
python limpa_headers_word.py
```

### 1) ETL do conteúdo HTML + imagens de cada obra

Lê os DOCX em `auxiliar/catalogo` (ou outra pasta a especificar), extrai conteúdo por obra, guarda HTML em `Obra.info_catalogo` e imagens de forma persistente em `mediafiles/catalogo/...`.

vai converter as imagens para 800px de largura, embora a resolução original seja muito maior

Teste sem gravar:
```bash
python manage.py import_catalogo_info --dry-run
```

Execução real:
```bash
python manage.py import_catalogo_info
```

Execução de outra pasta:
```bash
python manage.py import_catalogo_info --source-dir "C:\Users\lucio\Downloads\catalogacao\catalogacao"
```

Execução real limpando primeiro o campo `info_catalogo`:
```bash
python manage.py import_catalogo_info --clear
```

### Notas

* Os dois comandos podem ser reexecutados sempre que houver alterações nos ficheiros Word.
* Ambos mostram no terminal os códigos sem correspondência na BD.
* O comando de catálogo serve imagens por `MEDIA_URL` (pasta persistente em `MEDIA_ROOT`).
* Se a app estiver montada num subpath (ex.: `/web`), definir no `.env`:
   ```env
   URL_PREFIX=/web
   ```
   Isto ajusta automaticamente `STATIC_URL` e `MEDIA_URL` para `/web/static/` e `/web/media/`.

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


