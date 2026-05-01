import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from obras.models import Obra


OBM_HEADER_PATTERN = re.compile(r"^\s*(\d{2}-\d{2})\b", re.MULTILINE)


def normalizar_codigo(valor):
    texto = str(valor or "").strip()
    texto = texto.replace("–", "-").replace("—", "-")
    texto = re.sub(r"\s+", "", texto)
    return texto.upper()


def extrair_obms_do_texto(texto):
    return {normalizar_codigo(match) for match in OBM_HEADER_PATTERN.findall(texto or "")}


class Command(BaseCommand):
    help = "Extrai OBM dos DOCX em auxiliar/catalogo e preenche Obra.obm pela chave Obra.codigo."

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
            "--dry-run",
            action="store_true",
            help="Processa e mostra resultados sem gravar alterações na base de dados.",
        )

    def handle(self, *args, **options):
        source_dir = Path(options["source_dir"])
        pandoc_bin = options["pandoc_bin"]
        dry_run = options["dry_run"]

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

        obms_extraidos = set()
        for docx_file in docx_files:
            self.stdout.write(f"A processar {docx_file.name}...")
            obms_extraidos.update(self._processar_docx(docx_file, pandoc_path))

        if not obms_extraidos:
            raise CommandError("Nenhum OBM foi extraído dos DOCX.")

        obras_por_codigo = defaultdict(list)
        for obra in Obra.objects.all().only("id", "codigo"):
            codigo = normalizar_codigo(obra.codigo)
            if codigo:
                obras_por_codigo[codigo].append(obra.id)

        updates = {}
        codigos_sem_obra = set()

        for obm in sorted(obms_extraidos):
            obra_ids = obras_por_codigo.get(obm)
            if not obra_ids:
                codigos_sem_obra.add(obm)
                continue

            for obra_id in obra_ids:
                updates[obra_id] = obm

        if not dry_run and updates:
            with transaction.atomic():
                obras = list(Obra.objects.filter(id__in=updates.keys()))
                for obra in obras:
                    obra.obm = updates[obra.id]
                Obra.objects.bulk_update(obras, ["obm"])

        self.stdout.write(self.style.SUCCESS(f"OBM extraídos: {len(obms_extraidos)}"))
        self.stdout.write(self.style.SUCCESS(f"Obras com OBM preparado: {len(updates)}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: nenhuma alteração foi gravada."))

        if codigos_sem_obra:
            self.stdout.write(
                self.style.WARNING(
                    "OBM sem obra correspondente por codigo: " + ", ".join(sorted(codigos_sem_obra))
                )
            )

    def _processar_docx(self, docx_file, pandoc_bin):
        with tempfile.TemporaryDirectory(prefix="obm_catalogo_") as temp_dir:
            temp_path = Path(temp_dir)
            docx_limpo = temp_path / f"{docx_file.stem}_limpo.docx"
            txt_path = temp_path / f"{docx_file.stem}.txt"

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
                    "-t",
                    "plain",
                    "-o",
                    str(txt_path),
                ],
                check=True,
                cwd=settings.BASE_DIR,
            )

            texto = txt_path.read_text(encoding="utf-8")
            return extrair_obms_do_texto(texto)