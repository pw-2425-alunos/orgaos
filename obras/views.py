import json
import re
import string
import unicodedata

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Case, Count, Exists, OuterRef, Q, Value, When
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CompositorForm, ReferenciaFormSet
from .models import Compositor, Extensao, Genero, Nota, Obra, Orgao, Registacao, Registo, Tonalidade


def _normalizar_letra_inicial(texto):
    if not texto:
        return "#"

    inicial = str(texto).strip()[:1].upper()
    if not inicial:
        return "#"

    base = unicodedata.normalize("NFD", inicial)
    sem_acento = "".join(ch for ch in base if unicodedata.category(ch) != "Mn")
    return sem_acento if sem_acento in string.ascii_uppercase else "#"


def _obter_extensao_por_componentes(nota_id, oitava, tipo):
    if not nota_id or not oitava:
        return None

    try:
        nota_id_int = int(nota_id)
        oitava_int = int(oitava)
    except (TypeError, ValueError):
        return None

    tipo_normalizado = (tipo or "").strip()
    if tipo_normalizado not in ["", "*", "s/"]:
        tipo_normalizado = ""

    extensao, _ = Extensao.objects.get_or_create(
        nota_id=nota_id_int,
        oitava=oitava_int,
        tipo=tipo_normalizado,
    )
    return extensao


def landing_view(request):
    context = {
        "total_compositores": Compositor.objects.count(),
        "total_obras": Obra.objects.count(),
        "total_registacoes": Registacao.objects.count(),
    }
    return render(request, "obras/landing.html", context)


def compositores_view(request):
    compositores = Compositor.objects.all().order_by("apelido", "nome")
    grupos = {}

    for compositor in compositores:
        letra = _normalizar_letra_inicial(compositor.apelido or compositor.nome)
        grupos.setdefault(letra, []).append(compositor)

    alfabeto = [{"letra": letra, "ativo": letra in grupos} for letra in string.ascii_uppercase]

    if "#" in grupos:
        alfabeto.append({"letra": "#", "ativo": True})

    grupos_ordenados = [{"letra": letra, "itens": grupos[letra]} for letra in string.ascii_uppercase if letra in grupos]

    if "#" in grupos:
        grupos_ordenados.append({"letra": "#", "itens": grupos["#"]})

    context = {
        "compositores": compositores,
        "alfabeto": alfabeto,
        "grupos_compositores": grupos_ordenados,
    }
    return render(request, "obras/compositores.html", context)


def pesquisa_view(request):
    titulo = request.GET.get("titulo", "").strip()
    compositor_id = request.GET.get("compositor", "").strip()
    genero_id = request.GET.get("genero", "").strip()
    num_orgaos = request.GET.get("num_orgaos", "").strip()
    registos_raw = request.GET.get("registos", "").strip()
    apenas_registos = request.GET.get("apenas_registos") == "on"
    ano_inicio = request.GET.get("ano_inicio", "").strip()
    ano_fim = request.GET.get("ano_fim", "").strip()
    tonalidade_id = request.GET.get("tonalidade", "").strip()

    obras = (
        Obra.objects.select_related("compositor", "genero")
        .annotate(
            num_orgaos=Count("orgaos", distinct=True),
            num_registacoes=Count("orgaos__registacoes", distinct=True),
        )
        .order_by("codigo")
    )

    if titulo:
        obras = obras.filter(titulo__icontains=titulo)

    if compositor_id:
        obras = obras.filter(compositor_id=compositor_id)

    if genero_id:
        obras = obras.filter(genero_id=genero_id)

    if num_orgaos:
        try:
            obras = obras.filter(num_orgaos=int(num_orgaos))
        except ValueError:
            pass

    registos = [reg.strip().lower() for reg in registos_raw.replace(",", " ").split() if reg.strip()]

    if registos:
        if apenas_registos:
            token_registo = r"(?:" + "|".join(re.escape(reg) for reg in registos) + r")"
            padrao_registos = rf"^\s*{token_registo}(?:\s+{token_registo})*\s*$"
            padrao_vazio = r"^\s*(?:-|—)?\s*$"
            padrao_registos_ou_vazio = rf"(?:{padrao_registos})|(?:{padrao_vazio})"
            registacoes_obra = Registacao.objects.filter(orgao__obra_id=OuterRef("pk"))
            registo_permitido = (
                Q(geral__nome__iregex=padrao_registos)
                | Q(mao_esquerda__nome__iregex=padrao_registos)
                | Q(mao_direita__nome__iregex=padrao_registos)
            )
            registo_nao_permitido = (
                (Q(geral__isnull=False) & ~Q(geral__nome__iregex=padrao_registos_ou_vazio))
                | (Q(mao_esquerda__isnull=False) & ~Q(mao_esquerda__nome__iregex=padrao_registos_ou_vazio))
                | (Q(mao_direita__isnull=False) & ~Q(mao_direita__nome__iregex=padrao_registos_ou_vazio))
            )

            obras = obras.annotate(
                tem_registo_permitido=Exists(registacoes_obra.filter(registo_permitido)),
                tem_registo_nao_permitido=Exists(registacoes_obra.filter(registo_nao_permitido)),
            ).filter(
                tem_registo_permitido=True,
                tem_registo_nao_permitido=False,
            )
        else:
            for reg in registos:
                filtro_registo = (
                    Q(orgaos__registacoes__geral__nome__icontains=reg)
                    | Q(orgaos__registacoes__mao_esquerda__nome__icontains=reg)
                    | Q(orgaos__registacoes__mao_direita__nome__icontains=reg)
                )
                obras = obras.filter(filtro_registo)

        obras = obras.distinct()

    if ano_inicio:
        try:
            obras = obras.filter(ano__gte=int(ano_inicio))
        except ValueError:
            pass

    if ano_fim:
        try:
            obras = obras.filter(ano__lte=int(ano_fim))
        except ValueError:
            pass

    if tonalidade_id:
        obras = obras.filter(tonalidade_id=tonalidade_id)

    # Ordenar tonalidades por ordem cromática: Dó, Dó♯/Ré♭, Ré, Ré♯/Mi♭, Mi, Fá, Fá♯, Sol, Sol♯/Lá♭, Lá, Lá♯/Si♭, Si, Si♯
    # Depois Maior antes de Menor
    # Filtrar apenas tonalidades que têm obras associadas
    tonalidades = Tonalidade.objects.filter(obras__isnull=False).distinct().select_related("nota", "modo").annotate(
        ordem_nota=Case(
            When(nota__nome="Dó", then=Value(1)),
            When(nota__nome="Dó♯", then=Value(2)),
            When(nota__nome="Ré♭", then=Value(2)),
            When(nota__nome="Ré", then=Value(3)),
            When(nota__nome="Ré♯", then=Value(4)),
            When(nota__nome="Mi♭", then=Value(4)),
            When(nota__nome="Mi", then=Value(5)),
            When(nota__nome="Fá", then=Value(6)),
            When(nota__nome="Fá♯", then=Value(7)),
            When(nota__nome="Sol", then=Value(8)),
            When(nota__nome="Sol♯", then=Value(9)),
            When(nota__nome="Lá♭", then=Value(9)),
            When(nota__nome="Lá", then=Value(10)),
            When(nota__nome="Lá♯", then=Value(11)),
            When(nota__nome="Si♭", then=Value(11)),
            When(nota__nome="Si", then=Value(12)),
            When(nota__nome="Si♯", then=Value(13)),
            default=Value(99),
        ),
        ordem_modo=Case(
            When(modo__nome="Maior", then=Value(1)),
            When(modo__nome="Menor", then=Value(2)),
            default=Value(99),
        ),
    ).order_by("ordem_nota", "ordem_modo")

    context = {
        "compositores": Compositor.objects.all().order_by("apelido", "nome"),
        "generos": Genero.objects.all().order_by("nome"),
        "tonalidades": tonalidades,
        "obras": obras,
        "filtros": {
            "titulo": titulo,
            "compositor": compositor_id,
            "genero": genero_id,
            "num_orgaos": num_orgaos,
            "registos": registos_raw,
            "apenas_registos": apenas_registos,
            "ano_inicio": ano_inicio,
            "ano_fim": ano_fim,
            "tonalidade": tonalidade_id,
        },
    }
    return render(request, "obras/pesquisa.html", context)


def compositor_view(request, id):
    compositor = get_object_or_404(Compositor, id=id)
    context = {
        'compositor': compositor
    }
    return render(request, "obras/compositor.html", context)


@login_required(login_url="login")
def criar_compositor_view(request):
    compositor_tmp = Compositor()
    form = CompositorForm(request.POST or None)
    referencia_formset = ReferenciaFormSet(request.POST or None, instance=compositor_tmp, prefix="referencias")

    if request.method == "POST" and form.is_valid() and referencia_formset.is_valid():
        compositor = form.save()
        referencia_formset.instance = compositor
        referencia_formset.save()
        return redirect("compositor", id=compositor.id)

    context = {
        "form": form,
        "referencia_formset": referencia_formset,
        "titulo_pagina": "Criar Compositor",
        "texto_botao": "Criar compositor",
    }
    return render(request, "obras/compositor_form.html", context)


@login_required(login_url="login")
def editar_compositor_view(request, id):
    compositor = get_object_or_404(Compositor, id=id)
    form = CompositorForm(request.POST or None, instance=compositor)
    referencia_formset = ReferenciaFormSet(request.POST or None, instance=compositor, prefix="referencias")

    if request.method == "POST" and form.is_valid() and referencia_formset.is_valid():
        compositor = form.save()
        referencia_formset.save()
        return redirect("compositor", id=compositor.id)

    context = {
        "form": form,
        "referencia_formset": referencia_formset,
        "compositor": compositor,
        "titulo_pagina": "Editar Compositor",
        "texto_botao": "Guardar alterações",
    }
    return render(request, "obras/compositor_form.html", context)


def obra_view(request, id):
    obra = Obra.objects.get(id=id)
    context = {
        'obra': obra
    }
    return render(request, "obras/obra.html", context)


@login_required(login_url='login')
def editar_obra_view(request, id):
    obra = Obra.objects.get(id=id)
    
    if request.method == "POST":
        # Atualizar campos básicos
        obra.titulo = request.POST.get("titulo", "").strip()
        obra.ano = request.POST.get("ano", "").strip() or None
        obra.efectivo_vocal = request.POST.get("efectivo_vocal", "").strip()
        obra.efectivo_orgao = request.POST.get("efectivo_orgao", "").strip()
        obra.descricao_fisica = request.POST.get("descricao_fisica", "").strip()
        obra.onomastica = request.POST.get("onomastica", "").strip()
        obra.referencias = request.POST.get("referencias", "").strip()
        
        # Atualizar FKs
        compositor_id = request.POST.get("compositor", "").strip()
        if compositor_id:
            obra.compositor_id = compositor_id
        
        genero_id = request.POST.get("genero", "").strip()
        obra.genero_id = genero_id if genero_id else None
        
        tonalidade_id = request.POST.get("tonalidade", "").strip()
        obra.tonalidade_id = tonalidade_id if tonalidade_id else None
        
        obra.save()
        
        # Deletar órgãos existentes (e suas registações em cascata)
        obra.orgaos.all().delete()
        
        # Processar órgãos e registações
        orgao_counter = 0
        while True:
            orgao_counter += 1
            ext_inicio_nota = request.POST.get(f"orgao_{orgao_counter}_ext_inicio_nota", "").strip()
            ext_inicio_oitava = request.POST.get(f"orgao_{orgao_counter}_ext_inicio_oitava", "").strip()
            ext_inicio_tipo = request.POST.get(f"orgao_{orgao_counter}_ext_inicio_tipo", "").strip()
            ext_fim_nota = request.POST.get(f"orgao_{orgao_counter}_ext_fim_nota", "").strip()
            ext_fim_oitava = request.POST.get(f"orgao_{orgao_counter}_ext_fim_oitava", "").strip()
            ext_fim_tipo = request.POST.get(f"orgao_{orgao_counter}_ext_fim_tipo", "").strip()
            ordem = request.POST.get(f"orgao_{orgao_counter}_ordem", "").strip()
            
            # Se não há dados para este órgão, parar
            if not (
                ext_inicio_nota
                or ext_inicio_oitava
                or ext_fim_nota
                or ext_fim_oitava
                or ordem
            ):
                break

            ext_inicio_obj = _obter_extensao_por_componentes(ext_inicio_nota, ext_inicio_oitava, ext_inicio_tipo)
            ext_fim_obj = _obter_extensao_por_componentes(ext_fim_nota, ext_fim_oitava, ext_fim_tipo)
            
            # Criar órgão
            orgao = Orgao(
                obra=obra,
                nome=f"org{orgao_counter}",
                extensao_inicio=ext_inicio_obj,
                extensao_fim=ext_fim_obj,
                ordem=int(ordem) if ordem else orgao_counter
            )
            orgao.save()
            
            # Processar registações para este órgão
            reg_counter = 0
            while True:
                reg_counter += 1
                geral_id = request.POST.get(f"orgao_{orgao_counter}_reg_{reg_counter}_geral", "").strip()
                esquerda_id = request.POST.get(f"orgao_{orgao_counter}_reg_{reg_counter}_esquerda", "").strip()
                direita_id = request.POST.get(f"orgao_{orgao_counter}_reg_{reg_counter}_direita", "").strip()
                numero = request.POST.get(f"orgao_{orgao_counter}_reg_{reg_counter}_numero", "").strip()
                
                # Se não há dados para esta registação, parar
                if not (geral_id or esquerda_id or direita_id or numero):
                    break
                
                # Criar registação
                numero_val = int(numero) if numero else reg_counter
                registacao = Registacao(
                    orgao=orgao,
                    geral_id=geral_id if geral_id else None,
                    mao_esquerda_id=esquerda_id if esquerda_id else None,
                    mao_direita_id=direita_id if direita_id else None,
                    numero=numero_val,
                    ordem=numero_val
                )
                registacao.save()
        
        return redirect("obra", id=obra.id)
    
    # Preparar tonalidades com ordenação cromática
    tonalidades = Tonalidade.objects.select_related("nota", "modo").annotate(
        ordem_nota=Case(
            When(nota__nome="Dó", then=Value(1)),
            When(nota__nome="Dó♯", then=Value(2)),
            When(nota__nome="Ré♭", then=Value(2)),
            When(nota__nome="Ré", then=Value(3)),
            When(nota__nome="Ré♯", then=Value(4)),
            When(nota__nome="Mi♭", then=Value(4)),
            When(nota__nome="Mi", then=Value(5)),
            When(nota__nome="Fá", then=Value(6)),
            When(nota__nome="Fá♯", then=Value(7)),
            When(nota__nome="Sol", then=Value(8)),
            When(nota__nome="Sol♯", then=Value(9)),
            When(nota__nome="Lá♭", then=Value(9)),
            When(nota__nome="Lá", then=Value(10)),
            When(nota__nome="Lá♯", then=Value(11)),
            When(nota__nome="Si♭", then=Value(11)),
            When(nota__nome="Si", then=Value(12)),
            When(nota__nome="Si♯", then=Value(13)),
            default=Value(99),
        ),
        ordem_modo=Case(
            When(modo__nome="Maior", then=Value(1)),
            When(modo__nome="Menor", then=Value(2)),
            default=Value(99),
        ),
    ).order_by("ordem_nota", "ordem_modo")
    
    # Filtrar apenas as notas naturais e oitavas permitidas
    notas_permitidas = ["Dó", "Ré", "Mi", "Fá", "Sol", "Lá", "Si"]
    notas_dict = {nota.nome: {"id": nota.id, "nome": nota.nome} for nota in Nota.objects.filter(nome__in=notas_permitidas)}
    notas_list = [notas_dict[nome] for nome in notas_permitidas if nome in notas_dict]
    oitavas_list = [1, 2, 3, 4, 5, 6]
    registos_list = [{"id": reg.id, "nome": reg.nome} for reg in Registo.objects.all().order_by("nome")]
    
    # Buscar órgãos existentes da obra
    orgaos_existentes = []
    for orgao in obra.orgaos.select_related("extensao_inicio__nota", "extensao_fim__nota").all().order_by("ordem"):
        registacoes_list = []
        for reg in orgao.registacoes.all().order_by("ordem"):
            registacoes_list.append({
                "geral_id": reg.geral_id,
                "esquerda_id": reg.mao_esquerda_id,
                "direita_id": reg.mao_direita_id,
                "numero": reg.numero
            })
        
        orgaos_existentes.append({
            "ext_inicio_nota_id": orgao.extensao_inicio.nota_id if orgao.extensao_inicio else "",
            "ext_inicio_oitava": orgao.extensao_inicio.oitava if orgao.extensao_inicio else "",
            "ext_inicio_tipo": orgao.extensao_inicio.tipo if orgao.extensao_inicio else "",
            "ext_fim_nota_id": orgao.extensao_fim.nota_id if orgao.extensao_fim else "",
            "ext_fim_oitava": orgao.extensao_fim.oitava if orgao.extensao_fim else "",
            "ext_fim_tipo": orgao.extensao_fim.tipo if orgao.extensao_fim else "",
            "ordem": orgao.ordem,
            "registacoes": registacoes_list
        })
    
    context = {
        "obra": obra,
        "compositores": Compositor.objects.all().order_by("apelido", "nome"),
        "generos": Genero.objects.all().order_by("nome"),
        "tonalidades": tonalidades,
        "registos": Registo.objects.all().order_by("nome"),
        "notas_json": json.dumps(notas_list),
        "oitavas_json": json.dumps(oitavas_list),
        "registos_json": json.dumps(registos_list),
        "orgaos_json": json.dumps(orgaos_existentes),
    }
    return render(request, "obras/editar_obra.html", context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("landing")
    
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next", "landing")
            return redirect(next_url)
        else:
            context = {
                "error": "Utilizador ou palavra-chave inválidos."
            }
            return render(request, "obras/login.html", context)
    
    return render(request, "obras/login.html")


def logout_view(request):
    logout(request)
    return redirect("landing")


@login_required(login_url='login')
def criar_obra_view(request):
    if request.method == "POST":
        # Criar nova obra
        titulo = request.POST.get("titulo", "").strip()
        compositor_id = request.POST.get("compositor", "").strip()
        
        # Se compositor_id não foi selecionado, tentar criar novo compositor
        if not compositor_id:
            new_compositor_nome = request.POST.get("new_compositor_nome", "").strip()
            new_compositor_apelido = request.POST.get("new_compositor_apelido", "").strip()
            
            if new_compositor_nome and new_compositor_apelido:
                compositor = Compositor.objects.create(
                    nome=new_compositor_nome,
                    apelido=new_compositor_apelido
                )
                compositor_id = compositor.id
        
        if not titulo or not compositor_id:
            # Filtrar apenas as notas naturais e oitavas permitidas
            notas_permitidas = ["Dó", "Ré", "Mi", "Fá", "Sol", "Lá", "Si"]
            notas_dict = {nota.nome: {"id": nota.id, "nome": nota.nome} for nota in Nota.objects.filter(nome__in=notas_permitidas)}
            notas_list = [notas_dict[nome] for nome in notas_permitidas if nome in notas_dict]
            oitavas_list = [1, 2, 3, 4, 5, 6]
            registos_list = [{"id": reg.id, "nome": reg.nome} for reg in Registo.objects.all().order_by("nome")]
            
            context = {
                "compositores": Compositor.objects.all().order_by("apelido", "nome"),
                "generos": Genero.objects.all().order_by("nome"),
                "tonalidades": Tonalidade.objects.select_related("nota", "modo").annotate(
                    ordem_nota=Case(
                        When(nota__nome="Dó", then=Value(1)),
                        When(nota__nome="Dó♯", then=Value(2)),
                        When(nota__nome="Ré♭", then=Value(2)),
                        When(nota__nome="Ré", then=Value(3)),
                        When(nota__nome="Ré♯", then=Value(4)),
                        When(nota__nome="Mi♭", then=Value(4)),
                        When(nota__nome="Mi", then=Value(5)),
                        When(nota__nome="Fá", then=Value(6)),
                        When(nota__nome="Fá♯", then=Value(7)),
                        When(nota__nome="Sol", then=Value(8)),
                        When(nota__nome="Sol♯", then=Value(9)),
                        When(nota__nome="Lá♭", then=Value(9)),
                        When(nota__nome="Lá", then=Value(10)),
                        When(nota__nome="Lá♯", then=Value(11)),
                        When(nota__nome="Si♭", then=Value(11)),
                        When(nota__nome="Si", then=Value(12)),
                        When(nota__nome="Si♯", then=Value(13)),
                        default=Value(99),
                    ),
                    ordem_modo=Case(
                        When(modo__nome="Maior", then=Value(1)),
                        When(modo__nome="Menor", then=Value(2)),
                        default=Value(99),
                    ),
                ).order_by("ordem_nota", "ordem_modo"),
                "registos": Registo.objects.all().order_by("nome"),
                "notas_json": json.dumps(notas_list),
                "oitavas_json": json.dumps(oitavas_list),
                "registos_json": json.dumps(registos_list),
                "error": "Título e Compositor são obrigatórios. Selecione um compositor ou crie um novo."
            }
            return render(request, "obras/criar_obra.html", context)
        
        ano = request.POST.get("ano", "").strip() or None
        efectivo_vocal = request.POST.get("efectivo_vocal", "").strip()
        efectivo_orgao = request.POST.get("efectivo_orgao", "").strip()
        descricao_fisica = request.POST.get("descricao_fisica", "").strip()
        onomastica = request.POST.get("onomastica", "").strip()
        referencias = request.POST.get("referencias", "").strip()
        genero_id = request.POST.get("genero", "").strip() or None
        tonalidade_id = request.POST.get("tonalidade", "").strip() or None
        
        obra = Obra(
            titulo=titulo,
            compositor_id=compositor_id,
            ano=ano,
            efectivo_vocal=efectivo_vocal,
            efectivo_orgao=efectivo_orgao,
            descricao_fisica=descricao_fisica,
            onomastica=onomastica,
            referencias=referencias,
            genero_id=genero_id,
            tonalidade_id=tonalidade_id,
        )
        obra.save()
        
        # Processar órgãos e registações
        orgao_counter = 0
        while True:
            orgao_counter += 1
            ext_inicio_nota = request.POST.get(f"orgao_{orgao_counter}_ext_inicio_nota", "").strip()
            ext_inicio_oitava = request.POST.get(f"orgao_{orgao_counter}_ext_inicio_oitava", "").strip()
            ext_inicio_tipo = request.POST.get(f"orgao_{orgao_counter}_ext_inicio_tipo", "").strip()
            ext_fim_nota = request.POST.get(f"orgao_{orgao_counter}_ext_fim_nota", "").strip()
            ext_fim_oitava = request.POST.get(f"orgao_{orgao_counter}_ext_fim_oitava", "").strip()
            ext_fim_tipo = request.POST.get(f"orgao_{orgao_counter}_ext_fim_tipo", "").strip()
            ordem = request.POST.get(f"orgao_{orgao_counter}_ordem", "").strip()
            
            # Se não há dados para este órgão, parar
            if not (ext_inicio_nota or ext_fim_nota or ordem):
                break
            
            # Obter ou criar extensões
            extensao_inicio = _obter_extensao_por_componentes(ext_inicio_nota, ext_inicio_oitava, ext_inicio_tipo) if ext_inicio_nota else None
            extensao_fim = _obter_extensao_por_componentes(ext_fim_nota, ext_fim_oitava, ext_fim_tipo) if ext_fim_nota else None
            
            # Criar órgão
            orgao = Orgao(
                obra=obra,
                nome=f"org{orgao_counter}",
                extensao_inicio=extensao_inicio,
                extensao_fim=extensao_fim,
                ordem=int(ordem) if ordem else orgao_counter
            )
            orgao.save()
            
            # Processar registações para este órgão
            reg_counter = 0
            while True:
                reg_counter += 1
                geral_id = request.POST.get(f"orgao_{orgao_counter}_reg_{reg_counter}_geral", "").strip()
                esquerda_id = request.POST.get(f"orgao_{orgao_counter}_reg_{reg_counter}_esquerda", "").strip()
                direita_id = request.POST.get(f"orgao_{orgao_counter}_reg_{reg_counter}_direita", "").strip()
                numero = request.POST.get(f"orgao_{orgao_counter}_reg_{reg_counter}_numero", "").strip()
                
                # Se não há dados para esta registação, parar
                if not (geral_id or esquerda_id or direita_id or numero):
                    break
                
                # Criar registação
                numero_val = int(numero) if numero else reg_counter
                registacao = Registacao(
                    orgao=orgao,
                    geral_id=geral_id if geral_id else None,
                    mao_esquerda_id=esquerda_id if esquerda_id else None,
                    mao_direita_id=direita_id if direita_id else None,
                    numero=numero_val,
                    ordem=numero_val
                )
                registacao.save()
        
        return redirect("obra", id=obra.id)
    
    # Preparar tonalidades com ordenação cromática
    tonalidades = Tonalidade.objects.select_related("nota", "modo").annotate(
        ordem_nota=Case(
            When(nota__nome="Dó", then=Value(1)),
            When(nota__nome="Dó♯", then=Value(2)),
            When(nota__nome="Ré♭", then=Value(2)),
            When(nota__nome="Ré", then=Value(3)),
            When(nota__nome="Ré♯", then=Value(4)),
            When(nota__nome="Mi♭", then=Value(4)),
            When(nota__nome="Mi", then=Value(5)),
            When(nota__nome="Fá", then=Value(6)),
            When(nota__nome="Fá♯", then=Value(7)),
            When(nota__nome="Sol", then=Value(8)),
            When(nota__nome="Sol♯", then=Value(9)),
            When(nota__nome="Lá♭", then=Value(9)),
            When(nota__nome="Lá", then=Value(10)),
            When(nota__nome="Lá♯", then=Value(11)),
            When(nota__nome="Si♭", then=Value(11)),
            When(nota__nome="Si", then=Value(12)),
            When(nota__nome="Si♯", then=Value(13)),
            default=Value(99),
        ),
        ordem_modo=Case(
            When(modo__nome="Maior", then=Value(1)),
            When(modo__nome="Menor", then=Value(2)),
            default=Value(99),
        ),
    ).order_by("ordem_nota", "ordem_modo")
    
    # Filtrar apenas as notas naturais e oitavas permitidas
    notas_permitidas = ["Dó", "Ré", "Mi", "Fá", "Sol", "Lá", "Si"]
    notas_dict = {nota.nome: {"id": nota.id, "nome": nota.nome} for nota in Nota.objects.filter(nome__in=notas_permitidas)}
    notas_list = [notas_dict[nome] for nome in notas_permitidas if nome in notas_dict]
    oitavas_list = [1, 2, 3, 4, 5, 6]
    registos_list = [{"id": reg.id, "nome": reg.nome} for reg in Registo.objects.all().order_by("nome")]
    
    context = {
        "compositores": Compositor.objects.all().order_by("apelido", "nome"),
        "generos": Genero.objects.all().order_by("nome"),
        "tonalidades": tonalidades,
        "registos": Registo.objects.all().order_by("nome"),
        "notas_json": json.dumps(notas_list),
        "oitavas_json": json.dumps(oitavas_list),
        "registos_json": json.dumps(registos_list),
    }
    return render(request, "obras/criar_obra.html", context)


def sobre_view(request):
    return render(request, "obras/sobre.html")