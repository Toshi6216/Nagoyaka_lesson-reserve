from django.db import models
from django.conf import settings
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
# ユーザーモデルを取得
User = get_user_model()


# [ステップ] 予約（レッスン）自体のデータを保存する箱
class Reservation(models.Model):
    title = models.CharField(max_length=150, verbose_name="予約タイトル")
    detail = models.TextField(blank=True, verbose_name="詳細内容")
    start = models.DateTimeField(verbose_name="開始日時")
    end = models.DateTimeField(verbose_name="終了日時")
    
    # 先生（作成者）が消えたら、そのレッスンも消える設定
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_reservations',
        verbose_name="作成者"
    )

    # 生徒さんたちのリスト
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='joined_reservations',
        verbose_name="参加者"
    )

    def __str__(self):
        return self.title

# --- [新機能] 幽霊データを残さないための魔法 ---
@receiver(pre_delete, sender=settings.AUTH_USER_MODEL)
def remove_user_from_reservations(sender, instance, **kwargs):
    """
    ユーザーが削除される直前に、すべての予約の参加者リストから
    そのユーザーを削除します。これで幽霊データが残らなくなります。
    """
    instance.joined_reservations.clear()


# [ステップ] レッスンごとの掲示板メッセージを保存するモデル
class LessonMessage(models.Model):
    # [解説] どのレッスンについてのメッセージか紐付けるよ
    # ここを on_delete=models.CASCADE に修正しました！
    reservation = models.ForeignKey(
        'Reservation', 
        on_delete=models.CASCADE, 
        related_name='messages',
        verbose_name="対象レッスン"
    )
    
    # [解説] 誰が書いたか記録するよ
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        verbose_name="投稿者"
    )
    
    # [解説] メッセージの内容だよ
    text = models.TextField(verbose_name="メッセージ内容")
    
    # [解説] 書いた時間を自動で記録するよ
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="投稿日時")

    class Meta:
        verbose_name = "レッスンメッセージ"
        ordering = ['created_at'] # 古い順（会話が続く順）に並べるよ

    def __str__(self):
        # author.nickname があることを前提にしているよ
        return f"{self.author.nickname}: {self.text[:10]}"
    
    # [ステップ] 30日経ったメッセージを「古い」と判断する命令だよ
    @property
    def is_expired(self):
        # レッスンの日から30日を計算するよ
        expiry_date = self.reservation.start + timedelta(days=30)
        return timezone.now() > expiry_date
    
# booking/models.py

class BoardAccess(models.Model):
    # [ステップ] 「だれが」「どの掲示板を」見たかを紐づけるよ
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    
    # [ステップ] 最後に見た時間を記録するよ（更新されるたびに時間が新しくなる設定だよ）
    last_accessed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'reservation') # 1人1レッスンにつき1つの記録にするよ



@receiver(pre_save, sender=User)
def send_approval_email(sender, instance, **kwargs):
    """
    [ステップ] ユーザーが「承認（is_active=True）」された瞬間にメールを送るよ
    """
    # すでに登録済みのユーザー（更新時）かどうかチェック
    if instance.pk:
        try:
            # 保存される前の、今の状態をデータベースから持ってくる
            old_instance = User.objects.get(pk=instance.pk)
            
            # 【重要】以前は「無効(False)」で、今回「有効(True)」に切り替わった場合だけ実行
            if not old_instance.is_active and instance.is_active:
                
                subject = "【TAP_NAGOYAKA】アカウント承認が完了しました"
                
                # メール本文に渡すデータ
                context = {
                    'user': instance,
                    # PythonAnywhereなどの本番ドメインに合わせてね
                    # [修正] 直接書かずに settings の値を使う！
                    'login_url': f"{settings.BASE_URL}/accounts/login/",
                    # [ポイント] ここで /home をガッチャンコする
                    'home_url': f"{settings.BASE_URL}/home/",
                }
                
                # 本文を組み立てる（※このあと作成するテキストファイルを読み込むよ）
                message = render_to_string('booking/emails/approved_notification.txt', context)
                
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [instance.email],
                        fail_silently=False,
                    )
                    print(f"承認メールを送信しました: {instance.email}")
                except Exception as e:
                    print(f"メール送信エラー: {e}")
                    
        except User.DoesNotExist:
            pass