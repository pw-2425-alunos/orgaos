import pandas as pd
import json
import re

EXCEL_FILE = "catalogo_todas_as_obras.xlsx"


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

    # separar partes
    partes = txt.split()

    nota_parte = partes[0]

    modo = None

    if len(partes) > 1:
        modo_txt = partes[1].lower()

        if modo_txt in ["m", "menor"]:
            modo = "menor"

        elif modo_txt in ["m", "maior", "M"]:
            modo = "Maior"

    # extrair nota
    m = re.match(r"^(Dó|Ré|Mi|Fá|Sol|Lá|Si)(#|b)?$", nota_parte)

    if not m:
        return None, None

    nota = m.group(1)

    acidente = simbolo_acidente(m.group(2))

    if acidente:
        nota += acidente

    if modo is None:
        modo = "Maior"

    return nota, modo

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
        "titulo": dados.get("Título"),
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

def main():

    xls = pd.ExcelFile(EXCEL_FILE)

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

    with open("short.json", "w", encoding="utf8") as f:

        json.dump(
            obras,
            f,
            ensure_ascii=False,
            indent=4
        )

    print("JSON gerado com", len(obras), "obras")


# ---------------------------------------------------

if __name__ == "__main__":
    main()