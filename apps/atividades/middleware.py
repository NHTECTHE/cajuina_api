import threading
from rest_framework_simplejwt.authentication import JWTAuthentication

_thread_locals = threading.local()

def get_current_user():
    return getattr(_thread_locals, 'user', None)

class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = None
        if request.user and request.user.is_authenticated:
            user = request.user
        else:
            try:
                authenticator = JWTAuthentication()
                res = authenticator.authenticate(request)
                if res is not None:
                    user = res[0]
            except Exception:
                pass
        
        _thread_locals.user = user
        try:
            response = self.get_response(request)
        finally:
            if hasattr(_thread_locals, 'user'):
                del _thread_locals.user
        return response
