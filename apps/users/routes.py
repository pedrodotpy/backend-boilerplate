from apps.users.api.views import UserViewSet

routes = [
    {"regex": r"users", "viewset": UserViewSet, "basename": "user"},
]
