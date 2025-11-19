from rest_framework import routers
from django.urls import path

from .views import (
    CurrentEmployeeView,
    DepartmentViewSet,
    EmployeeViewSet,
    ImprovementProposalViewSet,
    LoginView,
    LogoutView,
)

router = routers.DefaultRouter()
router.register(r"departments", DepartmentViewSet)
router.register(r"employees", EmployeeViewSet)
router.register(r"improvement-proposals", ImprovementProposalViewSet, basename="improvement-proposals")

urlpatterns = router.urls + [
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path("employees/me/", CurrentEmployeeView.as_view(), name="employees-me"),
]
