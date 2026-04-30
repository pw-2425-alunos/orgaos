from django.db import models

class Compositor(models.Model):
    nome = models.CharField(max_length=100)
    apelido = models.CharField(max_length=100)
    nascimento = models.CharField(max_length=30, blank=True, null=True, default="")
    nascimento_c = models.BooleanField(blank=True, null=True, default=False)
    morte = models.CharField(max_length=30, blank=True, null=True, default="")
    morte_c = models.BooleanField(blank=True, null=True, default=False)
    a = models.CharField(max_length=30, blank=True, null=True, default="")
    d = models.CharField(max_length=30, blank=True, null=True, default="")
    fl = models.CharField(max_length=30, blank=True, null=True, default="")
    
    def __str__(self):
        return self.apelido + ', ' + self.nome


class Referencia(models.Model):
    nome = models.CharField(max_length=100, null=True, blank=True)
    url = models.URLField(blank=True)
    compositor = models.ForeignKey(Compositor, on_delete=models.CASCADE, related_name="referencias", null=True, blank=True)

    def __str__(self):
        return f"{self.nome} ({self.url})"


class Genero(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome



class Nota(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome
    

class Modo(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


class Tonalidade(models.Model):
    nota = models.ForeignKey(Nota, on_delete=models.CASCADE, related_name="tonalidades")
    modo = models.ForeignKey(Modo, on_delete=models.CASCADE, related_name="tonalidades", null=True, blank=True)
    def __str__(self):
        return f"{self.nota} {self.modo}"


class Obra(models.Model):
    obm = models.CharField(max_length=20, default="")
    titulo = models.CharField(max_length=100)
    compositor = models.ForeignKey(Compositor, related_name="obras", on_delete=models.CASCADE)
    ano = models.PositiveIntegerField(null=True, blank=True)
    efectivo_vocal = models.CharField(max_length=255, blank=True)
    efectivo_orgao = models.CharField(max_length=50, blank=True)
    tonalidade = models.ForeignKey(Tonalidade, on_delete=models.CASCADE, related_name="obras", null=True, blank=True)
    genero = models.ForeignKey(Genero, related_name="obras", on_delete=models.CASCADE, null=True, blank=True)
    descricao_fisica = models.TextField(blank=True)
    onomastica = models.TextField(blank=True)
    referencias = models.TextField(blank=True)
    observacoes = models.TextField(blank=True, default="")
    codigo = models.CharField(max_length=50, blank=True, default="")

    def __str__(self):
        return f"{self.titulo} ({self.compositor})"

   

class Extensao(models.Model):
    nota = models.ForeignKey(Nota, on_delete=models.CASCADE, related_name="extensoes")
    oitava = models.IntegerField()
    tipo = models.CharField(max_length=2, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["nota", "oitava", "tipo"], name="unique_extensao")
        ]

    def __str__(self):
        return f"{self.nota}{self.oitava}{self.tipo}"
    

class Orgao(models.Model):
    nome = models.CharField(max_length=2)
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="orgaos")
    extensao_inicio = models.ForeignKey(Extensao, on_delete=models.CASCADE, related_name="orgaos_inicio", null=True, blank=True)
    extensao_fim = models.ForeignKey(Extensao, on_delete=models.CASCADE, related_name="orgaos_fim", null=True, blank=True)
    ordem = models.IntegerField()

    class Meta:
        ordering = ["ordem"]

    def __str__(self):
        return self.nome


class Registo(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome
    
class Registacao(models.Model):
    orgao = models.ForeignKey(Orgao, on_delete=models.CASCADE, related_name="registacoes")
    geral = models.ForeignKey(Registo, on_delete=models.CASCADE, related_name="registacoes_geral", null=True, blank=True)
    mao_esquerda = models.ForeignKey(Registo, on_delete=models.CASCADE, related_name="registacoes_esquerda", null=True, blank=True)
    mao_direita = models.ForeignKey(Registo, on_delete=models.CASCADE, related_name="registacoes_direita", null=True, blank=True)
    numero = models.IntegerField()
    ordem = models.IntegerField()

    class Meta:
        ordering = ["ordem"]
