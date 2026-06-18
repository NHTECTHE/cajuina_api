from django.db import models


class Tomador(models.Model):
    # Identificação
    cnpj = models.CharField(max_length=18, unique=True)
    nome = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255, blank=True, default="")

    # Vínculo
    produtor = models.CharField(max_length=100, default="CAJUINA SEGUROS")
    corretora = models.CharField(max_length=100, default="CAJUINA")

    # Contato principal
    contato = models.CharField(max_length=100, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    habilitar_email = models.BooleanField(default=False)
    telefone = models.CharField(max_length=20, blank=True, default="")
    celular = models.CharField(max_length=20, blank=True, default="")

    # Endereço
    cep = models.CharField(max_length=10, blank=True, default="")
    endereco = models.CharField(max_length=255, blank=True, default="")
    numero = models.CharField(max_length=20, blank=True, default="")
    complemento = models.CharField(max_length=100, blank=True, default="")
    bairro = models.CharField(max_length=100, blank=True, default="")
    cidade = models.CharField(max_length=100, blank=True, default="")
    uf = models.CharField(max_length=2, blank=True, default="")

    # Configurações
    ativar_cotacao = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True, default="")

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tomadores"
        ordering = ["nome"]
        verbose_name = "Tomador"
        verbose_name_plural = "Tomadores"

    def __str__(self):
        return f"{self.nome} ({self.cnpj})"


class ContatoAdicional(models.Model):
    tomador = models.ForeignKey(
        Tomador,
        on_delete=models.CASCADE,
        related_name="contatos_adicionais",
    )
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")

    class Meta:
        db_table = "tomadores_contatos"
        verbose_name = "Contato Adicional"
        verbose_name_plural = "Contatos Adicionais"

    def __str__(self):
        return f"{self.nome} — {self.tomador.nome}"


class Socio(models.Model):
    QUALIFICACAO_CHOICES = [
        ("Sócio Administrador", "Sócio Administrador"),
        ("Diretor", "Diretor"),
        ("Sócio", "Sócio"),
        ("Administrador", "Administrador"),
        ("Procurador", "Procurador"),
    ]

    tomador = models.ForeignKey(
        Tomador,
        on_delete=models.CASCADE,
        related_name="socios",
    )
    nome = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, blank=True, default="")
    nascimento = models.DateField(null=True, blank=True)
    qualificacao = models.CharField(
        max_length=50,
        choices=QUALIFICACAO_CHOICES,
        blank=True,
        default="",
    )

    class Meta:
        db_table = "tomadores_socios"
        verbose_name = "Sócio"
        verbose_name_plural = "Sócios"

    def __str__(self):
        return f"{self.nome} — {self.tomador.nome}"
