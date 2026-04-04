from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.dispatch import receiver
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
# [ステップ] 会員登録が終わったよ！という合図（シグナル）を受け取るための準備
from allauth.account.signals import user_signed_up

class UserManager(BaseUserManager):
    """
    [ステップ] ユーザーの作り方のルールを決める場所
    メールアドレスを名前（ID）として使うように設定しているよ。
    """
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Emailアドレスは必須です")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    """
    [ステップ] ユーザーそのもののデータ項目を決める場所
    """
    # [ステップ] ログインには名前（username）を使わず、メールアドレスを使うよ
    username = None
    email = models.EmailField(unique=True)

    # [ステップ] ニックネームを保存できるようにするよ
    nickname = models.CharField(max_length=30, blank=True, unique=True, verbose_name="ニックネーム")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nickname"]

    def __str__(self):
        return self.nickname if self.nickname else self.email

# ==========================================
# 会員登録後の自動処理
# ==========================================

@receiver(user_signed_up)
def manage_new_user_allauth(request, user, **kwargs):
    print("SIGNAL RUNNING")
    """
    [ステップ] サインアップ（会員登録）ボタンが押されたあとに自動で動く魔法
    """

    # 1. [ステップ] まだ先生が確認していないので、ログインできない状態（お休み中）にする
    if not user.is_staff:
        user.is_active = False
        user.save()

        # 2. [ステップ] メールの内容を準備する
        user.refresh_from_db()
        nickname = user.nickname if user.nickname else "新しい利用者"
        staff_emails = list(get_user_model().objects.filter(is_staff=True).values_list('email', flat=True))
        activate_url = f"{settings.BASE_URL}/booking/activate/{user.id}/"

        subject_staff = "【承認待ち】利用者の登録申請"
        message_staff = (
            f"{nickname} さんから登録申請が届きました。\n\n"
            f"以下のURLから内容を確認して、承認してください。\n"
            f"{activate_url}"
        )

        # 3. [ステップ] 重要！メールを送る「守りの処理」
        # PythonAnywhere（無料）だとここで失敗しやすいので、try...except で守るよ
        try:
            send_mail(
                subject_staff,
                message_staff,
                settings.DEFAULT_FROM_EMAIL,
                staff_emails
            )
            # 成功したらコンソール（ログ）に「成功したよ」と出す
            print("Successfully sent approval email to staff.")

        except Exception as e:
            # [ステップ] もし「無料プランの制限」などでメールが送れなくても、
            # エラー画面を出さずに、こっそりログに記録して登録処理を続けるよ。
            print(f"メール送信に失敗しました（無料プラン制限など）: {e}")
            # ※ここで print した内容は、PythonAnywhereの「Server Log」で確認できるよ！