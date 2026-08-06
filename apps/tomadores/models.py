from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
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

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="tomadores_criados",
        null=True,
        blank=True,
        help_text="Usuário que cadastrou o tomador. Nulo para registros anteriores ao campo.",
    )

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


class TomadorArquivo(models.Model):
    tomador = models.ForeignKey(
        Tomador,
        on_delete=models.CASCADE,
        related_name="arquivos",
    )
    arquivo = models.FileField(upload_to="tomadores/arquivos/%Y/%m/")
    nome_original = models.CharField(max_length=255, blank=True, default="")
    tamanho = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tomadores_arquivos"
        ordering = ["-criado_em"]
        verbose_name = "Arquivo do Tomador"
        verbose_name_plural = "Arquivos do Tomador"

    def __str__(self):
        return f"{self.nome_original} — {self.tomador.nome}"


class TomadorSeguradora(models.Model):
    """Condições comerciais de um tomador em uma seguradora.

    Cada seguradora analisa o CNPJ do tomador e chega a uma taxa própria, então
    o mesmo tomador tem condições diferentes em cada uma. A taxa é o interruptor:
    zero deixa a seguradora fora das cotações, qualquer valor positivo habilita.

    `premio_minimo` e `dias_vencimento` em branco herdam o valor da seguradora —
    são política comercial dela, não avaliação de risco do tomador.
    """

    class Status(models.TextChoices):
        CADASTRO_OK = "cadastro_ok", "Cadastro OK"
        SEM_CADASTRO = "sem_cadastro", "Sem cadastro"
        OUTRO_CORRETOR = "outro_corretor", "Outro corretor"
        SEM_ACEITACAO = "sem_aceitacao", "Sem aceitação"

    tomador = models.ForeignKey(
        Tomador,
        on_delete=models.CASCADE,
        related_name="seguradoras",
    )
    seguradora = models.ForeignKey(
        "seguradoras.Seguradora",
        on_delete=models.PROTECT,
        related_name="tomadores",
    )

    taxa = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Zero deixa a seguradora fora das cotações deste tomador.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SEM_CADASTRO,
    )
    premio_minimo = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Em branco usa o prêmio mínimo da seguradora.",
    )
    dias_vencimento = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Em branco usa o dia de vencimento da seguradora.",
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tomadores_seguradoras"
        ordering = ["seguradora__nome"]
        verbose_name = "Seguradora do Tomador"
        verbose_name_plural = "Seguradoras do Tomador"
        constraints = [
            models.UniqueConstraint(
                fields=["tomador", "seguradora"],
                name="uniq_tomador_seguradora",
            )
        ]

    def __str__(self):
        return f"{self.tomador.nome} — {self.seguradora.nome}: {self.taxa}%"

    @property
    def apto(self) -> bool:
        """Se este par pode ser usado em cotações."""
        # Decimal() porque a instância pode carregar a taxa como str antes de
        # passar pelo banco (ex.: objects.create(taxa="1.50")).
        return Decimal(self.taxa) > 0 and self.status == self.Status.CADASTRO_OK

    @property
    def premio_minimo_efetivo(self):
        """Piso a aplicar: o do par, ou o da seguradora quando não definido."""
        if self.premio_minimo is not None:
            return self.premio_minimo
        return self.seguradora.premio_minimo

    @property
    def dias_vencimento_efetivo(self):
        """Vencimento a aplicar: o do par, ou o da seguradora quando não definido."""
        if self.dias_vencimento is not None:
            return self.dias_vencimento
        return self.seguradora.vencimento_dias


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
