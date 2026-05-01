# CI/CD para WebHS

* dar commmit e push para remote GitHub
* em [WebHS](https://hosting45.serverhs.org:2083/cpsess7752493317/frontend/jupiter/version_control/index.html#/manage/%252Fhome%252Fobmdatab%252Frepositories%252Forgaos-2/deploy), Git\Pull or Deploy, fazer Ùpdate from Remote`
* em [WebApplication](https://hosting45.serverhs.org:2083/cpsess7752493317/frontend/jupiter/lveversion/python-selector.html.tt#/applications/repositories%2Forgaos-2):
   * executar collect static, 
   * eventualmente run pip install -r requirements.txt se houve novos packages 
   * dar restart da app



# BD
está independente em WebHS. mantém persistentes alterações que se façam

sequencia de comandos:
```parse
auxiliar> python gera_json.py
> python .\manage.py migrate
> python .\carrega_obras.py
> python manage.py import_catalogo_info --source-dir "C:\Users\lucio\Downloads\catalogacao\catalogacao"
```

# Códigos sem obra correspondente

Secções preparadas: 170
Códigos sem obra correspondente: 03-03, 03-05, 03-09, 03-15, 03-16, 03-17, 03-19, 03-25, 03-26, 03-28, 04-03, 04-05, 04-07, 04-09, 04-11, 04-13, 04-15, 04-17, 04-19, 04-21, 04-23, 04-25, 04-27, 05-07, 05-09, 05-11, 05-13, 05-15, 05-17, 05-18, 05-19, 05-20, 05-21, 05-23, 14-18, 35-62, 57-58, 58-60, 59-60, 62-63, 63-87, 68-74, 74-75, 75-77, 78-79, 79-80, 81-82, 86-87, 90-92, 92-93, 94-95, 96-98

# Processo ETL Excel -> BD

Converter para JSON:
```parse
auxiliar>python gera_json.py
```

criar base de dados:
```parse
> python .\manage.py migrate
```

carregar obras:
```parse
> python .\carrega_obras.py
```

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

### 1) ETL do conteúdo HTML + imagens de cada obra

Lê os DOCX em `auxiliar/catalogo` (ou outra pasta a especificar), extrai conteúdo por obra, guarda HTML em `Obra.info_catalogo` e imagens de forma persistente em `mediafiles/catalogo/...`.

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


