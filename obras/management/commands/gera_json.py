from django.core.management.base import BaseCommand

from auxiliar.gera_json import gerar_json


class Command(BaseCommand):
    help = "Gera o ficheiro JSON consolidado a partir do Excel do catálogo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--excel-file",
            default="auxiliar/catalogo_todas_as_obras.xlsx",
            help="Caminho para o ficheiro Excel de origem.",
        )
        parser.add_argument(
            "--output",
            default="auxiliar/short.json",
            help="Caminho do ficheiro JSON a gerar.",
        )

    def handle(self, *args, **options):
        total_obras, output_path = gerar_json(
            excel_file=options["excel_file"],
            output_file=options["output"],
        )
        self.stdout.write(self.style.SUCCESS(f"JSON gerado com {total_obras} obras em {output_path}"))