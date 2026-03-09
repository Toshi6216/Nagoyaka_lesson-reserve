from django.urls import path
from . import views

app_name = 'nagoyaka'

urlpatterns = [
    # [ステップ] '' と書くことで、トップページ（表紙）として表示されるようになるよ！
    path('', views.HomeView.as_view(), name="nagoyaka_home"),
]