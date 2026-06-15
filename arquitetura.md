```txt id="j1jqm0"
backend/
  manage.py
  pyproject.toml
  Dockerfile
  docker-compose.yml
  .env.example

  config/
    __init__.py
    urls.py
    asgi.py
    wsgi.py
    celery.py

    settings/
      __init__.py
      base.py
      local.py
      production.py

  apps/
    <app_name>/
      __init__.py
      admin.py
      apps.py
      models.py
      services.py
      selectors.py
      permissions.py
      tasks.py

      api/
        __init__.py
        v1/
          __init__.py
          serializers.py
          views.py
          urls.py
          filters.py

      migrations/
        __init__.py

      tests/
        __init__.py
        test_models.py
        test_services.py
        test_api.py

  shared/
    __init__.py
    models.py
    envelope.py
    responses.py
    exceptions.py
    pagination.py
    permissions.py
    validators.py
    utils.py
```
