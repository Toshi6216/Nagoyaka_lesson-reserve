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
     * [ステップ] 指定した日のレッスン一覧を表示する（ボタン付き）
     */
  
    function updateSidebarDisplay(dateStr, calendar) {
        selectedDateStr = dateStr;
        const lessons = cachedDailyData[dateStr] || [];
        // calendar.html側の受け皿IDに合わせる
        // const infoArea = document.getElementById('selected-date-info-area') || document.getElementById('selected-date-info');
        const infoArea = document.getElementById('selected-date-info');
        const container = document.getElementById('lesson-info-container');
        const label = document.getElementById('selected-date-label');
        const createBtn = document.getElementById('create-btn');

        const d = new Date(dateStr);
        label.innerText = `${d.getMonth() + 1}月${d.getDate()}日のレッスン`;

        if (lessons.length > 0) {
            let html = '';
            lessons.forEach(res => {
                // [ここが重要！] ボタン付きの新しい設計図です
                html += `
                    <div class="lesson-summary-item p-3 mb-3 shadow-sm border rounded bg-white">
                        <div class="row align-items-center">
                            <div class="col-7">
                                <h6 class="mb-1 fw-bold text-dark">${res.title}</h6>
                                <div class="small text-secondary">
                                    <i class="bi bi-clock"></i> ${res.start_time}〜
                                </div>
                            </div>
                            <div class="col-5 d-grid gap-1">
                                <a href="/booking/lesson/${res.id}/detail/" class="btn btn-sm btn-outline-primary fw-bold p-1" style="font-size: 0.75rem;">詳細</a>
                                <a href="/booking/lesson/${res.id}/detail/" class="btn btn-sm btn-warning fw-bold p-1 text-dark" style="font-size: 0.75rem;">参加</a>
                            </div>
                        </div>
                        ${isStaff ? `
                            <div class="mt-2 text-end border-top pt-1">
                                <button class="btn btn-link btn-sm text-danger p-0" onclick="window.deleteLesson('${res.id}', '${res.title}', '${dateStr}')">
                                    <i class="bi bi-trash"></i> 削除
                                </button>
                            </div>
                        ` : ''}
                    </div>
                `;
            });
            infoArea.innerHTML = html;
        } else {
            infoArea.innerHTML = '<p class="text-muted text-center py-3">予定はありません</p>';
        }

        container.classList.remove('d-none');
        if (createBtn) {
            createBtn.classList.remove('d-none');
            createBtn.href = `/booking/lesson/add/?date=${dateStr}`;
        }
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