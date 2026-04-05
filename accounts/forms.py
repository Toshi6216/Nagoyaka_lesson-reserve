from django import forms
from allauth.account.forms import SignupForm
from django.contrib.auth import get_user_model

# ユーザーモデルを呼んでくるよ
User = get_user_model()

# [ステップ] サインアップの入力項目を増やすための設計図
class CustomSignupForm(SignupForm):
    # ニックネームの入力欄を定義する
    nickname = forms.CharField(
        max_length=30,
        label='ニックネーム',
        widget=forms.TextInput(attrs={'placeholder': '表示名（掲示板などで使います）'})
    )
    # --- [追加] ニックネームが被っていないかチェックする魔法 ---
    def clean_nickname(self):
        nickname = self.cleaned_data.get('nickname')
        # データベースに同じニックネームの人がすでにいるか確認
        if User.objects.filter(nickname=nickname).exists():
            # 被っていたら、画面に優しいエラーメッセージを出す
            raise forms.ValidationError("このニックネームはすでに使われています。別の名前を入力してね。")
        return nickname
    # -----------------------------------------------------

    def save(self, request):
        # [ステップ] 入力されたデータをユーザーモデルに保存する
        user = super(CustomSignupForm, self).save(request)
        user.nickname = self.cleaned_data['nickname']
        user.save()
        return user