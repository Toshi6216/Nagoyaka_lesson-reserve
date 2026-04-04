
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
import json
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from .models import Reservation, LessonMessage, BoardAccess
from django.views.decorators.http import require_POST
from .forms import LessonForm

User = get_user_model()

# ==========================================
# 1. カレンダー表示・データ取得
# ==========================================

@login_required
def calendar_view(request):
    """[ステップ] カレンダーの画面をひらくよ"""
    return render(request, 'booking/calendar.html')

@login_required
def get_reservations(request):
    """[ステップ] 1日1つのマークにまとめつつ、詳細データも送るよ"""
    #reservations = Reservation.objects.all()

    """[ステップ] 3か月前までのデータに絞って、カレンダーに送るよ"""
    
    # --- [追加] ここから：3か月前の日付を計算 ---
    from django.utils import timezone
    from datetime import timedelta
    # 今から90日（約3か月）前より後のものだけを表示対象にする
    three_months_ago = timezone.now() - timedelta(days=90)
    # ------------------------------------------

    # --- [修正] all() ではなく filter(...) を使う ---
    reservations = Reservation.objects.filter(start__gte=three_months_ago)
    # ------------------------------------------

    daily_data = {}
    event_list = []
    # [ステップ] すでにマークをつけた日付を覚えておくためのセット
    dates_with_events = set()

    for res in reservations:
        date_str = res.start.date().isoformat()

        # --- 1. 詳細リスト用のデータ (これは今まで通り全部入れる) ---
        lesson_info = {
            'id': res.id,
            'title': res.title,
            'start': res.start.isoformat(),
            'end': res.end.isoformat(),
            'description': res.detail,
            'p_count': res.participants.count(),
        }
        if date_str not in daily_data:
            daily_data[date_str] = []
        daily_data[date_str].append(lesson_info)

        # --- 2. カレンダーの「●」印用のデータ (ここを修正！) ---
        # [ステップ] その日にまだマークをつけていなければ、ひとつだけ追加するよ
        if date_str not in dates_with_events:
            event_list.append({
                'title': '●',
                'start': res.start.date().isoformat(), # 時間は含めず日付だけでOK
                'allDay': True, # 1日中（＝マスの真ん中あたり）に表示
                'display': 'list-item',
                'color': '#ffc107'
            })
            # マークをつけたことをメモする
            dates_with_events.add(date_str)

    return JsonResponse({
        'daily_data': daily_data,
        'event_list': event_list
    })

# ==========================================
# 2. 予約・作成・削除・キャンセル
# ==========================================

@require_POST
def add_reservation(request):
    """[ステップ] レッスンを新しく作るよ（先生専用）"""
    try:
        data = json.loads(request.body)
        Reservation.objects.create(
            title=data.get('event_title'),
            detail=data.get('description', ''),
            start=data.get('start_date'),
            end=data.get('end_date'),
            user=request.user
        )
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def delete_reservation(request):
    """[ステップ] レッスンを消すよ"""
    data = json.loads(request.body)
    res = get_object_or_404(Reservation, id=data.get('res_id'))
    if request.user.is_staff or res.user == request.user:
        res.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=403)

@login_required
@require_POST
def quit_reservation(request, res_id):
    """[ステップ] 予約をキャンセルし、JavaScriptかHTMLかに合わせて正しく返事をするよ"""
    res = get_object_or_404(Reservation, id=res_id)

    if request.user in res.participants.all():
        res.participants.remove(request.user)

        # --- キャンセル通知メール（自分を含む全スタッフに送信） ---
        staff_emails = list(User.objects.filter(is_staff=True).values_list('email', flat=True))
        if staff_emails:
            # [重要ステップ] UTC時間を日本時間に変換する
            local_start = timezone.localtime(res.start)

            subject = f"【キャンセル】{res.title} - {request.user.nickname}様"
            message = (
                f"管理者 各位\n\n"
                f"以下のレッスンの予約がキャンセルされました。\n\n"
                f"■レッスン名: {res.title}\n"
                # [修正ポイント] local_start を使うように変更
                f"■日時: {local_start.strftime('%m/%d %H:%M')} ～\n"
                f"■キャンセル者: {request.user.nickname} 様\n"
            )
            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, staff_emails)
            except:
                pass

    # --- [重要] 返し方の切り分け ---
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({'status': 'ok'})

    return redirect('booking:lesson_detail', pk=res_id)

# ==========================================
# 3. レッスン詳細・掲示板・編集
# ==========================================

@login_required
def lesson_detail_view(request, pk):
    """[ステップ] 詳細ページを表示し、予約時は自分を含むスタッフ全員へメールを送るよ"""
    reservation = get_object_or_404(Reservation, pk=pk)

    if request.method == 'POST':
        # [ステップ] まだ予約していなければ名簿に追加する
        if request.user not in reservation.participants.all():
            reservation.participants.add(request.user)

            # --- [重要修正] 予約通知メール：自分も含めた全スタッフに送る ---
            # excludeを外すことで、スタッフが自分1人の時でも自分にメールが届きます
            staff_emails = list(User.objects.filter(is_staff=True).values_list('email', flat=True))

            # データベースのUTC時間を、日本時間に変換するよ
            jst_start = timezone.localtime(reservation.start)
            jst_end = timezone.localtime(reservation.end)

            if staff_emails:
                # スタッフが予約した場合は件名に(スタッフ)と付けてわかりやすくする
                role_str = "(スタッフ)" if request.user.is_staff else ""
                subject = f"【新規予約{role_str}】{reservation.title} - {request.user.nickname}様"
                message = (
                    f"管理者 各位\n\n"
                    f"以下のレッスンに新しい予約が入りました。\n\n"
                    f"■レッスン名: {reservation.title}\n"
                    f"■日時: {jst_start.strftime('%m/%d %H:%M')} ～ {jst_end.strftime('%H:%M')}\n"
                    f"■予約者: {request.user.nickname} 様 {role_str}\n\n"
                    f"内容を確認してください。\n"
                )
                try:
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, staff_emails)
                except:
                    # メール送信でエラーが起きても画面が止まらないようにする魔法
                    pass

        return redirect('booking:lesson_detail', pk=pk)

    # --- 掲示板の表示準備 ---
    messages = reservation.messages.all().order_by('created_at')

    # [ステップ] このページを開いた時間を記録して「新着マーク」を消せるようにする（既読処理）
    BoardAccess.objects.update_or_create(
        user=request.user,
        reservation=reservation,
        defaults={'last_accessed_at': timezone.now()}
    )

    context = {
        'res': reservation,
        'participants': reservation.participants.all(),
        'is_joined': request.user in reservation.participants.all(),
        'messages': messages,
    }
    return render(request, 'booking/lesson_detail.html', context)

@login_required
@require_POST
def post_message(request, pk):
    """[ステップ] レッスン参加者とスタッフ全員にメールで知らせるよ"""
    res = get_object_or_404(Reservation, pk=pk)
    text = request.POST.get('text')
    
    if text:
        # 1. メッセージを保存
        LessonMessage.objects.create(
            reservation=res, 
            author=request.user, 
            text=text
        )

        # 2. メール送信先リストを作る
        # A. レッスン参加者全員
        participant_emails = list(res.participants.all().values_list('email', flat=True))
        # B. スタッフ全員
        staff_emails = list(User.objects.filter(is_staff=True).values_list('email', flat=True))
        
        # 3. リストを合体させて、重複（参加者かつスタッフの場合など）を削除
        all_recipients = list(set(participant_emails + staff_emails))
        
        # もし可能なら「投稿した本人」を除外すると親切です
        if request.user.email in all_recipients:
            all_recipients.remove(request.user.email)
        
        if all_recipients:
            subject = f"【掲示板】{res.title} にメッセージが届きました"
            message = (
                f"掲示板に新しい投稿がありました。\n\n"
                f"■レッスン名: {res.title}\n"
                f"■投稿者: {request.user.nickname} 様\n"
                f"■内容:\n{text}\n\n"
                f"以下のURLから確認してください。\n"
                f"{settings.BASE_URL}/booking/lesson/{pk}/detail/"
            )
            
            # 4. [バリア] メール送信
            try:
                send_mail(
                    subject, 
                    message, 
                    settings.DEFAULT_FROM_EMAIL, 
                    all_recipients # 全員に送信
                )
                print(f"掲示板メール送信成功: {len(all_recipients)} 名へ送信")
            except Exception as e:
                print(f"掲示板メール送信失敗: {e}")

    return redirect('booking:lesson_detail', pk=pk)



@login_required
def message_list_view(request):
    """[ステップ] 掲示板があるレッスンを一覧表示。新着を一番上にするよ"""
    reservations = Reservation.objects.all()
    chat_list = []

    for res in reservations:
        latest_msg = res.messages.order_by('-created_at').first()

        # メッセージが1つもないレッスンは一覧に出さない
        if not latest_msg:
            continue

        access = BoardAccess.objects.filter(user=request.user, reservation=res).first()
        has_new = False
        if latest_msg:
            if not access or latest_msg.created_at > access.last_accessed_at:
                has_new = True

        # HTML側の変数名に合わせてデータをセット
        chat_list.append({
            'reservation': res,
            'last_message': latest_msg,
            'has_new': has_new,
        })

    # 新着があるものを優先し、かつ日付が新しい順に並び替え
    chat_list.sort(key=lambda x: (not x['has_new'], x['last_message'].created_at), reverse=True)

    return render(request, 'booking/message_list.html', {'chat_list': chat_list})



@staff_member_required
def lesson_edit(request, pk=None):
    """[ステップ] 登録と編集を両方こなす魔法の関数だよ"""
    if pk:
        lesson = get_object_or_404(Reservation, pk=pk)
        title = "レッスンの編集"
    else:
        lesson = None
        title = "新規レッスン登録"

    if request.method == 'POST':
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            # --- [ここを修正！] ---
            # まだ保存（commit=False）せずに、一度データを受け取ります
            new_lesson = form.save(commit=False)

            # もし新規登録（まだ作者が決まっていない）なら、今のユーザーを作者にする
            if not pk:
                new_lesson.user = request.user

            # ここで本当に保存する
            new_lesson.save()
            # ---------------------

            return redirect('booking:lesson_detail', pk=new_lesson.pk)
    else:
        # (以下、変更なし)
        initial_data = {}
        if not lesson:
            date_str = request.GET.get('date')
            if date_str:
                initial_data['start'] = f"{date_str}T10:00"
                initial_data['end'] = f"{date_str}T11:00"

        form = LessonForm(instance=lesson, initial=initial_data)

    return render(request, 'booking/lesson_edit.html', {
        'form': form,
        'lesson': lesson,
        'title': title,
    })

# ==========================================
# 4. ユーザー管理・承認
# ==========================================

@staff_member_required
def waiting_user_list(request):
    """[ステップ] 承認待ちユーザー一覧"""
    waiting_users = User.objects.filter(is_active=False).order_by('-date_joined')
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        target_user = get_object_or_404(User, id=user_id)
        if action == 'approve':
            target_user.is_active = True
            target_user.save()
        elif action == 'delete':
            target_user.delete()
        return redirect('booking:waiting_user_list')
    return render(request, 'booking/waiting_user_list.html', {'users': waiting_users})

def activate_user(request, user_id):
    """[ステップ] メールからの承認"""
    target_user = get_object_or_404(User, id=user_id)
    target_user.is_active = True
    target_user.save()
    return HttpResponse(f"<h3>{target_user.nickname} さんを承認しました！</h3>")

@staff_member_required
def approve_user_from_list(request, user_id):
    """[ステップ] ボタンから承認"""
    target_user = get_object_or_404(User, id=user_id)
    target_user.is_active = True
    target_user.save()
    return redirect('booking:waiting_user_list')

@staff_member_required
def staff_manage(request):
    """[ステップ] スタッフ権限管理"""
    users = User.objects.all().order_by('-is_staff', 'nickname')
    if request.method == 'POST':
        target_user_id = request.POST.get('user_id')
        make_staff = request.POST.get('make_staff') == 'true'
        target_user = get_object_or_404(User, id=target_user_id)
        if target_user != request.user:
            target_user.is_staff = make_staff
            target_user.save()
        return redirect('booking:staff_manage')
    return render(request, 'booking/staff_manage.html', {'users': users})

# ==========================================
# 5. マイページ・お問い合わせ
# ==========================================

@login_required
def my_booking_view(request):
    """[ステップ] 自分の予約一覧"""
    sort = request.GET.get('sort', 'old')
    query = Reservation.objects.filter(participants=request.user)
    if sort == 'new':
        my_reservations = query.order_by('-start')
    else:
        my_reservations = query.order_by('start')
    return render(request, 'booking/my_bookings.html', {
        'my_reservations': my_reservations,
        'current_sort': sort
    })

@staff_member_required
def staff_schedule_view(request):
    """[ステップ] 先生用スケジュール"""
    reservations = Reservation.objects.all().order_by('start')
    return render(request, 'booking/staff_schedule.html', {'reservations': reservations})

def contact_view(request):
    return render(request, 'booking/contact.html')

from django.utils import timezone # [ステップ] 時間を扱うために必要

def contact_send(request):
    if request.method == 'POST':
        # 1. フォームからすべての項目を受け取る
        name = request.POST.get('name')
        email = request.POST.get('email')
        tel = request.POST.get('tel', 'なし')  # 電話番号は未入力でもOKにする
        message_body = request.POST.get('message')

        staff_emails = list(User.objects.filter(is_staff=True).values_list('email', flat=True))

        if staff_emails:
            # 2. メールの本文をきれいにまとめる
            subject = f"【お問い合わせ】{name} 様より"
            full_message = (
                f"ホームページからお問い合わせがありました。\n\n"
                f"■お名前: {name}\n"
                f"■メールアドレス: {email}\n"
                f"■電話番号: {tel}\n\n"
                f"■お問い合わせ内容:\n{message_body}"
            )

            # 3. メール送信（バリア付き）
            try:
                send_mail(
                    subject,
                    full_message,
                    settings.DEFAULT_FROM_EMAIL,
                    staff_emails
                )
            except Exception as e:
                print(f"Mail error: {e}")

        return render(request, 'booking/contact_success.html')

    return redirect('booking:contact')

# views.py のどこか（一番下など）に追加
def csrf_failure_view(request, reason=""):
    """[ステップ] CSRFエラーが起きたときに、やさしくホームへ案内する画面"""
    return render(request, '403_csrf.html', status=403)
