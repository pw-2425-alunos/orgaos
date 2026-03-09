import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from obras.models import (
    Compositor, Genero, Nota, Modo, Tonalidade,
    Obra, Extensao, Orgao, Registo, Registacao
)


def carregar_json(ficheiro="auxiliar/short.json"):

    with open(ficheiro, encoding="utf8") as f:
        dados = json.load(f)

    # caches para evitar queries repetidas
    notas_cache = {}
    modos_cache = {}
    generos_cache = {}
    registos_cache = {}

    for item in dados:

        # -----------------------
        # COMPOSITOR
        # -----------------------

        comp = item["compositor"]

        compositor, _ = Compositor.objects.get_or_create(
            nome=comp["nome"] or "",
            apelido=comp["apelido"] or ""
        )

        # -----------------------
        # TONALIDADE
        # -----------------------

        tonalidade = None
        ton = item.get("tonalidade")

        if ton and ton["nota"]:

            nota_nome = ton["nota"]

            if nota_nome not in notas_cache:
                nota_obj, _ = Nota.objects.get_or_create(nome=nota_nome)
                notas_cache[nota_nome] = nota_obj

            nota = notas_cache[nota_nome]

            modo = None
            if ton["modo"]:

                modo_nome = ton["modo"]

                if modo_nome not in modos_cache:
                    modo_obj, _ = Modo.objects.get_or_create(nome=modo_nome)
                    modos_cache[modo_nome] = modo_obj

                modo = modos_cache[modo_nome]

            tonalidade, _ = Tonalidade.objects.get_or_create(
                nota=nota,
                modo=modo
            )

        # -----------------------
        # GENERO
        # -----------------------

        genero = None
        genero_nome = item["obra"]["genero"]

        if genero_nome:

            if genero_nome not in generos_cache:
                genero_obj, _ = Genero.objects.get_or_create(nome=genero_nome)
                generos_cache[genero_nome] = genero_obj

            genero = generos_cache[genero_nome]

        # -----------------------
        # OBRA
        # -----------------------

        obra_data = item["obra"]

        ano = None
        if obra_data["ano"]:
            try:
                ano = int(obra_data["ano"])
            except:
                ano = None

        obra = Obra.objects.create(
            titulo=obra_data["titulo"] or "",
            compositor=compositor,
            ano=ano,
            efectivo_vocal=obra_data["efectivo_vocal"] or "",
            efectivo_orgao=obra_data["efectivo_orgao"] or "",
            tonalidade=tonalidade,
            genero=genero,
            descricao_fisica=obra_data["descricao_fisica"] or "",
            onomastica=obra_data["onomastica"] or "",
            referencias=obra_data["referencias"] or ""
        )

        # -----------------------
        # ORGÃOS
        # -----------------------

        for org in item["orgaos"]:

            # extensão início
            ext_inicio = None
            if org["extensao_inicio"]:

                ei = org["extensao_inicio"]

                nota_nome = ei["nota"]

                if nota_nome not in notas_cache:
                    nota_obj, _ = Nota.objects.get_or_create(nome=nota_nome)
                    notas_cache[nota_nome] = nota_obj

                nota = notas_cache[nota_nome]

                ext_inicio = Extensao.objects.create(
                    nota=nota,
                    oitava=ei["oitava"],
                    tipo=ei["tipo"] or ""
                )

            # extensão fim
            ext_fim = None
            if org["extensao_fim"]:

                ef = org["extensao_fim"]

                nota_nome = ef["nota"]

                if nota_nome not in notas_cache:
                    nota_obj, _ = Nota.objects.get_or_create(nome=nota_nome)
                    notas_cache[nota_nome] = nota_obj

                nota = notas_cache[nota_nome]

                ext_fim = Extensao.objects.create(
                    nota=nota,
                    oitava=ef["oitava"],
                    tipo=ef["tipo"] or ""
                )

            orgao = Orgao.objects.create(
                obra=obra,
                nome=org["nome"],
                extensao_inicio=ext_inicio,
                extensao_fim=ext_fim,
                ordem=org["ordem"]
            )

            # -----------------------
            # REGISTAÇÕES
            # -----------------------

            for reg in org["registacoes"]:

                def get_registo(nome):

                    if not nome:
                        nome = "—"

                    if nome not in registos_cache:
                        obj, _ = Registo.objects.get_or_create(nome=nome)
                        registos_cache[nome] = obj

                    return registos_cache[nome]

                geral = get_registo(reg["geral"])
                mao_esquerda = get_registo(reg["mao_esquerda"])
                mao_direita = get_registo(reg["mao_direita"])

                numero = None
                try:
                    numero = int(reg["numero"])
                except:
                    numero = 0

                Registacao.objects.create(
                    orgao=orgao,
                    geral=geral,
                    mao_esquerda=mao_esquerda,
                    mao_direita=mao_direita,
                    numero=numero,
                    ordem=reg["ordem"]
                )

    print("Importação concluída:", len(dados), "obras")


if __name__ == "__main__":
    carregar_json()
