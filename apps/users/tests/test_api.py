import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

User = get_user_model()

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def create_user(db):
    def make_user(**kwargs):
        kwargs.setdefault('password', 'senha')
        if 'email' not in kwargs:
            kwargs['email'] = 'admin@empresa.com'
        return User.objects.create_user(**kwargs)
    return make_user

@pytest.mark.django_db
class TestAuthAPI:
    def test_obtain_token_pair(self, api_client, create_user):
        create_user(email='testuser@empresa.com', password='testpassword')
        url = reverse('token_obtain_pair')
        
        response = api_client.post(url, {
            'email': 'testuser@empresa.com',
            'password': 'testpassword'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_obtain_token_pair_invalid_credentials(self, api_client, create_user):
        create_user(email='testuser@empresa.com', password='testpassword')
        url = reverse('token_obtain_pair')
        
        response = api_client.post(url, {
            'email': 'testuser@empresa.com',
            'password': 'wrongpassword'
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'access' not in response.data

    def test_refresh_token(self, api_client, create_user):
        create_user(email='testuser@empresa.com', password='testpassword')
        url_obtain = reverse('token_obtain_pair')
        
        response_obtain = api_client.post(url_obtain, {
            'email': 'testuser@empresa.com',
            'password': 'testpassword'
        }, format='json')
        
        refresh_token = response_obtain.data['refresh']
        
        url_refresh = reverse('token_refresh')
        response_refresh = api_client.post(url_refresh, {
            'refresh': refresh_token
        }, format='json')
        
        assert response_refresh.status_code == status.HTTP_200_OK
        assert 'access' in response_refresh.data


@pytest.mark.django_db
class TestCustomUserCargo:
    """Campo cargo deve existir e aceitar apenas os valores definidos."""

    def test_cargo_default_e_usuario(self, db):
        user = User.objects.create_user(password="123", email="x@x.com")
        assert user.cargo == "usuario"

    def test_cargo_aceita_choices_validos(self, db):
        for cargo in ["administrador", "financeiro", "usuario", "corretor", "produtor", "auto", "tomador"]:
            user = User.objects.create_user(
                password="123", email=f"{cargo}@x.com", cargo=cargo
            )
            assert user.cargo == cargo


# ─── Fixtures para CRUD de usuários ──────────────────────────────────────────

@pytest.fixture
def auth_client_user(db):
    from rest_framework.test import APIClient
    client = APIClient()
    User.objects.create_user(email="admin@t.com", password="admin123")
    resp = client.post(reverse("token_obtain_pair"), {"email": "admin@t.com", "password": "admin123"}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client

@pytest.fixture
def outro_usuario(db):
    return User.objects.create_user(
        email="maria@empresa.com", password="senha123",
        first_name="Maria Silva", cargo="financeiro"
    )

# ─── Testes ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUsuarioCRUDAutenticacao:
    """Endpoints de CRUD de usuários exigem token."""

    def test_listar_sem_token_retorna_401(self, client):
        from rest_framework.test import APIClient
        resp = APIClient().get(reverse("usuario-list-create"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_criar_sem_token_retorna_401(self, client):
        from rest_framework.test import APIClient
        resp = APIClient().post(reverse("usuario-list-create"), {}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUsuarioCRUD:
    """Fluxo principal do CRUD de usuários."""

    def test_listar_retorna_lista(self, auth_client_user, outro_usuario):
        resp = auth_client_user.get(reverse("usuario-list-create"))
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data["data"], list)

    def test_criar_usuario_com_senha_padrao(self, auth_client_user, db):
        resp = auth_client_user.post(
            reverse("usuario-list-create"),
            {"first_name": "João", "email": "joao@emp.com", "cargo": "corretor"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="joao@emp.com")
        assert user.check_password("123456")

    def test_criar_usuario_com_senha_personalizada(self, auth_client_user, db):
        resp = auth_client_user.post(
            reverse("usuario-list-create"),
            {"first_name": "Ana", "email": "ana@emp.com", "cargo": "usuario", "password": "minhaSenha99"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="ana@emp.com")
        assert user.check_password("minhaSenha99")

    def test_email_duplicado_retorna_400(self, auth_client_user, outro_usuario):
        resp = auth_client_user.post(
            reverse("usuario-list-create"),
            {"first_name": "Outro", "email": "maria@empresa.com", "cargo": "usuario"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_busca_por_nome(self, auth_client_user, outro_usuario, db):
        resp = auth_client_user.get(reverse("usuario-list-create"), {"search": "Maria"})
        assert resp.status_code == status.HTTP_200_OK
        nomes = [u["first_name"] for u in resp.data["data"]]
        assert any("Maria" in n for n in nomes)

    def test_patch_atualiza_cargo(self, auth_client_user, outro_usuario):
        resp = auth_client_user.patch(
            reverse("usuario-detail", args=[outro_usuario.pk]),
            {"cargo": "administrador"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["cargo"] == "administrador"
        outro_usuario.refresh_from_db()
        assert outro_usuario.cargo == "administrador"

    def test_patch_sem_senha_mantem_senha_atual(self, auth_client_user, outro_usuario):
        resp = auth_client_user.patch(
            reverse("usuario-detail", args=[outro_usuario.pk]),
            {"first_name": "Maria Atualizada"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        outro_usuario.refresh_from_db()
        assert outro_usuario.check_password("senha123")

    def test_patch_com_nova_senha_atualiza(self, auth_client_user, outro_usuario):
        resp = auth_client_user.patch(
            reverse("usuario-detail", args=[outro_usuario.pk]),
            {"password": "novaSenha99"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        outro_usuario.refresh_from_db()
        assert outro_usuario.check_password("novaSenha99")

    def test_delete_remove_usuario(self, auth_client_user, outro_usuario):
        pk = outro_usuario.pk
        resp = auth_client_user.delete(reverse("usuario-detail", args=[pk]))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(pk=pk).exists()

    def test_detalhe_inexistente_retorna_404(self, auth_client_user, db):
        resp = auth_client_user.get(reverse("usuario-detail", args=[99999]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestEmailObrigatorioEUnico:
    def test_criar_usuario_sem_email_retorna_400(self, auth_client_user):
        resp = auth_client_user.post(
            reverse("usuario-list-create"),
            {"first_name": "Sem Email", "cargo": "usuario"},
            format="json",
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in resp.data

    def test_criar_usuario_com_email_duplicado_retorna_400(self, auth_client_user, outro_usuario):
        resp = auth_client_user.post(
            reverse("usuario-list-create"),
            {"first_name": "Outro", "email": "maria@empresa.com", "cargo": "usuario"},
            format="json",
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in resp.data

    def test_editar_mantendo_o_proprio_email_funciona(self, auth_client_user, outro_usuario):
        resp = auth_client_user.patch(
            reverse("usuario-detail", args=[outro_usuario.pk]),
            {"first_name": "Maria Silva", "email": "maria@empresa.com"},
            format="json",
        )

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["first_name"] == "Maria Silva"
