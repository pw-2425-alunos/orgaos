import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageOps, UnidentifiedImageError


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def format_mb(value):
    return f"{value / (1024 * 1024):.2f} MB"


def save_optimized_image(img, path, extension, quality):
    if extension in {".jpg", ".jpeg"}:
        work = img.convert("RGB")
        work.save(path, format="JPEG", quality=quality, optimize=True, progressive=True)
        return

    if extension == ".png":
        if img.mode not in {"P", "L", "LA", "RGBA"}:
            work = img.convert("RGB").quantize(colors=256)
        else:
            work = img
        work.save(path, format="PNG", optimize=True, compress_level=9)
        return

    if extension == ".webp":
        work = img.convert("RGB") if img.mode not in {"RGB", "RGBA"} else img
        work.save(path, format="WEBP", quality=quality, method=6)
        return

    raise ValueError(f"Extensão não suportada: {extension}")


def optimize_image_copy(source_path, destination_path, width, quality):
    extension = source_path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Extensão não suportada: {extension}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source_path) as img:
        img = ImageOps.exif_transpose(img)

        resized = False
        if img.width > width:
            new_height = max(1, int(round(img.height * (width / img.width))))
            img = img.resize((width, new_height), Image.Resampling.LANCZOS)
            resized = True

        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            save_optimized_image(img=img, path=temp_path, extension=extension, quality=quality)
            optimized_size = temp_path.stat().st_size
            original_size = source_path.stat().st_size
            should_use_optimized = resized or optimized_size < original_size

            if should_use_optimized:
                shutil.move(str(temp_path), str(destination_path))
                return resized, optimized_size, True

            shutil.copy2(source_path, destination_path)
            return resized, destination_path.stat().st_size, False
        finally:
            if temp_path.exists():
                temp_path.unlink()


def copytree_optimized(source_dir, destination_dir, width, quality):
    if destination_dir.exists():
        shutil.rmtree(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)

    for path in source_dir.rglob("*"):
        relative_path = path.relative_to(source_dir)
        destination_path = destination_dir / relative_path

        if path.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            continue

        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            optimize_image_copy(path, destination_path, width=width, quality=quality)
            continue

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination_path)


class Command(BaseCommand):
    help = "Redimensiona e otimiza imagens extraídas do catálogo para uso web."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-dir",
            default="catalogo",
            help="Subdiretório dentro de MEDIA_ROOT com as imagens a otimizar.",
        )
        parser.add_argument(
            "--width",
            type=int,
            default=400,
            help="Largura máxima das imagens em pixels (mantém proporção).",
        )
        parser.add_argument(
            "--quality",
            type=int,
            default=82,
            help="Qualidade JPEG/WEBP (1-100).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula as alterações sem gravar ficheiros.",
        )

    def handle(self, *args, **options):
        width = options["width"]
        quality = options["quality"]
        dry_run = options["dry_run"]

        if width <= 0:
            raise CommandError("--width deve ser um inteiro positivo.")

        if quality < 1 or quality > 100:
            raise CommandError("--quality deve estar entre 1 e 100.")

        source_dir = Path(settings.MEDIA_ROOT) / options["source_dir"]
        if not source_dir.exists():
            raise CommandError(f"Diretório não encontrado: {source_dir}")

        image_files = [
            path for path in source_dir.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        if not image_files:
            raise CommandError(f"Nenhuma imagem suportada encontrada em {source_dir}")

        processed = 0
        resized = 0
        optimized = 0
        skipped = 0
        errors = 0
        total_before = 0
        total_after = 0

        for image_path in image_files:
            original_size = image_path.stat().st_size
            total_before += original_size

            try:
                did_resize, new_size, changed = self._optimize_image(
                    image_path=image_path,
                    width=width,
                    quality=quality,
                    dry_run=dry_run,
                )
            except (UnidentifiedImageError, OSError, ValueError) as exc:
                errors += 1
                total_after += original_size
                self.stdout.write(self.style.WARNING(f"Erro em {image_path}: {exc}"))
                continue

            processed += 1
            total_after += new_size

            if not changed:
                skipped += 1
                continue

            optimized += 1
            if did_resize:
                resized += 1

        reduction = total_before - total_after
        reduction_pct = (reduction / total_before * 100) if total_before else 0.0

        self.stdout.write(self.style.SUCCESS(f"Imagens analisadas: {len(image_files)}"))
        self.stdout.write(self.style.SUCCESS(f"Imagens processadas: {processed}"))
        self.stdout.write(self.style.SUCCESS(f"Imagens otimizadas: {optimized}"))
        self.stdout.write(self.style.SUCCESS(f"Imagens redimensionadas: {resized}"))
        self.stdout.write(self.style.SUCCESS(f"Imagens sem alteração: {skipped}"))
        self.stdout.write(self.style.SUCCESS(f"Erros: {errors}"))
        self.stdout.write(self.style.SUCCESS(f"Tamanho antes: {format_mb(total_before)}"))
        self.stdout.write(self.style.SUCCESS(f"Tamanho depois: {format_mb(total_after)}"))
        self.stdout.write(self.style.SUCCESS(f"Redução: {format_mb(reduction)} ({reduction_pct:.1f}%)"))

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: nenhuma imagem foi alterada."))

    def _optimize_image(self, image_path, width, quality, dry_run):
        extension = image_path.suffix.lower()

        with Image.open(image_path) as img:
            img = ImageOps.exif_transpose(img)

            resized = False
            if img.width > width:
                new_height = max(1, int(round(img.height * (width / img.width))))
                img = img.resize((width, new_height), Image.Resampling.LANCZOS)
                resized = True

            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
                temp_path = Path(temp_file.name)

            try:
                save_optimized_image(img=img, path=temp_path, extension=extension, quality=quality)
                new_size = temp_path.stat().st_size

                original_size = image_path.stat().st_size
                should_replace = resized or new_size < original_size

                if should_replace and not dry_run:
                    shutil.move(str(temp_path), str(image_path))
                return resized, (new_size if should_replace else original_size), should_replace
            finally:
                if temp_path.exists():
                    temp_path.unlink()