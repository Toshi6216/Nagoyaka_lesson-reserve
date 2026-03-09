from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    # 一覧にnicknameを表示
    list_display = ("email", "nickname", "is_staff", "is_active")
    
    # 編集画面の項目設定にnicknameを追加
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("個人情報", {"fields": ("nickname",)}), # ここに追加
        ("Permissions", {"fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
    )
    
    # ユーザー作成画面の項目にも追加
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "nickname", "password"),
        }),
    )
    search_fields = ("email", "nickname")
    ordering = ("email",)

# これが必須です！
admin.site.register(User, CustomUserAdmin)