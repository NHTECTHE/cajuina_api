from django.db import models

class Tomador(models.Model):
    cnpj = models.CharField(max_length=25, unique=True)
    nome = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255, blank=True, null=True)
    produtor = models.CharField(max_length=255, blank=True, null=True)
    corretora = models.CharField(max_length=255, blank=True, null=True)
    
    # Endereco
    cep = models.CharField(max_length=10, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=20, blank=True, null=True)
    complemento = models.CharField(max_length=255, blank=True, null=True)
    bairro = models.CharField(max_length=255, blank=True, null=True)
    cidade = models.CharField(max_length=255, blank=True, null=True)
    uf = models.CharField(max_length=2, blank=True, null=True)
    
    # Contatos principais
    contato = models.CharField(max_length=255, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    celular = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    habilitar_email = models.BooleanField(default=False)
    
    # Outros
    observacoes = models.TextField(blank=True, null=True)
    ativar_cotacao = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nome} ({self.cnpj})"

class Socio(models.Model):
    tomador = models.ForeignKey(Tomador, related_name='socios', on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.nome

class ContatoAdicional(models.Model):
    tomador = models.ForeignKey(Tomador, related_name='contatos', on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    cargo = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nome
