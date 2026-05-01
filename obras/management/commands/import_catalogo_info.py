import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup, NavigableString, Tag
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from obras.models import Obra

CODE_PATTERN = re.compile(r"\b\d{2}-\d{2}\b")

def normalizar_codigo(valor):
    texto = str(valor or "").strip()
    texto = texto.replace("–", "-").replace("—", "-")
    texto = re.sub(r"\s+", "", texto)
    return texto.upper()

def extrair_codigos(texto):
    texto_normalizado = str(texto or "").replace("–", "-").replace("—", "-")
    return [normalizar_codigo(match) for match in CODE_PATTERN.findall(texto_normalizado)]

def iterar_blocos(body):
    for child in body.children:
        if isinstance(child, NavigableString):
            if child.strip():
                yield child
            continue
        if isinstance(child, Tag):
            yield child

def limpar_fragmento_html(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    for tag in soup.find_all(True):
        if tag.attrs:
            tag.attrs = {
                chave: valor
                for chave, valor in tag.attrs.items()
                if chave in {"href", "src", "alt", "title"}
            }

    fragmento = "".join(str(node) for node in soup.contents).strip()
    return fragmento

def construir_url_media(media_url, media_subdir, ficheiro_subdir, relativo):
    media_url_base = (media_url or "/media/").rstrip("/")
    partes = [media_url_base, media_subdir.strip("/"), ficheiro_subdir.strip("/"), relativo.as_posix().lstrip("/")]
    return "/".join(parte for parte in partes if parte)

def reescrever_referencias_media(html, origem_media_dir, media_url, media_subdir, ficheiro_subdir):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(True):
        for atributo in ("src", "href"):
            valor = tag.get(atributo)
            if not valor:
                continue

            parsed = urlparse(valor)
            if parsed.scheme in {"http", "https", "data"}:
                continue

            caminho = parsed.path
            if not caminho:
                continue

            path_obj = Path(caminho)
            if not path_obj.is_absolute():
                path_obj = (origem_media_dir / path_obj).resolve()

            try:
                relativo = path_obj.relative_to(origem_media_dir)
            except ValueError:
                continue

            tag[atributo] = construir_url_media(media_url, media_subdir, ficheiro_subdir, relativo)

    return str(soup)

def dividir_html_por_codigo(html):
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup
    secoes = defaultdict(list)
    codigo_atual = None

    for bloco in iterar_blocos(body):
        texto = bloco.get_text(" ", strip=True) if isinstance(bloco, Tag) else str(bloco).strip()
        codigos = extrair_codigos(texto)

        if codigos:
            codigo_atual = codigos[0]

        if codigo_atual is None:
            continue

        secoes[codigo_atual].append(str(bloco))

    return {
        codigo: limpar_fragmento_html("".join(fragmentos))
        for codigo, fragmentos in secoes.items()
        if limpar_fragmento_html("".join(fragmentos))
    }

class Command(BaseCommand):
    help = "Importa para info_catalogo o HTML extraído dos DOCX em auxiliar/catalogo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-dir",
            default="auxiliar/catalogo",
            help="Diretório com os ficheiros DOCX do catálogo.",
        )
        parser.add_argument(
            "--pandoc-bin",
            default="pandoc",
            help="Executável do pandoc a usar.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Limpa info_catalogo antes de importar.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Processa os ficheiros mas não grava alterações na base de dados.",
        )
        parser.add_argument(
            "--media-subdir",
            default="catalogo",
            help="Subdiretório dentro de MEDIA_ROOT para guardar imagens extraídas.",
        )
        parser.add_argument(
            "--image-width",
            type=int,
            default=800,
            help="Largura máxima (px) para otimizar as imagens extraídas; usa 0 para desativar.",
        )

    def handle(self, *args, **options):
        source_dir = Path(options["source_dir"])
        pandoc_bin = options["pandoc_bin"]
        dry_run = options["dry_run"]
        media_subdir = options["media_subdir"]
        image_width = options["image_width"]

        if not source_dir.is_absolute():
            source_dir = Path(settings.BASE_DIR) / source_dir

        if not source_dir.exists():
            raise CommandError(f"Diretório não encontrado: {source_dir}")

        pandoc_path = shutil.which(pandoc_bin) if not Path(pandoc_bin).is_absolute() else pandoc_bin
        if not pandoc_path:
            raise CommandError(f"Executável pandoc não encontrado: {pandoc_bin}")

        docx_files = sorted(source_dir.glob("*.docx"))
        if not docx_files:
            raise CommandError(f"Não existem ficheiros DOCX em {source_dir}")

        obras_por_codigo = {}
        for obra in Obra.objects.all().only("id", "codigo", "obm"):
            for candidato in [obra.codigo, obra.obm]:
                codigo = normalizar_codigo(candidato)
                if codigo:
                    obras_por_codigo[codigo] = obra.id

        if not obras_por_codigo:
            raise CommandError("Nenhuma obra com codigo ou obm preenchido foi encontrada.")

        updates = {}
        codigos_sem_obra = set()

        for docx_file in docx_files:
            self.stdout.write(f"A processar {docx_file.name}...")
            secoes = self._processar_docx(
                docx_file=docx_file,
                pandoc_bin=pandoc_path,
                media_subdir=media_subdir,
                dry_run=dry_run,
            )

            if not secoes:
                self.stdout.write(self.style.WARNING(f"Sem secções reconhecidas em {docx_file.name}"))
                continue

            for codigo, html in secoes.items():
                obra_id = obras_por_codigo.get(codigo)
                if obra_id is None:
                    codigos_sem_obra.add(codigo)
                    continue
                updates[obra_id] = html

        if options["clear"] and not dry_run:
            Obra.objects.update(info_catalogo="")

        if not dry_run and updates:
            with transaction.atomic():
                obras = list(Obra.objects.filter(id__in=updates.keys()))
                for obra in obras:
                    obra.info_catalogo = updates[obra.id]
                Obra.objects.bulk_update(obras, ["info_catalogo"])

        if not dry_run and image_width > 0:
            self.stdout.write("A otimizar imagens do catálogo...")
            call_command("optimize_catalog_images", source_dir=media_subdir, width=image_width)

        self.stdout.write(self.style.SUCCESS(f"Secções preparadas: {len(updates)}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: nenhuma alteração foi gravada."))
        if codigos_sem_obra:
            self.stdout.write(
                self.style.WARNING(
                    "Códigos sem obra correspondente: " + ", ".join(sorted(codigos_sem_obra))
                )
            )

    def _processar_docx(self, docx_file, pandoc_bin, media_subdir, dry_run):
        with tempfile.TemporaryDirectory(prefix="catalogo_") as temp_dir:
            temp_path = Path(temp_dir)
            docx_limpo = temp_path / f"{docx_file.stem}_limpo.docx"
            html_path = temp_path / f"{docx_file.stem}.html"
            imagens_dir = temp_path / "imagens"
            ficheiro_subdir = slugify(docx_file.stem) or docx_file.stem.lower().replace(" ", "-")

            script_path = Path(settings.BASE_DIR) / "auxiliar" / "limpa_headers_word.py"
            subprocess.run(
                [sys.executable, str(script_path), str(docx_file), str(docx_limpo)],
                check=True,
                cwd=settings.BASE_DIR,
            )
            subprocess.run(
                [
                    pandoc_bin,
                    str(docx_limpo),
                    "-o",
                    str(html_path),
                    f"--extract-media={imagens_dir}",
                ],
                check=True,
                cwd=settings.BASE_DIR,
            )

            html = html_path.read_text(encoding="utf-8")
            if imagens_dir.exists():
                if not dry_run:
                    destino_media = Path(settings.MEDIA_ROOT) / media_subdir / ficheiro_subdir
                    if destino_media.exists():
                        shutil.rmtree(destino_media)
                    shutil.copytree(imagens_dir, destino_media)

                html = reescrever_referencias_media(
                    html=html,
                    origem_media_dir=imagens_dir,
                    media_url=settings.MEDIA_URL,
                    media_subdir=media_subdir,
                    ficheiro_subdir=ficheiro_subdir,
                )

            return dividir_html_por_codigo(html)