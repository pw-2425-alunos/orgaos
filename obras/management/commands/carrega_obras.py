from django.core.management.base import BaseCommand

from carrega_obras import carregar_json


class Command(BaseCommand):
    help = "Carrega obras a partir do JSON consolidado para a base de dados."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ficheiro",
            default="auxiliar/short.json",
            help="Caminho para o ficheiro JSON a importar.",
        )

    def handle(self, *args, **options):
        total_obras = carregar_json(ficheiro=options["ficheiro"], stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(f"Carga terminada: {total_obras} obras processadas"))