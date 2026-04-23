from django.core.management.base import BaseCommand
from django.db.models import Case, When, Value, IntegerField
from obras.models import Obra, Compositor
from collections import defaultdict

class Command(BaseCommand):
    help = "Recalcula e atualiza o código de todas as obras"

    def handle(self, *args, **kwargs):

        # --- ranking dos compositores (XX) ---
        compositores = list(
            Compositor.objects
            .order_by('apelido', 'nome')
            .values_list('id', flat=True)
        )

        compositor_rank = {
            cid: idx + 1
            for idx, cid in enumerate(compositores)
        }

        # --- ordenação das obras (YY) ---
        obras = list(
            Obra.objects
            .annotate(
                tipo_ordem=Case(
                    When(genero__nome__iexact="Missa", then=Value(1)),
                    When(genero__nome__iexact="Vesperas", then=Value(2)),
                    When(genero__nome__iexact="Salmos", then=Value(3)),
                    default=Value(4),
                    output_field=IntegerField()
                )
            )
            .order_by('compositor_id', 'tipo_ordem', 'titulo')
        )

        # --- atualizar códigos ---
        contador_por_compositor = defaultdict(int)

        updates = []

        for obra in obras:

            xx = compositor_rank.get(obra.compositor_id)
            if xx is None:
                continue

            contador_por_compositor[obra.compositor_id] += 1
            yy = contador_por_compositor[obra.compositor_id]

            obra.codigo = f"{xx:02d}-{yy:02d}"
            updates.append(obra)

        Obra.objects.bulk_update(updates, ['codigo'])

        self.stdout.write(
            self.style.SUCCESS(f"{len(updates)} códigos atualizados")
        )