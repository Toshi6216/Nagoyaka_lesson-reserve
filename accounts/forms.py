from django import forms
from allauth.account.forms import SignupForm

# [ステップ] サインアップの入力項目を増やすための設計図
class CustomSignupForm(SignupForm):
    # ニックネームの入力欄を定義する
    nickname = forms.CharField(
        max_length=30,
        label='ニックネーム',
        widget=forms.TextInput(attrs={'placeholder': '表示名（掲示板などで使います）'})
    )

    def save(self, request):
        # [ステップ] 入力されたデータをユーザーモデルに保存する
        user = super(CustomSignupForm, self).save(request)
        user.nickname = self.cleaned_data['nickname']
        user.save()
        return user