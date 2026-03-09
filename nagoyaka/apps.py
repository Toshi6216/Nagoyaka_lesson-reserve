from django.apps import AppConfig

# 小学生向けの解説：
# ここは「このアプリ（nagoyaka）を動かすよ！」という設定を書く場所だよ。
# JavaScriptのコード（// で始まるもの）をここに書くと、エラーになっちゃうんだ。
class NagoyakaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nagoyaka'