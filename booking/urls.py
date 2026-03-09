from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    # --- カレンダー・予約基本 ---
    path('', views.calendar_view, name='calendar'),
    #path('add/', views.add_reservation, name='add_reservation'),
    path('get/', views.get_reservations, name='get_reservations'),
    path('delete/', views.delete_reservation, name='delete_reservation'),
    path('quit/<int:res_id>/', views.quit_reservation, name='quit_reservation'),

    # --- 詳細・掲示板・編集 ---
    path('lesson/<int:pk>/detail/', views.lesson_detail_view, name='lesson_detail'),
    path('lesson/<int:pk>/post_message/', views.post_message, name='post_message'),
    path('lesson/<int:pk>/edit/', views.lesson_edit, name='lesson_edit'),
    # [エラー解消] 掲示板一覧（メッセージリスト）への道を復活！
    path('messages/', views.message_list_view, name='message_list'),

    # --- ユーザー管理・承認 ---
    path('my-bookings/', views.my_booking_view, name='my_bookings'),
    path('waiting-users/', views.waiting_user_list, name='waiting_user_list'),
    path('activate/<int:user_id>/', views.activate_user, name='activate_user'),
    path('approve-user/<int:user_id>/', views.approve_user_from_list, name='approve_user_from_list'),
    path('staff-manage/', views.staff_manage, name='staff_manage'),

    # --- スタッフ専用 ---
    path('staff/schedule/', views.staff_schedule_view, name='staff_schedule'),

    # --- お問い合わせ ---
    path('contact/', views.contact_view, name='contact'),
    path('contact/send/', views.contact_send, name='contact_send'),

    path('lesson/add/', views.lesson_edit, name='lesson_add'), # 新規登録用
]