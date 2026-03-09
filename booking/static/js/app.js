// [ステップ1] サーバー（Django）と安全に通信するための合言葉設定
axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

let selectedDateStr = ""; // いま選んでいる日付を覚えておく変数
let regModal;             // 登録画面（先生用）

/**
 * [ステップ2] 「1000」と入力されたら「10:00:00」に直す関数
 */
function formatTimeInput(timeStr) {
    const digits = timeStr.replace(/\D/g, ''); 
    let formatted = "";
    if (digits.length === 3) { formatted = "0" + digits.substring(0, 1) + ":" + digits.substring(1); }
    else if (digits.length === 4) { formatted = digits.substring(0, 2) + ":" + digits.substring(2); }
    else { formatted = timeStr; }
    return formatted.includes(":") ? formatted + ":00" : formatted;
}

/**
 * [ステップ3] ボタンを「処理中...」にして連打できないようにする魔法
 */
function setButtonLoading(btnElement, isLoading) {
    if (!btnElement) return;
    if (isLoading) {
        btnElement.disabled = true;
        btnElement.dataset.originalHtml = btnElement.innerHTML;
        btnElement.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 処理中...`;
    } else {
        btnElement.disabled = false;
        if (btnElement.dataset.originalHtml) {
            btnElement.innerHTML = btnElement.dataset.originalHtml;
        }
    }
}

/**
 * [ステップ4] 画面を「予定リスト」まで自動で動かす魔法
 */
function scrollToSidebar() {
    const target = document.getElementById('selected-date');
    if (target) {
        const offset = 80;
        const bodyRect = document.body.getBoundingClientRect().top;
        const targetRect = target.getBoundingClientRect().top;
        const targetPosition = targetRect - bodyRect - offset;
        window.scrollTo({ top: targetPosition, behavior: 'smooth' });
    }
}

// 画面の準備ができたらスタート！
document.addEventListener('DOMContentLoaded', function() {
    const regElem = document.getElementById('resModal');
    if (regElem) regModal = new bootstrap.Modal(regElem);

    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return;

 
    /**
     * [ステップ6修正] 1つのマークに詰め込まれた「全レッスン」を画面に表示する
     */
    function updateSidebarDisplay(dateStr, calendarInstance) {
        const eventListEl = document.getElementById('event-list');
        const selectedDateEl = document.getElementById('selected-date');
        
        if (selectedDateEl) selectedDateEl.innerText = dateStr + " の予約";
        eventListEl.innerHTML = "";

        // 1. その日の「マーク（イベント）」を1つだけ見つける [cite: 38]
        const dayMark = calendarInstance.getEvents().find(e => e.startStr === dateStr);
        
        // 2. マークがない、または中にレッスンが入っていない場合 [cite: 39]
        if (!dayMark || !dayMark.extendedProps.lessons) {
            eventListEl.innerHTML = '<div class="p-5 text-center text-muted">予約はありません</div>';
            return;
        }

        // 3. 詰め込まれたレッスン情報を取り出し、開始時間順に並べる
        const dailyLessons = dayMark.extendedProps.lessons;
        dailyLessons.sort((a, b) => new Date(a.start) - new Date(b.start));

        // 4. 各レッスンをカードにして表示する [cite: 41]
        dailyLessons.forEach(lesson => {
            const start = new Date(lesson.start).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            const end = new Date(lesson.end).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

            const div = document.createElement('div');
            div.className = "list-group-item p-3 border-start border-4 border-primary mb-3 shadow-sm rounded bg-white";
            div.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div style="flex: 1;">
                    <h5 class="mb-1 fw-bold text-dark">${lesson.title}</h5>
                    <p class="mb-0 text-primary small"><i class="bi bi-clock"></i> ${start} ～ ${end}</p>
                    <div class="mt-1">
                        ${lesson.p_count > 0 ? `<span class="badge bg-success small me-1">予約 ${lesson.p_count}名</span>` : ''}
                        ${lesson.has_new_message ? `<span class="badge bg-danger small">New</span>` : ''}
                    </div>
                </div>
                <div class="ms-2">
                    <a href="/booking/lesson/${lesson.id}/detail/" class="btn btn-sm btn-info text-white px-3">詳細</a>
                    ${isTeacher ? `<button class="btn btn-sm btn-outline-danger mt-1 d-block w-100" onclick="window.deleteLesson(${lesson.id}, '${lesson.title}', '${dateStr}')">削除</button>` : ''}
                </div>
            </div>`;
            eventListEl.appendChild(div);
        });
    }

    /**
     * [ステップ7] レッスンを新しく作る処理（先生用）
     */
    const saveBtn = document.getElementById('btn-save-modal');
    if (saveBtn) {
        saveBtn.onclick = function() {
            const title = document.getElementById('m-title').value;
            const startInput = document.getElementById('m-start').value;
            const endInput = document.getElementById('m-end').value;
            if (!title) return alert("名前を入れてね！");

            const data = {
                event_title: title,
                start_date: selectedDateStr + "T" + formatTimeInput(startInput),
                end_date: selectedDateStr + "T" + formatTimeInput(endInput),
                description: document.getElementById('m-desc').value
            };

            setButtonLoading(saveBtn, true);
            axios.post('/booking/add/', data)
                .then(() => {
                    regModal.hide();
                    calendar.refetchEvents();
                    setTimeout(() => updateSidebarDisplay(selectedDateStr, calendar), 500);
                })
                .catch(err => alert("⚠️ エラー: " + (err.response.data.message || "登録できません")))
                .finally(() => setButtonLoading(saveBtn, false));
        };
    }

    // 削除の命令を外からも使えるようにする
    window.deleteLesson = (id, title, dateStr) => {
        if (confirm(`「${title}」を削除しますか？`)) {
            axios.post('/booking/delete/', { res_id: id })
            .then(() => {
                calendar.refetchEvents();
                setTimeout(() => updateSidebarDisplay(dateStr, calendar), 500);
            }).catch(() => alert("削除に失敗しました。"));
        }
    };
});