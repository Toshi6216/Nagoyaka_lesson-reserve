from django.db import models
from django.conf import settings
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string


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
    