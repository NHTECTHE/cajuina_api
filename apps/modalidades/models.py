from django.db import models


class ModalidadeNaoMapeada(Exception):
    """Não há código cadastrado para a modalidade naquela seguradora.

    O sistema antigo, nesse caso, mandava o ID interno da Cajuína no lugar
    (`modalidade_helper.php`) e torcia para coincidir com o catálogo da
    seguradora. Quando não coincidia, a cotação saía na modalidade errada sem
    ninguém perceber. Aqui a falta de mapeamento é erro explícito.
    """

    def __init__(self, modalidade, seguradora):
        self.modalidade = modalidade
        self.seguradora = seguradora
        super().__init__(
            f"Modalidade '{modalidade}' não está mapeada na seguradora '{seguradora}'."
        )


class Modalidade(models.Model):
    nome = models.CharField(max_length=255)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "modalidades"
        ordering = ["nome"]
        verbose_name = "Modalidade"
        verbose_name_plural = "Modalidades"

    def __str__(self):
        return self.nome


class ModalidadeSeguradora(models.Model):
    """Código que uma seguradora usa para identificar esta modalidade.

    Cada seguradora mantém o próprio catálogo: a mesma "Garantia de Execução de
    Contrato" pode ser 3 numa e 17 noutra. O ID interno da Cajuína não serve
    para conversar com a API de ninguém, então o par precisa ser traduzido.

    A ausência da linha é o que marca "esta seguradora não oferece esta
    modalidade" — não existe valor neutro para um código externo.
    """

    modalidade = models.ForeignKey(
        Modalidade,
        on_delete=models.CASCADE,
        related_name="seguradoras",
    )
    seguradora = models.ForeignKey(
        "seguradoras.Seguradora",
        on_delete=models.CASCADE,
        related_name="modalidades",
    )

    codigo_seguradora = models.CharField(
        max_length=50,
        help_text="Código da modalidade no catálogo da seguradora.",
    )
    ativo = models.BooleanField(
        default=True,
        help_text="Desmarcado suspende o mapeamento sem perder o código.",
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "modalidade_seguradoras"
        ordering = ["seguradora__nome"]
        verbose_name = "Modalidade da Seguradora"
        verbose_name_plural = "Modalidades da Seguradora"
        constraints = [
            models.UniqueConstraint(
                fields=["modalidade", "seguradora"],
                name="uniq_modalidade_seguradora",
            )
        ]

    def __str__(self):
        return f"{self.modalidade.nome} — {self.seguradora.nome}: {self.codigo_seguradora}"
