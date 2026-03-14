from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
# [追加] allauth専用の合図をインポート
from allauth.account.signals import user_signed_up
User = get_user_model()

class UserManager(BaseUserManager):
    """
    カスタムユーザーマネージャー
    emailを唯一の識別子としてユーザーを作成するようにロジックを書き換えます。
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

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    # nicknameを追加
    nickname = models.CharField(max_length=30, blank=True, verbose_name="ニックネーム")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nickname"]  # createsuperuser時にnicknameも聞かれるようにします

    def __str__(self):
        return self.nickname if self.nickname else self.email
    
# [新しい魔法] 会員登録が「完全に」終わったときに自動で呼ばれる
@receiver(user_signed_up)
def manage_new_user_allauth(request, user, **kwargs):
    # この 'user' には、入力されたばかりの nickname がもう入っています！
    
    # 1. まずは「お休み中（is_active=False）」にする
    if not user.is_staff:
        user.is_active = False
        user.save()

        # 2. 最新のデータを読み込む
        user.refresh_from_db()
        nickname = user.nickname if user.nickname else "新しい利用者"

        # 3. 先生と本人にメールを送る
        staff_emails = list(get_user_model().objects.filter(is_staff=True).values_list('email', flat=True))
        #activate_url = f"http://127.0.0.1:8000/booking/activate/{user.id}/" ローカルサーバ用
        activate_url = f"{settings.BASE_URL}/booking/activate/{user.id}/"
        
        # スタッフへ
        send_mail(
            "【承認待ち】利用者の登録申請",
            f"{nickname} さんから登録申請がありました。\n承認リンク：{activate_url}",
            settings.DEFAULT_FROM_EMAIL,
            staff_emails
        )
        
        # 本人へ
        send_mail(
            "登録申請を受け付けました",
            f"{nickname} 様\n\nスタッフが確認中です。承認までお待ちください。",
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )
