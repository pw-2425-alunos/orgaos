import json
import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_EXCEL_FILE = BASE_DIR / "catalogo_todas_as_obras.xlsx"
DEFAULT_OUTPUT_FILE = BASE_DIR / "short.json"

MAPA_NOTAS = {
    "Do": "Dó",
    "Re": "Ré",
    "Fa": "Fá",
    "La": "Lá"
}

MAPA_NOTAS_CANONICAS = {
    "do": "Dó",
    "dó": "Dó",
    "re": "Ré",
    "ré": "Ré",
    "mi": "Mi",
    "fa": "Fá",
    "fá": "Fá",
    "sol": "Sol",
    "la": "Lá",
    "lá": "Lá",
    "si": "Si",
}

PALAVRAS_MINUSCULAS = {
    "a", "ao", "aos", "as", "da", "das", "de", "do", "dos",
    "e", "em", "na", "nas", "no", "nos", "o", "os", "por"
}


# ---------------------------------------------------
# UTILIDADES
# ---------------------------------------------------

def limpar(v):
    """Normaliza valores vindos do Excel"""

    if v is None:
        return None

    try:
        if pd.isna(v):
            return None
    except:
        pass

    v = str(v)

    v = v.replace("\xa0", " ")
    v = v.strip()

    if v == "":
        return None

    return v


def normalizar_acidentes(txt):
    """Aceita b/# e normaliza para ♭/♯"""
    if not txt:
        return txt

    txt = txt.replace("♭", "b")
    txt = txt.replace("♯", "#")

    return txt


def simbolo_acidente(a):
    if a == "b":
        return "♭"
    if a == "#":
        return "♯"
    return ""


def normalizar_nota(nota):
    if not nota:
        return None

    nota = str(nota).strip()
    nota = re.sub(r"\s+", "", nota)

    match = re.match(r"^(Do|Dó|Re|Ré|Mi|Fa|Fá|Sol|La|Lá|Si)([b#♭♯]?)$", nota, re.IGNORECASE)
    if not match:
        return nota or None

    base = MAPA_NOTAS_CANONICAS.get(match.group(1).lower(), match.group(1))
    acidente = simbolo_acidente(match.group(2).replace("♭", "b").replace("♯", "#"))

    return f"{base}{acidente}" if acidente else base


def normalizar_modo(modo):
    if not modo:
        return None

    modo_txt = re.sub(r"[^A-Za-zÀ-ÿ]", "", str(modo).strip())

    if modo_txt == "M" or modo_txt.lower() == "maior":
        return "Maior"

    if modo_txt == "m" or modo_txt.lower() == "menor":
        return "menor"

    return None


def garantir_title(txt):
    if not txt:
        return txt

    txt = str(txt).strip()

    if not txt:
        return txt

    palavras = txt.split()
    resultado = []
    ultima_posicao = len(palavras) - 1

    for indice, palavra in enumerate(palavras):
        palavra_title = palavra[:1].upper() + palavra[1:].lower() if palavra else palavra
        palavra_limpa = re.sub(r"^[^A-Za-zÀ-ÿ]*|[^A-Za-zÀ-ÿ]*$", "", palavra).lower()

        if indice not in {0, ultima_posicao} and palavra_limpa in PALAVRAS_MINUSCULAS:
            palavra_title = palavra.lower()

        resultado.append(palavra_title)

    return " ".join(resultado)


def extrair_tonalidade_do_titulo(titulo):
    if not titulo:
        return None

    pattern = re.compile(
        r"^(?P<base>.+?)\s*(?:em\s+)?(?P<nota>Dó|Ré|Mi|Fá|Sol|Lá|Si|Do|Re|Fa|La)(?P<acc>[♭♯b#])?\s*(?P<modo>M|m|Maior|menor)\s*$",
        re.IGNORECASE,
    )

    match = pattern.match(str(titulo).strip())
    if not match:
        return None

    base = match.group("base").strip(" -\t")
    nota = normalizar_nota((match.group("nota") or "") + (match.group("acc") or ""))
    modo = normalizar_modo(match.group("modo"))

    if not base or not nota or not modo:
        return None

    return {
        "base": base,
        "nota": nota,
        "modo": modo,
    }


def corrigir_titulo_obra(titulo, nota, modo):
    parse = extrair_tonalidade_do_titulo(titulo)

    if not parse:
        return garantir_title(titulo)

    nota_normalizada = normalizar_nota(nota)
    modo_normalizado = normalizar_modo(modo)

    if parse["nota"] == nota_normalizada and parse["modo"] == modo_normalizado:
        return garantir_title(parse["base"])

    return garantir_title(titulo)


# ---------------------------------------------------
# COMPOSITOR
# ---------------------------------------------------

def parse_compositor(txt):

    txt = limpar(txt)

    if not txt:
        return None

    txt = txt.replace("XYZ", "").strip()

    if "," in txt:
        apelido, nome = txt.split(",", 1)

        return {
            "apelido": limpar(apelido),
            "nome": limpar(nome)
        }

    partes = txt.split()

    if len(partes) == 1:
        return {
            "apelido": partes[0],
            "nome": None
        }

    return {
        "apelido": partes[-1],
        "nome": " ".join(partes[:-1])
    }


# ---------------------------------------------------
# TONALIDADE
# ---------------------------------------------------

def parse_tonalidade(txt):

    txt = limpar(txt)

    if not txt:
        return None, None

    txt = normalizar_acidentes(txt)

    match = re.match(
        r"^\s*(?P<nota>Do|Dó|Re|Ré|Mi|Fa|Fá|Sol|La|Lá|Si)(?P<acc>[b#]?)\s*(?P<modo>M|m|Maior|menor)?\s*$",
        txt,
        re.IGNORECASE,
    )

    if not match:
        return None, None

    nota_parte = normalizar_nota((match.group("nota") or "") + (match.group("acc") or ""))
    modo = normalizar_modo(match.group("modo"))

    if modo is None:
        modo = "Maior"

    return nota_parte, modo

# ---------------------------------------------------
# EXTENSÕES
# ---------------------------------------------------

def parse_extensao(txt):

    txt = limpar(txt)

    if not txt:
        return None

    txt = normalizar_acidentes(txt)
    txt = re.sub(r"\s+", "", txt)

    m = re.match(
        r"^(Dó|Ré|Mi|Fá|Sol|Lá|Si|Do|Re|Fa|La)(#|b)?(\d+)(.*)$",
        txt
    )

    if not m:
        return None

    nota = m.group(1)

    mapa = {
        "Do": "Dó",
        "Re": "Ré",
        "Fa": "Fá",
        "La": "Lá"
    }

    nota = mapa.get(nota, nota)

    acidente = simbolo_acidente(m.group(2))

    if acidente:
        nota += acidente

    oitava = int(m.group(3))

    modificador = limpar(m.group(4))

    return {
        "nota": nota,
        "oitava": oitava,
        "tipo": modificador
    }


# ---------------------------------------------------
# PROCURAR SECÇÃO
# ---------------------------------------------------

def encontrar_secao(df, titulo):

    titulo = titulo.lower()

    for i in range(len(df)):

        valor = limpar(df.iloc[i, 0])

        if valor and titulo in valor.lower():
            return i

    return None


# ---------------------------------------------------
# LER FOLHA
# ---------------------------------------------------

def ler_folha(df, id_obra):

    dados = {}

    for i in range(len(df)):

        chave = limpar(df.iloc[i, 0])
        valor = limpar(df.iloc[i, 1])

        if chave:
            dados[chave] = valor

    obm = dados.get("Código")
    compositor = parse_compositor(dados.get("Compositor"))
    nota, modo = parse_tonalidade(dados.get("Tonalidade"))

    obra = {
        "id": id_obra,
        "obm": obm,
        "titulo": corrigir_titulo_obra(dados.get("Título"), nota, modo),
        "ano": dados.get("Ano"),
        "efectivo_vocal": dados.get("Efectivo Vocal"),
        "efectivo_orgao": dados.get("Efectivo Órgão"),
        "genero": dados.get("Género"),
        "descricao_fisica": dados.get("Descrição física"),
        "onomastica": dados.get("Onomástica"),
        "referencias": dados.get("Referências"),
    }

    # ---------------------------------------------------
    # EXTENSÕES
    # ---------------------------------------------------

    orgaos = []

    linha_ext = encontrar_secao(df, "Extensões")

    if linha_ext is not None:

        i = linha_ext + 2
        ordem = 1

        while i < len(df):

            nome = limpar(df.iloc[i, 0])

            if not nome:
                break

            if "Regista" in nome:
                break

            inicio = parse_extensao(df.iloc[i, 1])
            fim = parse_extensao(df.iloc[i, 2])

            orgaos.append({
                "nome": nome,
                "extensao_inicio": inicio,
                "extensao_fim": fim,
                "ordem": ordem,
                "registacoes": []
            })

            ordem += 1
            i += 1

    # ---------------------------------------------------
    # REGISTAÇÕES
    # ---------------------------------------------------

    linha_reg = encontrar_secao(df, "Regista")

    if linha_reg is not None:

        registacoes_por_orgao = {}
        ordem_reg = {}

        i = linha_reg + 2

        while i < len(df):

            orgao = limpar(df.iloc[i, 0])

            if not orgao:
                i += 1
                continue

            if orgao not in registacoes_por_orgao:
                registacoes_por_orgao[orgao] = []
                ordem_reg[orgao] = 1

            reg = {
                "mao_esquerda": limpar(df.iloc[i, 1]),
                "mao_direita": limpar(df.iloc[i, 2]),
                "geral": limpar(df.iloc[i, 3]),
                "numero": limpar(df.iloc[i, 4]),
                "ordem": ordem_reg[orgao]
            }

            registacoes_por_orgao[orgao].append(reg)

            ordem_reg[orgao] += 1

            i += 1

        for org in orgaos:

            nome = org["nome"]

            org["registacoes"] = registacoes_por_orgao.get(nome, [])

    return {
        "compositor": compositor,
        "tonalidade": {
            "nota": nota,
            "modo": modo
        },
        "obra": obra,
        "orgaos": orgaos
    }


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

def gerar_json(excel_file=DEFAULT_EXCEL_FILE, output_file=DEFAULT_OUTPUT_FILE):

    excel_path = Path(excel_file)
    if not excel_path.is_absolute():
        excel_path = BASE_DIR / excel_path

    output_path = Path(output_file)
    if not output_path.is_absolute():
        output_path = BASE_DIR / output_path

    xls = pd.ExcelFile(excel_path)

    obras = []

    id_obra = 1

    for sheet in xls.sheet_names[1:]:

        df = pd.read_excel(
            xls,
            sheet_name=sheet,
            header=None
        )

        obra = ler_folha(df, id_obra)

        obras.append(obra)

        id_obra += 1

    with output_path.open("w", encoding="utf8") as f:

        json.dump(
            obras,
            f,
            ensure_ascii=False,
            indent=4
        )

    return len(obras), output_path


def main(excel_file=DEFAULT_EXCEL_FILE, output_file=DEFAULT_OUTPUT_FILE):

    total_obras, output_path = gerar_json(excel_file=excel_file, output_file=output_file)
    print("JSON gerado com", total_obras, "obras em", output_path)


# ---------------------------------------------------

if __name__ == "__main__":
    main()