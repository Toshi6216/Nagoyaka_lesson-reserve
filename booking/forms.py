from django import forms
# [ステップ] 予約データの設計図（Reservation）を読み込むよ
from .models import Reservation

# [ステップ] レッスンを修正するための「入力フォーム」の設計図
class LessonForm(forms.ModelForm):
    class Meta:
        model = Reservation
        # [修正] モデルの名前に合わせて 'detail' にしたよ！
        fields = ['title', 'start', 'end', 'detail']
        
        # [ステップ] 入力欄の見た目を整える設定
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            # [ステップ] 日付と時間をカレンダーから選べるようにする魔法だよ
            'start': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}, 
                format='%Y-%m-%dT%H:%M'
            ),
            'end': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}, 
                format='%Y-%m-%dT%H:%M'
            ),
            # [修正] ここも 'detail' に変更！
            'detail': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }