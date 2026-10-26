/* TRMD Web UI — 前端腳本(含從 telegram-tt 移植的漸變背景實現)
 * Copyright © 2024-2026 Gentlesprite
 * SPDX-License-Identifier: GPL-3.0-only
 * 本檔案整體以 GNU GPL-3.0 授權;完整許可見倉庫根目錄 LICENCE。
 */
const EMPTY_SUMMARY = {percent: 0, info: '0.00B / 0.00B', speed: '', remaining: ''};

var SECTIONS = {
    download: ['download'],
    upload: ['upload'],
    listener: ['listener'],
    admin: ['admin']
};
var PAGES = SECTIONS.download.concat(SECTIONS.upload, SECTIONS.listener, SECTIONS.admin);  // 各側邊欄頁面。
var SUMMARY_IDS = {
    download: {fill: 'overallFill', percent: 'overallPercent', info: 'overallInfo', extra: 'overallExtra'},
    upload: {fill: 'uploadFill', percent: 'uploadPercent', info: 'uploadInfo', extra: 'uploadExtra'}
};  // 下載與上載各自獨立的總進度面板,避免相互覆蓋。
var SECTION_KEY = 'trmd_section';
var LISTEN_KEY = 'trmd_listen';
var HAS_BOT = document.body.getAttribute('data-bot') === '1';  // 是否設定了機械人,決定上載/監聽側邊欄是否展示(無機械人時只有下載可用)。
var COLLAPSE_KEY = 'trmd_collapsed';  // 各分組摺疊狀態的本機儲存鍵。
var ALL_KEY = 'trmd_all_collapsed';  // 下載頁全部摺疊開關的本機儲存鍵。
var UPLOAD_ALL_KEY = 'trmd_upload_all_collapsed';  // 上載頁全部摺疊開關的本機儲存鍵。
var LINK_LAST_KEY = 'trmd_link_last';  // 下載頁連結層最後一次手動選擇的本機儲存鍵。
var UPLOAD_LAST_KEY = 'trmd_upload_last';  // 上載頁頻道層最後一次手動選擇的本機儲存鍵。
var LISTEN_TABS = ['forward', 'download'];  // 監聽頁的選項卡:轉發、下載。

var STATE_TEXT = {
    pending: '佇列中',  // 排隊中,尚未開始處理(對應後端 DownloadStatus.PENDING)。
    downloading: '下載中',
    paused: '已暫停',
    cancelled: '已取消',
    success: '已完成',
    skip: '已跳過',
    failure: '失敗'
};
var STATE_CLASS = {
    pending: 'status-pending',
    downloading: 'status-running',
    paused: 'status-pending',
    cancelled: 'status-skip',
    success: 'status-done',
    skip: 'status-skip',
    failure: 'status-failed'
};
var STATE_ICON = {
    pending: '⏳',
    downloading: '📥',
    paused: '⏸️',
    cancelled: '⏹️',
    success: '✅',
    skip: '⏭',
    failure: '❌'
};

var HEAD_LABELS = ['頻道', '頻道 / 連結', '頻道 / 連結 / 名稱'];  // 表頭首列隨目前展開的層級變化。
var SIZE_LABELS = ['完成 / 總數', '完成 / 總數', '數量 / 大小'];  // 第三列同理,分組行是數量,成員行才是位元組大小。
var UPLOAD_HEAD_NAME = ['頻道', '頻道 / 檔案路徑'];  // 上載頁只有頻道與檔案兩級。
var UPLOAD_HEAD_SIZE = ['完成 / 總數', '大小'];
var UPLOAD_TEXT = {
    pending: '佇列中',
    uploading: '上載中',
    paused: '已暫停',
    cancelled: '已取消',
    success: '已完成',
    sent: '已完成',
    failure: '失敗'
};
var UPLOAD_CLASS = {
    pending: 'status-pending',
    uploading: 'status-running',
    paused: 'status-pending',
    cancelled: 'status-skip',
    success: 'status-done',
    sent: 'status-done',
    failure: 'status-failed'
};
var UPLOAD_ICON = {
    pending: '⏳',
    uploading: '📤',
    paused: '⏸️',
    cancelled: '⏹️',
    success: '✅',
    sent: '✅',
    failure: '❌'
};
var collapsed = {};
var allCollapsed = false;
var uploadAllCollapsed = false;
var lastLinkCollapsed = true;  // 下載頁連結層最後的手動選擇,缺省摺疊以保持原有預設。
var lastUploadCollapsed = false;  // 上載頁頻道層最後的手動選擇,缺省展開以保持原有預設。
var UNGROUPED_NAME = '未分組';
var currentSection = 'download';
var currentListen = 'forward';
var lastDownloadActive = 0;
var lastUploadActive = 0;
var lastListenCount = 0;
var lastUploadFinished = 0;  // 上載已結束(成功 + 失敗)的任務數,用於驅動背景漸變步進。

function esc(text) {
    var div = document.createElement('div');
    div.textContent = text === undefined || text === null ? '' : text;
    return div.innerHTML;
}

function escAttr(text) {
    return esc(text).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function dash(text) {
    return text ? esc(text) : '—';
}

function progressCell(percent) {
    // --p 供手機端把橫向條換成圓環時使用(帶 % 的完整角度值);桌面端不讀取,無副作用。
    return '<span class="cell-progress" style="--p:' + percent + '%">' +
        '<span class="track"><span class="fill" style="width:' + percent + '%"></span></span>' +
        '<span class="pct">' + percent + '%</span></span>';
}

var SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];  // 與終端機的十進制單位保持一致。

function sizeText(bytes) {
    var value = Number(bytes) || 0;
    var index = 0;
    while (value >= 1000 && index < SIZE_UNITS.length - 1) {
        value = value / 1000;
        index++;
    }
    return value.toFixed(2) + SIZE_UNITS[index];
}

function secondsText(seconds) {
    var total = Math.floor(Number(seconds) || 0);
    if (total < 60) {
        return total + '秒';
    }
    if (total < 3600) {
        return Math.floor(total / 60) + '分' + (total % 60) + '秒';
    }
    return Math.floor(total / 3600) + '時' + Math.floor(total % 3600 / 60) + '分' + (total % 60) + '秒';
}

function groupStat(members, live) {
    var speed = 0;
    var left = 0;
    for (var i = 0; i < members.length; i++) {
        var member = members[i];
        var task = live[member.task_id] || member;  // 上載成員自帶進度字段,查不到進度列任務時回退到自身。
        if (member.state === 'success' || member.state === 'skip' || member.state === 'sent' || member.state === 'cancelled') {
            continue;  // 已完成、已跳過、已發送的成員不再計入速度與剩餘。
        }
        if (task && task.speed_value) {
            speed += Number(task.speed_value) || 0;
        }
        left += Math.max((Number(member.size_byte) || 0) - (Number(task && task.completed) || 0), 0);
    }
    return {speed: speed, remaining: speed && left > 0 ? left / speed : null};
}

function groupStatCells(stat) {
    var speed = stat.speed ? sizeText(stat.speed) + '/s' : '—';
    var remain = stat.remaining === null ? '—' : secondsText(stat.remaining);
    return '<span class="cell-speed">' + speed + '</span>' +
        '<span class="cell-remain">' + remain + '</span>';
}

function taskActions(state, link, messageId, kind, id, pauseRequested, cancelRequested) {
    if (cancelRequested) {
        return '<span class="admin-feedback">取消中…</span>';
    }
    if (pauseRequested) {
        return '<span class="admin-feedback">暫停中…</span>';
    }
    var actions = [];
    if (state === 'pending' || state === 'downloading' || state === 'uploading') {
        actions.push(['pause', '暫停', false], ['cancel', '取消', true]);
    } else if (state === 'paused') {
        actions.push(['resume', '繼續', false], ['cancel', '取消', true]);
    } else if (state === 'failure') {
        actions.push(['retry', '重試', false]);
    }
    if (!actions.length) {
        return '';
    }
    return '<span class="task-actions">' + actions.map(function (action) {
        var attrs = kind === 'download' ?
            ' data-link="' + escAttr(link) + '" data-message-id="' + escAttr(messageId) + '"' :
            ' data-task-id="' + escAttr(id) + '"';
        return '<button class="task-action' + (action[2] ? ' danger' : '') +
            '" type="button" data-task-kind="' + kind + '" data-action="' + action[0] + '"' +
            attrs + '>' + action[1] + '</button>';
    }).join('') + '</span>';
}

function taskRow(task, member, link) {
    var done = task.percent >= 100;
    var state = member.state || 'downloading';
    var stateText = STATE_TEXT[state] || '下載中';
    // data-task-id 供"列表結構未變時就地更新進度",避免每秒整表重建。
    return '<div class="task-row member-row" data-task-id="' + escAttr(task.id) + '">' +
        '<span class="cell-name"><span class="ficon">' + esc(task.type || '📄') + '</span>' +
        '<span class="fname" title="' + escAttr(task.filename) + '">' + esc(task.filename) + '</span></span>' +
        progressCell(task.percent) +
        '<span class="cell-size">' + dash(task.info) + '</span>' +
        '<span class="cell-speed">' + dash(task.speed) + '</span>' +
        '<span class="cell-remain">' + dash(task.remaining) + '</span>' +
        '<span class="cell-status ' + (done ? 'status-done' : (STATE_CLASS[state] || 'status-running')) + '">' +
        (done ? '已完成' : stateText) +
        taskActions(state, link, member.message_id, 'download', '', member.pause_requested, member.cancel_requested) +
        '</span>' +
        '</div>';
}

function memberRow(item, link) {
    var state = item.state || 'pending';
    var text = STATE_TEXT[state] || '佇列中';
    var cls = STATE_CLASS[state] || 'status-pending';
    var pending = state === 'pending';
    var progress;
    if (state === 'success') {
        progress = progressCell(100);
    } else if (item.note) {  // 不支援或被忽略的類型拿不到檔案類型,進度欄改為顯示具體原因,避免與普通跳過混淆。
        progress = '<span class="cell-progress"><span class="pct note" title="' + escAttr(item.note) + '">' +
            esc(item.note) + '</span></span>';
    } else {
        progress = '<span class="cell-progress"><span class="pct' + (pending ? ' pending' : '') + '">' + text + '</span></span>';
    }
    return '<div class="task-row member-row">' +
        '<span class="cell-name"><span class="ficon">' + (STATE_ICON[state] || '⏳') + '</span>' +
        '<span class="fname" title="' + escAttr(item.name) + '">' + esc(item.name) + '</span>' +
        (item.date ? '<span class="gcount">' + esc(item.date) + '</span>' : '') +
        '</span>' +
        progress +
        '<span class="cell-size">' + dash(item.size) + '</span>' +
        '<span class="cell-speed">—</span>' +
        '<span class="cell-remain">—</span>' +
        '<span class="cell-status ' + cls + '">' + text +
        taskActions(state, link, item.message_id, 'download', '', item.pause_requested, item.cancel_requested) +
        '</span>' +
        '</div>';
}

function linkStatusCell(link) {
    var remaining = link.remaining || 0;
    var failed = link.failed || 0;
    var cancelled = link.cancelled || 0;
    if (remaining) {
        return '<span class="cell-status status-pending">剩 ' + remaining + ' 條</span>';
    }
    if (failed) {
        return '<span class="cell-status status-failed">失敗 ' + failed + ' 條</span>';
    }
    if (cancelled && cancelled === link.total) {
        return '<span class="cell-status status-skip">已取消</span>';
    }
    return '<span class="cell-status status-done">已完成</span>';
}

function getChannelGroups(links) {
    var groups = [];  // 按頻道分組下載連結,保持頻道首次出現的順序。
    var index = {};
    var i;
    for (i = 0; i < links.length; i++) {
        var channel = links[i].channel || UNGROUPED_NAME;
        if (index[channel] === undefined) {
            index[channel] = groups.length;
            groups.push({channel: channel, name: '', links: []});
        }
        var group = groups[index[channel]];
        var name = links[i].channel_name || channel;
        if (name.length > group.name.length) {
            group.name = name;  // 同一頻道取資訊最全的名稱,"標題(ID)"比純ID長。
        }
        group.links.push(links[i]);
    }
    for (i = 0; i < groups.length; i++) {
        var channelGroup = groups[i];
        channelGroup.count = channelGroup.links.length;
        channelGroup.complete = 0;
        channelGroup.member = 0;
        channelGroup.remaining = 0;
        channelGroup.failed = 0;
        channelGroup.cancelled = 0;
        channelGroup.members = [];  // 彙總該頻道下所有連結的成員,用於計算頻道級速度與剩餘時間。
        for (var j = 0; j < channelGroup.links.length; j++) {
            channelGroup.complete += channelGroup.links[j].complete || 0;
            channelGroup.member += channelGroup.links[j].member || 0;
            channelGroup.remaining += channelGroup.links[j].remaining || 0;
            channelGroup.failed += channelGroup.links[j].failed || 0;
            channelGroup.cancelled += channelGroup.links[j].cancelled || 0;
            channelGroup.members = channelGroup.members.concat(channelGroup.links[j].queue || []);
        }
        var base = channelGroup.member - channelGroup.failed - channelGroup.cancelled;
        channelGroup.percent = base ?
            Math.round(channelGroup.complete / base * 1000) / 10 : 0;
    }
    return groups;
}

function channelBlock(group, live) {
    var key = 'channel:' + group.channel;
    var filtering = Boolean(statFilter.download);
    // 篩選時強制展開,避免結果被摺疊狀態藏起來。
    var isCollapsed = filtering ? false : (collapsed[key] === undefined ? allCollapsed : collapsed[key]);
    var stat = groupStat(group.members || [], live);
    var html = '<div class="group' + (isCollapsed ? '' : ' open') + '" data-channel="' + escAttr(key) + '" data-level="1">' +
        '<div class="group-head" data-channel="' + escAttr(key) + '">' +
        '<span class="cell-name"><span class="arrow"></span>' +
        '<span class="ficon">📺</span>' +
        '<span class="gname" title="' + escAttr(group.name || group.channel) + '">' +
        esc(group.name || group.channel) + '</span>' +
        '<span class="gcount">' + group.count + ' 個連結</span></span>' +
        progressCell(group.percent) +
        '<span class="cell-size">' + group.complete + '/' + group.member + '</span>' +
        groupStatCells(stat) +
        linkStatusCell(group) +
        '</div>' +
        '<div class="group-body"' + (isCollapsed ? ' style="display:none"' : '') + '>';
    var body = '';
    for (var i = 0; i < group.links.length; i++) {
        body += linkBlock(group.links[i], live);
    }
    if (filtering && !body) {
        return '';  // 篩選後該頻道下沒有任何匹配內容,整組不顯示。
    }
    return html + body + '</div></div>';
}

function linkBlock(link, live) {
    var key = 'link:' + link.link;
    var filtering = Boolean(statFilter.download);
    var all = link.queue || [];
    var members = all;
    if (filtering) {
        members = all.filter(matchDownloadState);
        if (members.length === 0) {
            return '';  // 篩選後無匹配成員,不再顯示該連結。
        }
    } else {
        // 無篩選卡片時按狀態置頂:進行中 > 佇列中 > 已完成/已跳過 > 失敗,使活躍任務集中顯示在最上方。
        members = members.slice().sort(function (a, b) {
            return stateRank(a.state) - stateRank(b.state);
        });
    }
    // 篩選時強制展開,否則結果會被摺疊狀態藏起來。
    var isCollapsed = filtering ? false : (collapsed[key] === undefined ? lastLinkCollapsed : collapsed[key]);
    var stat = groupStat(all, live);
    var html = '<div class="group' + (isCollapsed ? '' : ' open') + '" data-channel="' + escAttr(key) + '" data-level="2">' +
        '<div class="group-head" data-channel="' + escAttr(key) + '">' +
        '<span class="cell-name"><span class="arrow"></span>' +
        '<span class="ficon">🔗</span>' +
        '<span class="fname" title="' + escAttr(link.link) + '">' + esc(link.link) + '</span>' +
        '<span class="gcount">' + (link.queue_total || 0) + ' 條未完成 / 共 ' + (link.total || 0) + ' 條</span></span>' +
        progressCell(link.percent) +
        '<span class="cell-size">' + link.complete + '/' + link.member + '</span>' +
        groupStatCells(stat) +
        linkStatusCell(link) +
        '</div>' +
        '<div class="group-body"' + (isCollapsed ? ' style="display:none"' : '') + '>';
    for (var i = 0; i < members.length; i++) {
        var member = members[i];
        var task = member.state === 'downloading' ? live[member.task_id] : null;
        html += task ? taskRow(task, member, link.link) : memberRow(member, link.link);  // 下載中的成員複用即時進度行。
    }
    if (members.length === 0) {
        html += '<div class="more">該連結暫無訊息。</div>';
    }
    return html + '</div></div>';
}

function groupVisible(node) {
    for (var parent = node.parentNode; parent; parent = parent.parentNode) {
        if (parent.style && parent.style.display === 'none') {
            return false;  // 任一層祖先被摺疊,該分組即不可見。
        }
    }
    return true;
}

function syncHeadLabel() {
    var level = 1;
    var nodes = document.querySelectorAll('#download .group.open');
    for (var i = 0; i < nodes.length; i++) {
        var depth = nodes[i].getAttribute('data-level') === '2' ? 3 : 2;
        if (depth > level && groupVisible(nodes[i])) {
            level = depth;  // 取目前可見的最深層級。
        }
    }
    document.getElementById('headName').querySelector('.htext').textContent = HEAD_LABELS[level - 1];
    document.getElementById('headSize').querySelector('.htext').textContent = SIZE_LABELS[level - 1];  // 分組行是條數,成員行才是位元組。
}

function bindGroups() {
    var nodes = document.querySelectorAll('.group-head');
    for (var i = 0; i < nodes.length; i++) {
        nodes[i].onclick = function () {
            var group = this.parentNode;
            var key = this.getAttribute('data-channel');
            var body = group.querySelector('.group-body');
            var hide = body.style.display !== 'none';  // 目前是展開的,點擊後摺疊。
            body.style.display = hide ? 'none' : '';
            group.className = hide ? 'group' : 'group open';
            collapsed[key] = hide;
            saveState(COLLAPSE_KEY, JSON.stringify(collapsed));  // 記住本次摺疊,重新整理後恢復。
            if (group.getAttribute('data-level') === '2') {
                lastLinkCollapsed = hide;  // 下載頁連結層的手動選擇。
                saveState(LINK_LAST_KEY, hide ? '1' : '0');
            } else if (group.closest('#upload')) {
                lastUploadCollapsed = hide;  // 上載頁頻道層的手動選擇。
                saveState(UPLOAD_LAST_KEY, hide ? '1' : '0');
            }
            syncHeadLabel();
            syncUploadHeads();
        };
    }
}

function syncToggleAll() {
    document.getElementById('toggleAll').textContent = allCollapsed ? '全部展開' : '全部摺疊';
}

function syncToggleUpload() {
    document.getElementById('toggleUpload').textContent = uploadAllCollapsed ? '全部展開' : '全部摺疊';
}

function setAllGroups(selector, hide) {
    var nodes = document.querySelectorAll(selector + ' .group');
    for (var i = 0; i < nodes.length; i++) {
        var key = nodes[i].getAttribute('data-channel');
        var body = nodes[i].querySelector('.group-body');
        body.style.display = hide ? 'none' : '';
        nodes[i].className = hide ? 'group' : 'group open';
        collapsed[key] = hide;
    }
    saveState(COLLAPSE_KEY, JSON.stringify(collapsed));  // 批量摺疊後同樣落盤,重新整理後保持。
    if (selector === '#download') {
        lastLinkCollapsed = hide;  // 批量操作同樣視為一次連結層選擇。
        saveState(LINK_LAST_KEY, hide ? '1' : '0');
    } else {
        lastUploadCollapsed = hide;  // 批量操作同樣視為一次頻道層選擇。
        saveState(UPLOAD_LAST_KEY, hide ? '1' : '0');
    }
}

function toggleAll() {
    allCollapsed = !allCollapsed;
    saveState(ALL_KEY, allCollapsed ? '1' : '0');
    setAllGroups('#download', allCollapsed);
    syncToggleAll();
    syncHeadLabel();
}

function toggleUploadAll() {
    uploadAllCollapsed = !uploadAllCollapsed;
    saveState(UPLOAD_ALL_KEY, uploadAllCollapsed ? '1' : '0');
    setAllGroups('#upload', uploadAllCollapsed);
    syncToggleUpload();
    syncUploadHeads();
}

function saveState(key, value) {
    try {
        localStorage.setItem(key, value);
    } catch (e) {
        // 隱私模式下寫入失敗可忽略。
    }
}

function applySection() {
    var items = document.querySelectorAll('.side-item');
    for (var i = 0; i < items.length; i++) {
        var active = items[i].getAttribute('data-section') === currentSection;
        items[i].className = active ? 'side-item active' : 'side-item';
    }
    var dlWasHidden = document.getElementById('downloadSummary').hidden;
    document.getElementById('downloadSummary').hidden = currentSection !== 'download';
    document.getElementById('uploadSummary').hidden = currentSection !== 'upload';  // 兩個板塊各自獨立的總進度。
    for (i = 0; i < PAGES.length; i++) {
        document.getElementById('page-' + PAGES[i]).hidden = PAGES[i] !== currentSection;
    }
    renderStatus();
    // 下載總進度卡片剛變為可見時,用最新資料強制重繪一次進度列,
    // 避免首屏或切回下載頁時它在隱藏態下渲染、進度列被跳過/未顯示。
    if (currentSection === 'download' && dlWasHidden) {
        refresh(true);
    }
}

function switchSection(name) {
    if (!SECTIONS[name]) {
        name = 'download';
    }
    if (!HAS_BOT && (name === 'upload' || name === 'listener')) {
        name = 'download';
    }
    currentSection = name;
    applySection();
    saveState(SECTION_KEY, currentSection);
    if (currentSection === 'admin') {
        loadAdminControlData();
        connectAdminLogStream();
    } else {
        disconnectAdminLogStream();
    }
}

function applyBotVisibility() {
    if (!HAS_BOT) {
        var items = document.querySelectorAll('.side-item[data-section="upload"], .side-item[data-section="listener"]');
        for (var i = 0; i < items.length; i++) {
            items[i].hidden = true;
        }
    }
}

function applyListenTab() {
    var tabs = document.querySelectorAll('#listenTabs .tab');
    for (var i = 0; i < tabs.length; i++) {
        var active = tabs[i].getAttribute('data-listen') === currentListen;
        tabs[i].className = active ? 'tab active' : 'tab';
    }
    document.getElementById('listenForwardBox').hidden = currentListen !== 'forward';
    document.getElementById('listenDownloadBox').hidden = currentListen !== 'download';
}

function switchListen(name) {
    if (LISTEN_TABS.indexOf(name) === -1) {
        name = LISTEN_TABS[0];
    }
    currentListen = name;
    applyListenTab();
    saveState(LISTEN_KEY, currentListen);
}

function extraText(item) {
    var extra = '';
    if (item.speed) {
        extra += item.speed;
    }
    if (item.remaining) {
        extra += (extra ? ' · 剩餘' : '剩餘') + item.remaining;
    }
    return extra;
}

function renderOverall(summary, taskCount, ids) {
    var data = summary || EMPTY_SUMMARY;
    document.getElementById(ids.fill).style.width = data.percent + '%';
    document.getElementById(ids.percent).textContent = data.percent + '%';
    document.getElementById(ids.info).textContent = data.info;
    document.getElementById(ids.extra).textContent =
        extraText(data) ? extraText(data) : (taskCount ? '正在測速' : '暫無速度');
}

/* 統計卡篩選:點擊後只顯示對應狀態的條目,再次點擊取消。 */
var statFilter = {download: '', upload: ''};

// 篩選後無匹配項時的空態文案,與統計卡片的篩選口徑保持一致。
var DOWNLOAD_EMPTY_TEXT = {
    success: '暫無成功的下載任務。',
    failure: '暫無失敗的下載任務。',
    skip: '暫無跳過的下載任務。',
    active: '暫無下載中的任務。',
    queue: '暫無佇列中的下載任務。'
};
var UPLOAD_EMPTY_TEXT = {
    success: '暫無上載成功的任務。',
    failure: '暫無上載失敗的任務。',
    uploading: '暫無上載中的任務。',
    pending: '暫無佇列中的上載任務。'
};

function statCell(label, value, cls, filter, scope) {
    if (!filter || !scope) {
        return '<div><span>' + label + '</span><b' + (cls ? ' class="' + cls + '"' : '') + '>' +
            value + '</b></div>';
    }
    var active = statFilter[scope] === filter;
    return '<div class="' + (active ? 'active ' : '') + '"' +
        ' data-filter="' + filter + '" data-scope="' + scope + '"' +
        ' title="點擊' + (active ? '取消篩選' : '只查看' + label) + '">' +
        '<span>' + label + '</span><b' + (cls ? ' class="' + cls + '"' : '') + '>' +
        value + '</b></div>';
}

// 判斷下載成員是否命中目前篩選。
function matchDownloadState(member) {
    var state = member.state || 'pending';
    var filter = statFilter.download;
    if (filter === 'success') {
        return state === 'success' || state === 'sent';
    }
    if (filter === 'failure') {
        return state === 'failure';
    }
    if (filter === 'skip') {
        return state === 'skip';
    }
    if (filter === 'active') {
        return state === 'downloading';
    }
    if (filter === 'queue') {
        return state === 'pending';
    }
    return true;
}

/* 統計"佇列中"的成員數:只算排隊中的,不含正在下載的。
   後端 data.queue 是"未完成總數"(含下載中),直接顯示會導致佇列數與進行中重複。 */
function countQueueMembers(links) {
    var total = 0;
    for (var i = 0; i < (links || []).length; i++) {
        var members = links[i].queue || [];
        for (var j = 0; j < members.length; j++) {
            var state = members[j].state || 'pending';
            if (state === 'pending') {
                total += 1;
            }
        }
    }
    return total;
}

// 判斷上載檔案是否命中指定篩選,與 uploadCount 的分類口徑保持一致。
function matchUploadState(file, filter) {
    var state = file.state || 'pending';
    if (filter === 'success') {
        return uploadDone(file);
    }
    if (filter === 'failure') {
        return state === 'failure';
    }
    if (filter === 'uploading') {
        return !uploadDone(file) && state === 'uploading';
    }
    if (filter === 'pending') {
        return !uploadDone(file) && state !== 'failure' && state !== 'uploading';
    }
    return true;  // 檔案總數等:不過濾。
}


function bindStatFilter() {
    document.addEventListener('click', function (event) {
        var cell = event.target && event.target.closest ? event.target.closest('[data-filter]') : null;
        if (!cell) {
            return;
        }
        var scope = cell.getAttribute('data-scope') || 'download';
        var value = cell.getAttribute('data-filter') || '';
        statFilter[scope] = statFilter[scope] === value ? '' : value;  // 再次點擊取消篩選。
        // 篩選狀態屬於介面狀態、不在快照資料裏,必須清空指紋強制重繪,
        // 否則會因"資料未變化"被跳過,導致點擊無反應。
        lastRenderKey = '';
        lastStructKey = null;
        lastUploadStructKey = null;
        refresh();  // 立即按新篩選重繪,無需等待下一次輪詢。
    });
}

function renderStat(id, cells) {
    document.getElementById(id).innerHTML = cells.join('');
}

function renderStatus() {
    // 下載、上載、監聽三個板塊的活躍情況統一顯示在頂欄左側,不再跟隨目前板塊切換。
    var parts = [];
    if (lastDownloadActive) {
        parts.push('下載 ' + lastDownloadActive);
    }
    if (lastUploadActive) {
        parts.push('上載 ' + lastUploadActive);
    }
    if (lastListenCount) {
        parts.push('監聽 ' + lastListenCount);
    }
    var active = parts.length > 0;
    document.getElementById('dot').className = active ? 'dot active' : 'dot';
    document.getElementById('statusText').textContent = active ? parts.join(' · ') : '空閒 · 等待任務';
}

function renderList(data) {
    var live = {};  // 進度列任務ID -> 任務,供下載中的成員複用即時進度。
    var i;
    for (i = 0; i < (data.tasks || []).length; i++) {
        live[data.tasks[i].id] = data.tasks[i];
    }
    var html = '';
    var groups = getChannelGroups(data.links || []);  // 頻道 > 連結 > 下載資訊,兩級可摺疊。
    for (i = 0; i < groups.length; i++) {
        html += channelBlock(groups[i], live);
    }
    /* 空態以"該連結下是否還有成員(含已完成的)"判斷,而非"是否有正在下載的任務"。
       否則全部下載完成後 data.tasks 為空,已完成的成員會被空態整塊隱藏,
       需新建任務才重新出現。 */
    // 處於篩選狀態時,無匹配項應提示具體的篩選條件,而非籠統的"暫無下載任務。"。
    var emptyText = '暫無下載任務。';
    if (statFilter.download) {
        emptyText = DOWNLOAD_EMPTY_TEXT[statFilter.download] || emptyText;
    }
    document.getElementById('download').innerHTML = html ? html : '<div class="empty">' + emptyText + '</div>';
    syncToggleAll();
    bindGroups();  // 頁面渲染完成後統一綁定摺疊事件。
    syncHeadLabel();
}

function listenRow(kind, source, target) {
    var link = target ? source + ' ' + target : source;  // 與後端監聽字典的鍵保持一致。
    var html = '<div class="task-row">' +
        '<span class="cell-name"><span class="ficon">🕵️</span>' +
        '<span class="fname" title="' + escAttr(source) + '">' + esc(source) + '</span></span>';
    if (target) {
        html += '<span class="cell-name"><span class="ficon">➡️</span>' +
            '<span class="fname" title="' + escAttr(target) + '">' + esc(target) + '</span></span>';
    }
    html += '<span class="cell-action"><button class="btn-del" type="button" title="移除該監聽"' +
        ' data-kind="' + kind + '" data-link="' + escAttr(link) + '">✖</button></span>';
    return html + '</div>';
}

function renderListeners(listeners) {
    var data = listeners || {};
    var forward = data.forward || [];
    var download = data.download || [];
    var html = '';
    var i;
    for (i = 0; i < forward.length; i++) {
        html += listenRow('forward', forward[i].source, forward[i].target);
    }
    document.getElementById('listenForward').innerHTML = html ? html : '<div class="empty">暫無監聽轉發。</div>';
    html = '';
    for (i = 0; i < download.length; i++) {
        html += listenRow('download', download[i]);
    }
    document.getElementById('listenDownload').innerHTML = html ? html : '<div class="empty">暫無監聽下載。</div>';
    return forward.length + download.length;
}

/* 與頁面同風格的確認彈出視窗(替代原生 confirm),返回 Promise<boolean>。 */
var confirmResolve = null;

function askConfirm(text, title) {
    return new Promise(function (resolve) {
        document.getElementById('confirmTitle').textContent = title || '確認操作';
        document.getElementById('confirmText').textContent = text || '';
        confirmResolve = resolve;
        document.getElementById('confirmModal').hidden = false;
    });
}

function closeConfirm(result) {
    document.getElementById('confirmModal').hidden = true;
    if (confirmResolve) {
        var resolve = confirmResolve;
        confirmResolve = null;  // 先清空再回調,避免回調內再次觸發時串台。
        resolve(result);
    }
}

/* 複用確認彈出視窗展示提示資訊:只保留"確定"按鈕(替代原生 alert)。 */
function askAlert(text, title) {
    var card = document.querySelector('#confirmModal .modal-card');
    var ok = document.getElementById('confirmOk');
    var cancel = document.getElementById('confirmCancel');
    card.classList.add('alert-card');  // 收窄到與登入卡片一致的比例。
    ok.classList.remove('danger');  // 提示框不是危險操作,確定按鈕不用紅色懸停。
    cancel.hidden = true;  // 提示框無需取消按鈕。
    return askConfirm(text, title).then(function (result) {
        card.classList.remove('alert-card');
        ok.classList.add('danger');  // 恢復,不影響後續"移除監聽"的確認框。
        cancel.hidden = false;
        return result;
    });
}

// ESC 關閉確認/提示彈出視窗,等同取消。
function confirmEscape(event) {
    if (event.key !== 'Escape') {
        return;
    }
    if (document.getElementById('confirmModal').hidden) {
        return;  // 未開啟時不處理,避免影響其它彈出視窗。
    }
    closeConfirm(false);
}

function bindConfirm() {
    document.getElementById('confirmOk').onclick = function () {
        closeConfirm(true);
    };
    document.getElementById('confirmCancel').onclick = function () {
        closeConfirm(false);
    };
    document.getElementById('confirmClose').onclick = function () {
        closeConfirm(false);
    };
    document.getElementById('confirmModal').onclick = function (event) {
        if (event.target === this) {
            closeConfirm(false);  // 點擊遮罩空白處等同取消。
        }
    };
    document.addEventListener('keydown', confirmEscape);
}

/* 登入卡片:替代瀏覽器原生的 Basic 認證彈出視窗,沿用頁面毛玻璃風格。 */

/* 未勾選"30天內免登入"時,令牌只存放在 sessionStorage:
   關閉標籤頁即被清空,下次必須重新登入。
   Cookie 無法做到"關閉標籤頁即失效"(會話Cookie要整個瀏覽器退出才清),
   所以未勾選時伺服器端不下發Cookie,改由前端持令牌隨請求帶來。 */
function setSessionToken(token) {
    try {
        if (token) {
            sessionStorage.setItem('trmd_token', token);
        } else {
            sessionStorage.removeItem('trmd_token');
        }
    } catch (e) {
        // 隱私模式等 sessionStorage 不可用的場景直接忽略。
    }
}

function authHeaders() {
    var token = '';
    try {
        token = sessionStorage.getItem('trmd_token') || '';
    } catch (e) {
        token = '';
    }
    return token ? {Authorization: 'Bearer ' + token} : {};
}

/* 登出:通知伺服器端輪換令牌並清除Cookie,然後回到登入卡片。 */
async function logout() {
    var dropdown = document.getElementById('menuDropdown');
    if (dropdown) {
        dropdown.hidden = true;  // 先收起選單,避免與詢問框疊加。
    }
    var ok = await askConfirm('退出後需要重新輸入帳號密碼。', '登出');
    if (!ok) {
        return;
    }
    try {
        await fetch('/api/logout', {
            method: 'POST',
            headers: Object.assign({'Content-Type': 'application/json'}, authHeaders())
        });
    } catch (e) {
        // 請求失敗也要在本機清理,避免介面停留在已登入狀態。
    }
    setSessionToken('');  // 清掉未勾選免登入時的臨時令牌。
    openLogin();  // 重新彈出登入卡片並隱藏頁面內容。
}

function initLogout() {
    if (document.body.getAttribute('data-auth') !== '1') {
        return;  // 未設定密碼時無需登出入口。
    }
    var btn = document.getElementById('btnLogout');
    if (!btn) {
        return;
    }
    btn.hidden = false;
    btn.onclick = logout;
}

var loginShown = false;

function openLogin() {
    if (loginShown) {
        return;  // 每秒輪詢都會觸發,已展示時不再重複開啟。
    }
    loginShown = true;
    document.getElementById('loginPass').value = '';
    document.getElementById('loginModal').hidden = false;
    document.body.classList.add('logged-out');  // 未登入時隱藏頁面卡片,只留漸變背景。
    var user = document.getElementById('loginUser');
    if (user.value) {
        document.getElementById('loginPass').focus();
    } else {
        user.focus();
    }
}

function closeLogin() {
    loginShown = false;
    document.getElementById('loginModal').hidden = true;
    document.body.classList.remove('logged-out');  // 恢復頁面內容。
}

async function submitLogin() {
    var remember = document.getElementById('loginRemember').checked;
    try {
        var res = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                username: document.getElementById('loginUser').value,
                password: document.getElementById('loginPass').value,
                remember: document.getElementById('loginRemember').checked
            })
        });
        var data = await res.json();
        if (!data.status) {
            await askAlert('帳號或密碼不正確，請重新輸入。', '登入失敗');
            return;
        }
        // 勾選"30天內免登入"時伺服器端已下發Cookie;未勾選則把令牌留在本標籤頁。
        setSessionToken(remember ? '' : (data.token || ''));
        // 清空指紋,確保登入後必定重繪一次並重建列表(否則資料未變會被跳過)。
        lastRenderKey = '';
        lastStructKey = null;
        lastUploadStructKey = null;
        closeLogin();
        refresh();
    } catch (e) {
        await askAlert('無法連執行緒式,請稍後重試。', '登入失敗');
    }
}

function bindLogin() {
    document.getElementById('loginSubmit').onclick = submitLogin;
    var user = document.getElementById('loginUser');
    var pass = document.getElementById('loginPass');
    user.onkeydown = function (event) {
        if (event.key === 'Enter') {
            pass.focus();
        }
    };
    pass.onkeydown = function (event) {
        if (event.key === 'Enter') {
            submitLogin();
        }
    };
    // 每輸入一個字元就推進一格漸變,複用官方"發送訊息時推進"的同一套邏輯。
    var advance = function () {
        if (!bgCtx) {
            return;  // 漸變背景未初始化成功時跳過。
        }
        bgAdvancePosition();
    };
    user.addEventListener('input', advance);
    pass.addEventListener('input', advance);
}

var removingListener = {};  // 正在等待確認或移除中的監聽,避免重複點擊被處理多次。

async function removeListener(kind, link) {
    if (!link || removingListener[link]) {
        return;  // 同一監聽已在確認或處理中,忽略重複點擊。
    }
    removingListener[link] = true;
    var ok = await askConfirm('確定移除該監聽?\n' + link, '移除監聽');
    if (!ok) {
        delete removingListener[link];
        return;
    }
    try {
        var res = await fetch('/api/listener/remove', {
            method: 'POST',
            headers: Object.assign({'Content-Type': 'application/json'}, authHeaders()),
            body: JSON.stringify({kind: kind, link: link})
        });
        var data = await res.json();
        if (!data.status) {
            window.alert('移除失敗:' + (data.e_code || '未知錯誤。'));
        }
    } catch (e) {
        window.alert('移除失敗:無法連執行緒式。');
    }
    delete removingListener[link];
    refresh();  // 移除後立即重新整理,無需等待下一次輪詢。
}

async function adminRequest(path, payload) {
    var response = await fetch(path, {
        method: payload === undefined ? 'GET' : 'POST',
        cache: 'no-store',
        headers: Object.assign({'Content-Type': 'application/json'}, authHeaders()),
        body: payload === undefined ? undefined : JSON.stringify(payload)
    });
    if (response.status === 401) {
        openLogin();
        throw new Error('登入已失效，請重新登入。');
    }
    var data = await response.json();
    if (!response.ok || !data.status) {
        throw new Error(data.e_code || '管理操作失敗。');
    }
    return data;
}

function renderService(service) {
    if (!service || !service.status) {
        return;
    }
    var badge = document.getElementById('adminServiceState');
    badge.textContent = service.stopping ? '正在安全停止' : (service.running ? '執行中' : '尚未執行');
    document.getElementById('adminBotState').textContent = service.bot_running ? '已連線' : '未連線';
    document.getElementById('adminDownloadState').textContent = service.downloads_active;
    document.getElementById('adminUploadState').textContent = service.uploads_active;
    document.getElementById('adminBindState').textContent = service.bind_address + ':' + service.port;
    document.getElementById('adminReconnectBot').disabled = service.stopping || !HAS_BOT;
    document.getElementById('adminShutdown').disabled = service.stopping;
}

var adminSettingsLoaded = false;

async function loadAdminSettings() {
    try {
        var data = await adminRequest('/api/settings');
        var config = data.config || {};
        var proxy = config.proxy || {};
        document.getElementById('settingApiId').value = config.api_id || '';
        document.getElementById('settingSessionDirectory').value = config.session_directory || '';
        document.getElementById('settingSaveDirectory').value = config.save_directory || '';
        document.getElementById('settingTempDirectory').value = config.temp_directory || '';
        document.getElementById('settingDownloadTasks').value = (config.max_tasks || {}).download || 1;
        document.getElementById('settingUploadTasks').value = (config.max_tasks || {}).upload || 1;
        document.getElementById('settingDownloadRetries').value = (config.max_retries || {}).download || 0;
        document.getElementById('settingUploadRetries').value = (config.max_retries || {}).upload || 0;
        document.getElementById('settingLinks').value = config.links || '';
        document.getElementById('settingAutoShutdown').value = String(Boolean(config.is_shutdown));
        document.getElementById('settingProxyEnabled').value = String(Boolean(proxy.enable_proxy));
        document.getElementById('settingProxyScheme').value = proxy.scheme || '';
        document.getElementById('settingProxyHost').value = proxy.hostname || '';
        document.getElementById('settingProxyPort').value = proxy.port || '';
        document.getElementById('settingProxyUser').value = proxy.username || '';
        document.getElementById('settingApiHashHint').textContent = data.secrets.api_hash ? '（已設定）' : '（未設定）';
        document.getElementById('settingBotTokenHint').textContent = data.secrets.bot_token ? '（已設定）' : '（未設定）';
        document.getElementById('settingProxyPasswordHint').textContent = data.secrets.proxy_password ? '（已設定）' : '（未設定）';
        document.getElementById('settingApiHash').value = '';
        document.getElementById('settingBotToken').value = '';
        document.getElementById('settingProxyPassword').value = '';
        var types = config.download_type || [];
        var boxes = document.querySelectorAll('input[name="downloadType"]');
        for (var i = 0; i < boxes.length; i++) {
            boxes[i].checked = types.indexOf(boxes[i].value) !== -1;
        }
        document.getElementById('adminSettingsState').textContent = '設定已載入';
        adminSettingsLoaded = true;
    } catch (e) {
        document.getElementById('adminSettingsState').textContent = '載入失敗';
        document.getElementById('adminSettingsFeedback').textContent = e.message;
    }
}

var adminLogAbort = null;
var adminLogRetryTimer = 0;
var adminLogLastEventId = 0;

function prettyBytes(value) {
    return value === null || value === undefined ? '不支援' : sizeText(value);
}

async function loadAdminControlData() {
    try {
        var results = await Promise.all([
            adminRequest('/api/admin/sessions'),
            adminRequest('/api/admin/system'),
            adminRequest('/api/admin/queue')
        ]);
        var sessions = results[0];
        var account = sessions.account || {};
        var sessionNames = (sessions.sessions || []).map(function (item) {
            return esc(item.name) + (item.active ? '（使用中）' : '');
        });
        document.getElementById('adminSessions').innerHTML =
            '<div>帳號：' + esc(account.first_name || '未登入') +
            (account.username ? ' (@' + esc(account.username) + ')' : '') +
            (account.id ? ' · ID ' + esc(account.id) : '') + '</div>' +
            '<div>連線狀態：' + (account.connected ? '已連線' : '未連線') + '</div>' +
            '<div>Session 檔案：' + (sessionNames.length ? sessionNames.join('、') : '找不到 .session 檔案') + '</div>';

        var system = results[1];
        var disk = system.disk || {};
        var metrics = [
            ['作業系統', system.platform || '—'],
            ['CPU load (1m)', system.cpu_load_1m === null ? '不支援' : Number(system.cpu_load_1m).toFixed(2)],
            ['程序 Peak RSS', prettyBytes(system.process_peak_rss)],
            ['系統記憶體', prettyBytes(system.system_memory_total)],
            ['程序 Peak RSS / 系統記憶體', system.process_peak_memory_percent === null ? '不支援' : system.process_peak_memory_percent + '%'],
            ['下載磁碟可用空間', prettyBytes(disk.free)]
        ];
        document.getElementById('adminResources').innerHTML = metrics.map(function (item) {
            return '<div><span>' + esc(item[0]) + '</span><strong>' + esc(item[1]) + '</strong></div>';
        }).join('');
        document.getElementById('adminResourceUpdated').textContent =
            '更新於 ' + new Date(system.timestamp * 1000).toLocaleTimeString();
        document.getElementById('adminQueueOrder').value = (results[2].links || []).join('\n');
    } catch (error) {
        document.getElementById('adminResourceUpdated').textContent = '讀取失敗';
    }
}

async function loadConfigYaml() {
    var feedback = document.getElementById('adminYamlFeedback');
    try {
        var result = await adminRequest('/api/admin/config');
        document.getElementById('adminConfigYaml').value = result.config_yaml || '';
        feedback.textContent = '設定已載入';
    } catch (error) {
        feedback.textContent = '載入失敗：' + error.message;
    }
}

async function saveConfigYaml() {
    var feedback = document.getElementById('adminYamlFeedback');
    feedback.textContent = '正在驗證並儲存…';
    try {
        var result = await adminRequest('/api/admin/config', {
            config_yaml: document.getElementById('adminConfigYaml').value
        });
        feedback.textContent = result.restart_required.length ?
            '已儲存；需重新啟動後生效：' + result.restart_required.join('、') :
            '設定已儲存並即時套用。';
        await loadAdminSettings();
    } catch (error) {
        feedback.textContent = '儲存失敗：' + error.message;
    }
}

async function saveQueueOrder() {
    var feedback = document.getElementById('adminQueueFeedback');
    var links = document.getElementById('adminQueueOrder').value.split(/\r?\n/)
        .map(function (link) { return link.trim(); }).filter(Boolean);
    feedback.textContent = '正在套用…';
    try {
        await adminRequest('/api/admin/download/reorder', {links: links});
        feedback.textContent = '佇列順序已更新';
        await refresh(true);
    } catch (error) {
        feedback.textContent = '更新失敗：' + error.message;
    }
}

function disconnectAdminLogStream() {
    if (adminLogRetryTimer) {
        clearTimeout(adminLogRetryTimer);
        adminLogRetryTimer = 0;
    }
    if (adminLogAbort) {
        adminLogAbort.abort();
        adminLogAbort = null;
    }
    document.getElementById('adminLogState').textContent = '未連線';
}

function scheduleAdminLogReconnect(controller, state) {
    if (controller.signal.aborted) {
        return;
    }
    state.textContent = '串流中斷，重新連線中';
    adminLogRetryTimer = setTimeout(function () {
        if (currentSection === 'admin') {
            connectAdminLogStream();
        }
    }, 2000);
}

async function connectAdminLogStream() {
    disconnectAdminLogStream();
    adminLogAbort = new AbortController();
    var controller = adminLogAbort;
    var state = document.getElementById('adminLogState');
    var output = document.getElementById('adminLogOutput');
    state.textContent = '連線中';
    try {
        var response = await fetch('/api/events', {
            cache: 'no-store',
            headers: Object.assign(authHeaders(), {'Last-Event-ID': String(adminLogLastEventId)}),
            signal: controller.signal
        });
        if (response.status === 401) {
            openLogin();
            return;
        }
        if (!response.ok || !response.body) {
            throw new Error('SSE 連線失敗：HTTP ' + response.status);
        }
        state.textContent = '即時串流中';
        var reader = response.body.getReader();
        var decoder = new TextDecoder();
        var buffer = '';
        while (!controller.signal.aborted) {
            var chunk = await reader.read();
            if (chunk.done) {
                break;
            }
            buffer += decoder.decode(chunk.value, {stream: true});
            var frames = buffer.split('\n\n');
            buffer = frames.pop() || '';
            frames.forEach(function (frame) {
                var lines = frame.split(/\r?\n/);
                var eventName = 'message';
                var data = '';
                lines.forEach(function (line) {
                    if (line.indexOf('id:') === 0) {
                        adminLogLastEventId = Number(line.slice(3).trim()) || adminLogLastEventId;
                    } else if (line.indexOf('event:') === 0) {
                        eventName = line.slice(6).trim();
                    } else if (line.indexOf('data:') === 0) {
                        data += line.slice(5).trim();
                    }
                });
                if (eventName === 'log' && data) {
                    try {
                        var item = JSON.parse(data);
                        output.textContent += item.message + '\n';
                        var logLines = output.textContent.split('\n');
                        if (logLines.length > 250) {
                            output.textContent = logLines.slice(-250).join('\n');
                        }
                        output.scrollTop = output.scrollHeight;
                    } catch (error) {
                        // Ignore malformed individual log events and keep the stream alive.
                    }
                }
            });
        }
        scheduleAdminLogReconnect(controller, state);
    } catch (error) {
        if (!controller.signal.aborted) {
            scheduleAdminLogReconnect(controller, state);
        }
    }
}

function selectedDownloadTypes() {
    var boxes = document.querySelectorAll('input[name="downloadType"]:checked');
    var values = [];
    for (var i = 0; i < boxes.length; i++) {
        values.push(boxes[i].value);
    }
    return values;
}

async function saveAdminSettings(event) {
    event.preventDefault();
    var settings = {
        api_id: Number(document.getElementById('settingApiId').value),
        api_hash: document.getElementById('settingApiHash').value,
        bot_token: document.getElementById('settingBotToken').value,
        session_directory: document.getElementById('settingSessionDirectory').value,
        save_directory: document.getElementById('settingSaveDirectory').value,
        temp_directory: document.getElementById('settingTempDirectory').value,
        links: document.getElementById('settingLinks').value,
        is_shutdown: document.getElementById('settingAutoShutdown').value === 'true',
        download_type: selectedDownloadTypes(),
        max_tasks: {
            download: Number(document.getElementById('settingDownloadTasks').value),
            upload: Number(document.getElementById('settingUploadTasks').value)
        },
        max_retries: {
            download: Number(document.getElementById('settingDownloadRetries').value),
            upload: Number(document.getElementById('settingUploadRetries').value)
        },
        proxy: {
            enable_proxy: document.getElementById('settingProxyEnabled').value === 'true',
            scheme: document.getElementById('settingProxyScheme').value,
            hostname: document.getElementById('settingProxyHost').value,
            port: document.getElementById('settingProxyPort').value ?
                Number(document.getElementById('settingProxyPort').value) : null,
            username: document.getElementById('settingProxyUser').value,
            password: document.getElementById('settingProxyPassword').value
        }
    };
    var feedback = document.getElementById('adminSettingsFeedback');
    feedback.textContent = '正在儲存…';
    try {
        var result = await adminRequest('/api/admin/settings', {settings: settings});
        await loadAdminSettings();
        feedback.textContent = result.restart_required.length ?
            '已儲存；以下設定需重新啟動後生效：' + result.restart_required.join('、') :
            '設定已儲存並即時套用。';
    } catch (e) {
        feedback.textContent = '儲存失敗：' + e.message;
    }
}

async function controlTask(kind, action, target) {
    if (action === 'cancel' && !window.confirm('確定要取消此項工作嗎？')) {
        return;
    }
    var path = kind === 'download' ? '/api/admin/download/control' : '/api/admin/upload/control';
    var payload = kind === 'download' ?
        {link: target.getAttribute('data-link'), message_id: target.getAttribute('data-message-id'), action: action} :
        {task_id: target.getAttribute('data-task-id'), action: action};
    try {
        await adminRequest(path, payload);
        await refresh(true);
    } catch (e) {
        window.alert('操作失敗：' + e.message);
    }
}

function bindAdmin() {
    document.getElementById('adminDownloadForm').addEventListener('submit', async function (event) {
        event.preventDefault();
        var input = document.getElementById('adminDownloadLink');
        try {
            await adminRequest('/api/admin/download/add', {link: input.value.trim()});
            input.value = '';
            await refresh(true);
        } catch (e) {
            window.alert('加入下載失敗：' + e.message);
        }
    });
    document.getElementById('adminSettingsForm').addEventListener('submit', saveAdminSettings);
    document.getElementById('adminForwardForm').addEventListener('submit', async function (event) {
        event.preventDefault();
        var submit = document.getElementById('adminForwardSubmit');
        var feedback = document.getElementById('adminForwardFeedback');
        submit.disabled = true;
        feedback.textContent = '轉發工作執行中…';
        try {
            var result = await adminRequest('/api/admin/forward', {
                origin_link: document.getElementById('adminForwardOrigin').value.trim(),
                target_link: document.getElementById('adminForwardTarget').value.trim(),
                start_id: Number(document.getElementById('adminForwardStart').value),
                end_id: Number(document.getElementById('adminForwardEnd').value)
            });
            feedback.textContent = '轉發工作已加入執行佇列…';
            var job;
            do {
                await new Promise(function (resolve) { setTimeout(resolve, 1000); });
                job = await adminRequest('/api/admin/forward/status?job_id=' + encodeURIComponent(result.job_id));
            } while (job.state === 'pending' || job.state === 'running');
            if (job.state === 'completed') {
                feedback.textContent = job.result.message;
            } else {
                feedback.textContent = '轉發失敗：' + ((job.result || {}).e_code || '未知錯誤。');
            }
        } catch (error) {
            feedback.textContent = '轉發失敗：' + error.message;
        } finally {
            submit.disabled = false;
        }
    });
    document.getElementById('adminRefreshSessions').addEventListener('click', loadAdminControlData);
    document.getElementById('adminLoadYaml').addEventListener('click', loadConfigYaml);
    document.getElementById('adminSaveYaml').addEventListener('click', saveConfigYaml);
    document.getElementById('adminSaveQueueOrder').addEventListener('click', saveQueueOrder);
    document.getElementById('page-download').addEventListener('click', function (event) {
        var target = event.target.closest('[data-task-kind="download"]');
        if (target) {
            controlTask('download', target.getAttribute('data-action'), target);
        }
    });
    document.getElementById('page-upload').addEventListener('click', function (event) {
        var target = event.target.closest('[data-task-kind="upload"]');
        if (target) {
            controlTask('upload', target.getAttribute('data-action'), target);
        }
    });
    document.getElementById('adminReconnectBot').addEventListener('click', async function () {
        try {
            var result = await adminRequest('/api/admin/service/reconnect', {});
            window.alert(result.message || '機械人已重新連線。');
            await refresh(true);
        } catch (e) {
            window.alert('重新連線失敗：' + e.message);
        }
    });
    document.getElementById('adminShutdown').addEventListener('click', async function () {
        if (!window.confirm('程式會等待目前的下載與上載工作完成後安全停止，確定繼續？')) {
            return;
        }
        try {
            var result = await adminRequest('/api/admin/service/shutdown', {});
            window.alert(result.message || '已送出安全停止要求。');
            await refresh(true);
        } catch (e) {
            window.alert('停止程式失敗：' + e.message);
        }
    });
}

function uploadDone(file) {
    return file.state === 'success' || file.state === 'sent';
}

// 無篩選時用於把活躍任務置頂的排序權重:進行中(downloading/uploading) > 佇列中(pending) > 已完成/已跳過(success/sent/skip) > 失敗(failure)。
// 排序在數組副本上進行,不改動後端快照資料,且為穩定排序,同權重的任務保持原有順序。
function stateRank(state) {
    if (state === 'downloading' || state === 'uploading') {
        return 0;
    }
    if (state === 'pending') {
        return 1;
    }
    if (state === 'success' || state === 'sent' || state === 'skip' || state === 'cancelled') {
        return 2;
    }
    return 3;  // failure 等失敗狀態置底。
}

function getUploadGroups(tasks) {
    var groups = [];  // 按頻道分組上載任務,保持頻道首次出現的順序。
    var index = {};
    var i;
    for (i = 0; i < tasks.length; i++) {
        var channel = tasks[i].channel || UNGROUPED_NAME;
        if (index[channel] === undefined) {
            index[channel] = groups.length;
            groups.push({channel: channel, name: tasks[i].chat || channel, files: []});
        }
        groups[index[channel]].files.push(tasks[i]);
    }
    for (i = 0; i < groups.length; i++) {
        var group = groups[i];
        group.count = group.files.length;
        group.complete = 0;
        group.failed = 0;
        group.cancelled = 0;
        group.total_byte = 0;
        group.done_byte = 0;
        for (var j = 0; j < group.files.length; j++) {
            var file = group.files[j];
            if (file.state === 'failure') {
                group.failed += 1;
                continue;  // 失敗檔案不計入分組進度基數,避免拖低進度。
            }
            if (file.state === 'cancelled') {
                group.cancelled += 1;
                continue;
            }
            var size = Number(file.size_byte) || 0;
            group.total_byte += size;
            if (uploadDone(file)) {
                group.complete += 1;
                group.done_byte += size;
            } else {
                group.done_byte += Math.min(Number(file.completed) || 0, size);  // 上載中的檔案按已傳位元組計入。
            }
        }
        group.percent = group.total_byte ?
            Math.round(group.done_byte / group.total_byte * 1000) / 10 : 0;
        group.stat = groupStat(group.files, {});
    }
    return groups;
}

function uploadSummary(tasks) {
    var total = 0;  // 總量只統計未失敗的上載檔案,失敗檔案退出進度基數。
    var done = 0;
    var speed = 0;
    for (var i = 0; i < tasks.length; i++) {
        var file = tasks[i];
        if (file.state === 'failure' || file.state === 'cancelled') {
            continue;  // 失敗檔案不再計入總量與速度,避免進度被拉低。
        }
        var size = Number(file.size_byte) || 0;
        total += size;
        if (uploadDone(file)) {
            done += size;
        } else if (file.state === 'uploading') {
            done += Math.min(Number(file.completed) || 0, size);  // 上載中的檔案按已傳位元組計入。
        }
        speed += Number(file.speed_value) || 0;
    }
    var remaining = speed && total > done ? (total - done) / speed : null;
    return {
        percent: total ? Math.round(done / total * 1000) / 10 : 0,
        info: sizeText(done) + '/' + sizeText(total),
        speed: speed ? sizeText(speed) + '/s' : '',
        remaining: remaining === null ? '' : secondsText(remaining)
    };
}

function uploadCount(tasks) {
    var count = {success: 0, failure: 0, cancelled: 0, uploading: 0, pending: 0, active: 0};
    for (var i = 0; i < tasks.length; i++) {
        var state = tasks[i].state;
        if (state === 'failure') {
            count.failure += 1;
        } else if (state === 'cancelled') {
            count.cancelled += 1;
        } else if (uploadDone(tasks[i])) {
            count.success += 1;
        } else {
            count.active += 1;
            if (state === 'uploading') {
                count.uploading += 1;
            } else {
                count.pending += 1;
            }
        }
    }
    return count;
}

function uploadRow(file) {
    var state = file.state || 'pending';
    var text = UPLOAD_TEXT[state] || '佇列中';
    var cls = UPLOAD_CLASS[state] || 'status-pending';
    var progress;
    if (uploadDone(file)) {
        progress = progressCell(100);
    } else if (state === 'uploading') {
        progress = progressCell(file.percent || 0);
    } else {
        progress = '<span class="cell-progress"><span class="pct' +
            (state === 'pending' ? ' pending' : '') + '">' + text + '</span></span>';
    }
    // data-upload-id 供"上載列表結構未變時就地更新進度",避免每秒整表重建。
    return '<div class="task-row member-row" data-upload-id="' +
        escAttr(file.task_id || file.path || file.file) + '">' +
        '<span class="cell-name"><span class="ficon">' + (UPLOAD_ICON[state] || '⏳') + '</span>' +
        '<span class="fname" title="' + escAttr(file.path || file.file) + '">' + esc(file.path || file.file) + '</span></span>' +
        progress +
        '<span class="cell-size">' + dash(file.size) + '</span>' +
        '<span class="cell-speed">' + dash(file.speed) + '</span>' +
        '<span class="cell-remain">' + dash(file.remaining) + '</span>' +
        '<span class="cell-status ' + cls + '" title="' + escAttr(file.error) + '">' + text +
        taskActions(state, '', '', 'upload', file.control_id, file.pause_requested, file.cancel_requested) +
        '</span>' +
        '</div>';
}

function uploadStatusCell(group) {
    if (group.failed) {
        return '<span class="cell-status status-failed">失敗 ' + group.failed + ' 個</span>';
    }
    if (group.cancelled === group.count) {
        return '<span class="cell-status status-skip">已取消</span>';
    }
    if (group.complete === group.count) {
        return '<span class="cell-status status-done">已完成</span>';
    }
    return '<span class="cell-status status-running">上載中</span>';
}

function uploadBlock(group) {
    var key = 'upload:' + group.channel;
    var filtering = Boolean(statFilter.upload);
    var files = group.files;
    if (filtering) {
        files = files.filter(function (file) {
            return matchUploadState(file, statFilter.upload);
        });
        if (files.length === 0) {
            return '';  // 篩選後無匹配檔案,不再顯示該分組。
        }
    } else {
        // 無篩選卡片時按狀態置頂:進行中 > 佇列中 > 已完成/已跳過 > 失敗,使活躍任務集中顯示在最上方。
        files = files.slice().sort(function (a, b) {
            return stateRank(a.state) - stateRank(b.state);
        });
    }
    // 篩選時強制展開,否則結果會被摺疊狀態藏起來。
    var isCollapsed = filtering ? false : (collapsed[key] === undefined ? lastUploadCollapsed : collapsed[key]);
    var html = '<div class="group' + (isCollapsed ? '' : ' open') + '" data-channel="' + escAttr(key) + '" data-level="1">' +
        '<div class="group-head" data-channel="' + escAttr(key) + '">' +
        '<span class="cell-name"><span class="arrow"></span>' +
        '<span class="ficon">📺</span>' +
        '<span class="gname" title="' + escAttr(group.name) + '">' + esc(group.name) + '</span>' +
        '<span class="gcount">' + group.count + ' 個檔案</span></span>' +
        progressCell(group.percent) +
        '<span class="cell-size">' + group.complete + '/' + group.count + '</span>' +
        groupStatCells(group.stat) +
        uploadStatusCell(group) +
        '</div>' +
        '<div class="group-body"' + (isCollapsed ? ' style="display:none"' : '') + '>';
    for (var i = 0; i < files.length; i++) {
        html += uploadRow(files[i]);
    }
    return html + '</div></div>';
}

function uploadList(tasks) {
    if (tasks.length === 0) {
        return '<div class="empty">暫無上載任務。</div>';
    }
    var html = '';
    var groups = getUploadGroups(tasks);  // 頻道 > 檔案完整路徑,一級可摺疊。
    for (var i = 0; i < groups.length; i++) {
        html += uploadBlock(groups[i]);
    }
    if (statFilter.upload && !html) {
        return '<div class="empty">' + (UPLOAD_EMPTY_TEXT[statFilter.upload] || '沒有符合條件的檔案。') + '</div>';
    }
    return html;
}

function syncUploadHeads() {
    var list = document.getElementById('upload');
    if (!list || !list.parentNode) {
        return;
    }
    var head = list.parentNode.querySelector('.list-head');
    var level = 1;
    var nodes = list.querySelectorAll('.group.open');
    for (var i = 0; i < nodes.length; i++) {
        if (groupVisible(nodes[i])) {
            level = 2;  // 有任意頻道展開時,最內層即為檔案行。
            break;
        }
    }
    head.querySelector('.h-name .htext').textContent = UPLOAD_HEAD_NAME[level - 1];
    head.querySelector('.h-size .htext').textContent = UPLOAD_HEAD_SIZE[level - 1];
}

function renderUpload(uploads) {
    var count = uploadCount(uploads);
    document.getElementById('badgeUpload').textContent = count.active;
    /* 只有結構變化(檔案增減/狀態改變)才重建 DOM,否則僅就地更新進度,避免每秒整表重建。 */
    var uploadKey = uploadStructKey(uploads);
    if (uploadKey !== lastUploadStructKey) {
        lastUploadStructKey = uploadKey;
        /* 空態以"是否存在上載檔案(含已完成的)"判斷,而非"是否有活躍任務"。
           否則全部上載結束後 count.active 為 0,已完成的檔案會被空態整塊隱藏,
           需新建任務才重新出現。 */
        // 處於篩選狀態時,無匹配項應提示具體的篩選條件,而非籠統的"暫無上載任務。"。
        var uploadEmpty = '暫無上載任務。';
        if (statFilter.upload) {
            uploadEmpty = UPLOAD_EMPTY_TEXT[statFilter.upload] || uploadEmpty;
        }
        document.getElementById('upload').innerHTML = uploads.length > 0 ? uploadList(uploads) : '<div class="empty">' + uploadEmpty + '</div>';
        syncToggleUpload();
        syncUploadHeads();
        bindGroups();  // 上載列表渲染完成後統一綁定摺疊事件。
    } else {
        updateUploadRows(uploads);
    }
    renderOverall(uploadSummary(uploads), count.active, SUMMARY_IDS.upload);
    lastUploadFinished = count.success + count.failure;
    renderStat('uploadStat', [
        statCell('成功', count.success, 'ok', 'success', 'upload'),
        statCell('失敗', count.failure, 'bad', 'failure', 'upload'),
        statCell('上載中', count.uploading, '', 'uploading', 'upload'),
        statCell('佇列', count.pending, 'skip', 'pending', 'upload')
    ]);
    return count.active;
}

var lastRenderKey = '';  // 上次渲染的資料指紋,用於跳過無變化的重繪。
var lastStructKey = null;  // 列表結構指紋,結構不變則不重建列表 DOM。(初始為 null 而非 '',否則空連結時 structKeyOf 返回 '' 會被誤判為"未變化",導致首次渲染跳過 renderList、列表區只剩表頭)
var lastUploadStructKey = null;  // 上載列表結構指紋,同上。

/* 輪詢間隔(毫秒)。預設 1 秒。
   若設備壓力明顯,調大到 2000~3000 可直接砍掉一半以上的拉取與渲染開銷,
   代價只是數字更新變慢。 */
var POLL_INTERVAL_MS = 1000;

/* 上載列表結構指紋:檔案路徑 + 狀態,不含進度/速度等每秒變化的數值。 */
function uploadStructKey(uploads) {
    var parts = [];
    for (var i = 0; i < (uploads || []).length; i++) {
        parts.push((uploads[i].path || uploads[i].file || '') + '|' + uploads[i].state);
    }
    return parts.join(';');
}

/* 上載列表結構未變時,只就地更新各行的進度與速度文字,不重建 DOM。 */
function updateUploadRows(uploads) {
    var live = {};
    var i;
    for (i = 0; i < (uploads || []).length; i++) {
        live[String(uploads[i].task_id || uploads[i].path || uploads[i].file)] = uploads[i];
    }
    var rows = document.querySelectorAll('#upload [data-upload-id]');
    for (i = 0; i < rows.length; i++) {
        var row = rows[i];
        var file = live[row.getAttribute('data-upload-id')];
        if (!file) {
            continue;
        }
        var percent = uploadDone(file) ? 100 : (Number(file.percent) || 0);
        var fill = row.querySelector('.fill');
        if (fill) {
            fill.style.width = percent + '%';  // 桌面端橫向條。
            var cell = fill.closest('.cell-progress');  // 手機端圓環依賴 --p,需同步更新。
            if (cell) {
                cell.style.setProperty('--p', percent + '%');
            }
        }
        var pct = row.querySelector('.pct');
        if (pct && fill) {
            pct.textContent = percent + '%';
        }
        var speed = row.querySelector('.cell-speed');
        if (speed) {
            speed.textContent = dash(file.speed);
        }
        var remain = row.querySelector('.cell-remain');
        if (remain) {
            remain.textContent = dash(file.remaining);
        }
    }
}

/* 列表結構指紋:頻道、連結、成員名稱與狀態。
   刻意不包含進度/速度等每秒變化的數值,否則每次輪詢都會觸發重建。 */
function structKeyOf(data) {
    var parts = [];
    var links = data.links || [];
    for (var i = 0; i < links.length; i++) {
        var members = links[i].queue || [];
        var sig = [];
        for (var j = 0; j < members.length; j++) {
            sig.push(members[j].name + '|' + members[j].state);
        }
        parts.push(links[i].link + '#' + sig.join(','));
    }
    return parts.join(';');
}

/* 結構未變化時,只就地更新"正在下載"的行:
   改寬度與文字,避免整表 DOM 重建(僅這幾行重排)。 */
function updateTaskRows(data) {
    var tasks = data.tasks || [];
    var live = {};
    var i;
    for (i = 0; i < tasks.length; i++) {
        live[String(tasks[i].id)] = tasks[i];
    }
    var rows = document.querySelectorAll('#download [data-task-id]');
    for (i = 0; i < rows.length; i++) {
        var row = rows[i];
        var task = live[row.getAttribute('data-task-id')];
        if (!task) {
            continue;  // 該任務已結束,等結構變化時整行替換。
        }
        var fill = row.querySelector('.fill');
        if (fill) {
            var pct = task.percent + '%';
            fill.style.width = pct;  // 桌面端橫向條。
            var cell = fill.closest('.cell-progress');  // 手機端圓環依賴 --p,需同步更新。
            if (cell) {
                cell.style.setProperty('--p', pct);
            }
        }
        var pct = row.querySelector('.pct');
        if (pct) {
            pct.textContent = task.percent + '%';
        }
        var size = row.querySelector('.cell-size');
        if (size) {
            size.textContent = dash(task.info);
        }
        var speed = row.querySelector('.cell-speed');
        if (speed) {
            speed.textContent = dash(task.speed);
        }
        var remain = row.querySelector('.cell-remain');
        if (remain) {
            remain.textContent = dash(task.remaining);
        }
    }
}

function render(data, force) {
    /* 資料未變化時直接跳過整頁重繪。
       原本每秒都會重建整個列表 DOM,導致所有毛玻璃圖層失效並重新採樣背景,
       這是 GPU 佔用的主要來源。空閒(無任務變化)時可完全省掉這部分開銷。 */
    var key = JSON.stringify(data);
    if (!force && key === lastRenderKey) {
        return;
    }
    lastRenderKey = key;
    var downloads = (data.tasks || []).length;
    lastDownloadActive = downloads;
    document.getElementById('badgeDownload').textContent = downloads;
    renderOverall(data.summary, downloads, SUMMARY_IDS.download);
    renderStat('stat', [
        statCell('成功', data.count.success, 'ok', 'success', 'download'),
        statCell('失敗', data.count.failure, 'bad', 'failure', 'download'),
        statCell('跳過', data.count.skip, 'skip', 'skip', 'download'),
        statCell('下載中', downloads, '', 'active', 'download'),
        statCell('佇列', countQueueMembers(data.links), 'queue', 'queue', 'download')
    ]);
    lastUploadActive = renderUpload(data.uploads || []);
    lastListenCount = renderListeners(data.listeners);
    renderService(data.service);
    if (!adminSettingsLoaded) {
        loadAdminSettings();
    }
    renderOuterLinks(data.outer_links);
    renderStatus();
    // 只有列表結構變化(成員增減/狀態改變)才重建 DOM;
    // 否則僅就地更新正在下載的行,避免每秒整表重建帶來的重排與重繪。
    var structKey = structKeyOf(data);
    if (structKey !== lastStructKey) {
        lastStructKey = structKey;
        renderList(data);
    } else {
        updateTaskRows(data);
    }
    syncBackgroundProgress(data.count.success + data.count.failure + data.count.skip + lastUploadFinished);
}

function syncBackgroundProgress(finished) {  // 下載或上載每完成一個任務,背景漸變就推進一格,與官方發送訊息時推進一致。
    if (bgLastProgress < 0) {
        bgLastProgress = finished;  // 首次只記錄基數,不觸發移動。
        return;
    }
    if (finished > bgLastProgress) {
        bgLastProgress = finished;
        bgAdvancePosition();
    }
    if (finished < bgLastProgress) {
        bgLastProgress = finished;  // 任務被清空或重置時同步基數,避免數字回退後誤觸發。
    }
}

async function refresh(force) {
    try {
        var res = await fetch('/api/progress', {cache: 'no-store', headers: authHeaders()});
        if (res.status === 401) {
            openLogin();  // 未認證:前端展示登入卡片,不再觸發瀏覽器原生彈出視窗。
            return;
        }
        document.body.classList.remove('logged-out');  // 認證通過,顯示頁面內容。
        render(await res.json(), force);
        refreshNameTip();  // 列表重繪後按目前滑鼠位置重新定位提示。
        document.getElementById('offline').style.display = 'none';
    } catch (e) {
        document.getElementById('offline').style.display = 'block';
    }
}

function bindSections() {
    var items = document.querySelectorAll('.side-item');
    for (var i = 0; i < items.length; i++) {
        items[i].onclick = function () {
            switchSection(this.getAttribute('data-section'));
        };
    }
}

function bindListenTabs() {
    var tabs = document.querySelectorAll('#listenTabs .tab');
    for (var i = 0; i < tabs.length; i++) {
        tabs[i].onclick = function () {
            switchListen(this.getAttribute('data-listen'));
        };
    }
}

function bindListenRemove() {
    var box = document.getElementById('page-listener');  // 用事件委託,避免每次輪詢重新綁定。
    box.onclick = function (event) {
        var target = event.target;
        if (!target || !target.classList || !target.classList.contains('btn-del')) {
            return;
        }
        removeListener(target.getAttribute('data-kind'), target.getAttribute('data-link'));
    };
}

var OUTER_LINK_IDS = {github: 'linkGithub', subscribe_channel: 'linkChannel', video_tutorial: 'linkVideo'};

function renderOuterLinks(links) {
    Object.keys(OUTER_LINK_IDS).forEach(function (key) {
        var node = document.getElementById(OUTER_LINK_IDS[key]);
        var url = (links || {})[key];
        node.href = url || '#';
        node.hidden = !url;  // 後端未提供該連結時隱藏對應選單項。
    });
}

function setMenuOpen(open) {
    document.getElementById('menuDropdown').hidden = !open;
}

function menuBtnClick(event) {
    event.stopPropagation();  // 阻止冒泡,避免立刻被外部點擊處理關閉。
    setMenuOpen(document.getElementById('menuDropdown').hidden);
}

function menuOutsideClick(event) {
    if (!document.getElementById('menuWrap').contains(event.target)) {
        setMenuOpen(false);
    }
}

function menuEscape(event) {
    if (event.key === 'Escape') {
        setMenuOpen(false);
    }
}

function bindMenu() {
    document.getElementById('menuBtn').onclick = menuBtnClick;
    document.addEventListener('click', menuOutsideClick);
    document.addEventListener('keydown', menuEscape);
}

var COLS_KEY = 'trmd_cols';  // 各表列寬的本機儲存鍵。
var COLS_MIN = 48;  // 單列最小寬度,避免被拖到不可讀。
var colsCache = {};  // 表名 -> 非彈性列的像素寬度數組。
var dragState = null;  // 拖拽過程中的臨時狀態。

function readDefaultCols(list) {
    var text = window.getComputedStyle(list).getPropertyValue('--cols');  // 自訂屬性在隱藏元素上也可讀取。
    /* 先去掉首列的 minmax(...):否則會把它裏面的最小值(如 minmax(200px, 1fr) 的 200px)
       也當成固定列寬提取出來,導致列數憑空多一列、網格軌道與表頭單元格數不匹配。
       縮放時反覆重算還會讓列數不斷累加,最終表頭錯亂。 */
    text = text.replace(/minmax\([^)]*\)/g, '');
    var matches = text.match(/(\d+(?:\.\d+)?)px/g) || [];
    var widths = [];
    for (var i = 0; i < matches.length; i++) {
        widths.push(Math.round(parseFloat(matches[i])));
    }
    return widths.length ? widths : [COLS_MIN];
}

var measureEl = null;  // 複用同一個隱藏元素測量文字寬度,避免頻繁建立節點。

function measureTextWidth(text, cs) {
    if (!measureEl) {
        measureEl = document.createElement('span');
        measureEl.style.cssText = 'position:absolute;left:-9999px;top:0;visibility:hidden;white-space:nowrap;';
        document.body.appendChild(measureEl);
    }
    measureEl.style.fontStyle = cs.fontStyle;
    measureEl.style.fontWeight = cs.fontWeight;
    measureEl.style.fontSize = cs.fontSize;
    measureEl.style.fontFamily = cs.fontFamily;
    measureEl.style.letterSpacing = cs.letterSpacing;
    measureEl.textContent = text;
    return measureEl.offsetWidth;
}

// 測量每列標題完整顯示所需的寬度,作為該列不可被壓縮的下限。
// 返回數組與表頭列格一一對應,首項為彈性列(頻道/監聽頻道)的下限。
function measureColMins(list) {
    var cells = list.querySelector('.list-head').children;
    var mins = [];
    for (var i = 0; i < cells.length; i++) {
        var cs = window.getComputedStyle(cells[i]);
        var need = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0) + 4;  // 內邊距 + 餘量,避免標題貼邊。
        var text = cells[i].querySelector('.htext');
        if (text && text.textContent) {
            need += measureTextWidth(text.textContent, cs);
        }
        // 單元格可通過 --col-min 聲明額外下限(如進度列需保證百分比可見)。
        var colMin = parseFloat(cs.getPropertyValue('--col-min')) || 0;
        mins.push(Math.max(COLS_MIN, Math.ceil(need), colMin));
    }
    return mins;
}

// 移動端彈性列(名稱列)的最小寬度保底:
// 窄屏下固定列合計已超過視口,彈性列會退回到"標題文字寬度"(約百來像素),
// 再被嵌套縮進吃掉一部分後檔案名稱幾乎完全看不見。故移動端強制留出可讀寬度,
// 超出的部分由橫向滾動承載。
var FLEX_MIN_MOBILE = 200;

function flexColMin(measured) {
    var min = Math.max(COLS_MIN, measured || COLS_MIN);
    if (window.innerWidth <= 760) {
        min = Math.max(min, FLEX_MIN_MOBILE);
    }
    return min;
}

function applyCols(list, widths, flexMin) {
    var parts = ['minmax(' + (flexMin || COLS_MIN) + 'px, 1fr)'];  // 首列彈性列不低於標題寬度,避免被其它列擠到看不見。
    for (var i = 0; i < widths.length; i++) {
        parts.push(widths[i] + 'px');
    }
    list.style.setProperty('--cols', parts.join(' '));
}

function buildGrips(list) {
    var head = list.querySelector('.list-head');
    var cells = head.children;
    var table = list.getAttribute('data-table');
    for (var i = 0; i < cells.length - 1; i++) {  // 末列格右側為容器邊界,不生成分隔條。
        if (cells[i].querySelector('.grip')) {
            continue;  // 已存在分隔條時不重複建立。
        }
        var grip = document.createElement('span');
        grip.className = 'grip';
        grip.setAttribute('data-table', table);
        grip.setAttribute('data-index', i);
        grip.onpointerdown = resizeStart;
        cells[i].appendChild(grip);
    }
}

function clampColsWidth(widths, index, value, maxFixed, mins) {
    var others = 0;
    for (var i = 0; i < widths.length; i++) {
        if (i !== index) {
            others += widths[i];
        }
    }
    // 下限取標題完整顯示所需寬度,保證表頭標題永不被壓縮。
    var floor = Math.max(COLS_MIN, (mins && mins[index + 1]) || COLS_MIN);
    // 預留首列彈性列的最小寬度,避免固定列被拉到超出可用空間後擠壓首列文字。
    var flexMin = flexColMin(mins && mins[0]);
    var max;
    if (window.innerWidth <= 760) {
        // 移動端允許橫向滾動,不把列寬限制在視口內,用戶可自由拖寬,超出部分滾動查看。
        max = Math.max(value, 900);
    } else {
        max = Math.max(COLS_MIN, maxFixed - others - flexMin);
    }
    // 標題優先:空間不足時保留標題所需寬度,寧可讓行溢出也不壓縮表頭文字。
    return Math.max(floor, Math.min(value, max));
}

function resizeStart(event) {
    var grip = event.currentTarget;
    var list = grip.closest('.list');
    var head = list.querySelector('.list-head');
    var index = Number(grip.getAttribute('data-index'));
    var table = list.getAttribute('data-table');
    var widths = colsCache[table] || readDefaultCols(list);
    var style = window.getComputedStyle(head);
    var gap = parseFloat(style.columnGap) || 0;
    var padding = (parseFloat(style.paddingLeft) || 0) + (parseFloat(style.paddingRight) || 0);
    dragState = {
        list: list,
        table: table,
        index: index,
        col: index,  // 每個分隔條都是其右側固定列的左邊界,統一調整該列,保證每列都有且僅有一個分隔條。
        sign: -1,  // 向右拖動縮小該列(空間讓給首列彈性列),向左拖動加寬;分隔條始終跟隨光標。
        origin: widths.slice(),
        widths: widths.slice(),
        startX: event.clientX,
        maxFixed: Math.max(head.clientWidth - padding - gap * widths.length, 0),
        mins: measureColMins(list)  // 各列標題所需的最小寬度,拖拽期間保持不變。
    };
    event.preventDefault();
    event.stopPropagation();
    document.body.classList.add('resizing');
    document.addEventListener('pointermove', resizeMove);
    document.addEventListener('pointerup', resizeEnd);
}

function resizeMove(event) {
    if (!dragState) {
        return;
    }
    var delta = event.clientX - dragState.startX;
    var value = dragState.origin[dragState.col] + delta * dragState.sign;
    dragState.widths[dragState.col] = clampColsWidth(dragState.widths, dragState.col, value, dragState.maxFixed, dragState.mins);
    applyCols(dragState.list, dragState.widths, flexColMin(dragState.mins[0]));
    event.preventDefault();
}

function resizeEnd() {
    if (!dragState) {
        return;
    }
    colsCache[dragState.table] = dragState.widths;
    try {
        localStorage.setItem(COLS_KEY, JSON.stringify(colsCache));  // 記住本次列寬,重新整理後恢復。
    } catch (e) {
        // 隱私模式下寫入失敗可忽略。
    }
    document.body.classList.remove('resizing');
    document.removeEventListener('pointermove', resizeMove);
    document.removeEventListener('pointerup', resizeEnd);
    dragState = null;
}

function initCols() {
    try {
        colsCache = JSON.parse(localStorage.getItem(COLS_KEY) || '{}') || {};
    } catch (e) {
        colsCache = {};
    }
    var lists = document.querySelectorAll('.list[data-table]');
    for (var i = 0; i < lists.length; i++) {
        var list = lists[i];
        var table = list.getAttribute('data-table');
        var head = list.querySelector('.list-head');
        var widths = colsCache[table];
        if (!widths || widths.length !== head.children.length - 1) {
            widths = readDefaultCols(list);  // 列數變化或首次載入時回退到預設列寬。
        }
        var mins = measureColMins(list);
        var j;
        for (j = 0; j < widths.length; j++) {
            widths[j] = Math.max(widths[j], mins[j + 1]);  // 已儲存的列寬也不得小於標題所需寬度。
        }
        colsCache[table] = widths;
        applyCols(list, widths, flexColMin(mins[0]));
        buildGrips(list);
    }
}

// 跨斷點(旋轉屏幕、縮放視窗)時重新應用列寬,
// 讓移動端彈性列的保底最小寬度在進入/離開窄屏時正確生效或取消。
/* 縮放、視窗尺寸變化都會改變 innerWidth(CSS 像素),
   統一防抖重算列寬,避免高縮放比例下殘留舊寬度導致表頭錯亂。 */
var resizeTimer = null;
window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(initCols, 150);
});

var savedSection = '';
var savedListen = '';
try {
    savedSection = localStorage.getItem(SECTION_KEY) || '';
    savedListen = localStorage.getItem(LISTEN_KEY) || '';
    collapsed = JSON.parse(localStorage.getItem(COLLAPSE_KEY) || '{}') || {};  // 讀回各分組摺疊狀態。
    allCollapsed = localStorage.getItem(ALL_KEY) === '1';
    uploadAllCollapsed = localStorage.getItem(UPLOAD_ALL_KEY) === '1';
    lastLinkCollapsed = localStorage.getItem(LINK_LAST_KEY) !== '0';  // 無記錄時保持連結層預設摺疊。
    lastUploadCollapsed = localStorage.getItem(UPLOAD_LAST_KEY) === '1';  // 無記錄時保持上載頻道層預設展開。
} catch (e) {
    savedSection = '';
    savedListen = '';
    collapsed = {};
    allCollapsed = false;
    uploadAllCollapsed = false;
    lastLinkCollapsed = true;
    lastUploadCollapsed = false;
}

function initVersion() {
    var tip = document.getElementById('logoVersion');
    var trmd = document.getElementById('tipTrmd');
    var pyrogram = document.getElementById('tipPyrogram');
    if (trmd.textContent.indexOf('__') === 0 || pyrogram.textContent.indexOf('__') === 0) {
        tip.hidden = true;  // 佔位符未被伺服器端替換時隱藏,避免顯示原始佔位文字。
    }
}

/* 統一接管原生 title 提示:任何帶 title 的元素都改用自訂玻璃提示,
   避免瀏覽器預設提示與自訂風格混雜(未截斷的名稱原本會冒出原生提示)。 */
var nameTipEl = null;
var nameTipFor = null;
var tipMouseX = 0;
var tipMouseY = 0;

function nameTipNode() {
    if (!nameTipEl) {
        nameTipEl = document.getElementById('nameTip');
    }
    return nameTipEl;
}

// 取最近的、帶提示文案的元素(data-tip 或 title)。
function nameTipTarget(node) {
    if (!node || !node.closest) {
        return null;
    }
    return node.closest('[data-tip], [title]');
}

// 原生 title 會與自訂提示同時彈出,首次遇到時遷移為 data-tip 並移除 title。
function takeTipText(el) {
    if (el.hasAttribute('title')) {
        el.setAttribute('data-tip', el.getAttribute('title'));
        el.removeAttribute('title');
    }
    return el.getAttribute('data-tip') || '';
}

function showNameTip(el) {
    var text = takeTipText(el);
    var tip = nameTipNode();
    if (!text || !tip) {
        return;
    }
    tip.textContent = text;
    tip.classList.add('show');  // 先顯示以取得實際尺寸,再據此定位。
    var rect = el.getBoundingClientRect();
    var left = rect.left;
    var top = rect.bottom + 8;
    var width = tip.offsetWidth;
    var height = tip.offsetHeight;
    if (left + width > window.innerWidth - 8) {
        left = Math.max(8, window.innerWidth - width - 8);
    }
    if (top + height > window.innerHeight - 8) {
        top = Math.max(8, rect.top - height - 8);  // 下方放不下時翻到上方。
    }
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
    nameTipFor = el;
}

function hideNameTip() {
    if (nameTipEl) {
        nameTipEl.classList.remove('show');
    }
    nameTipFor = null;
}

// 列表每秒重繪會銷燬懸停元素,重繪後按目前滑鼠位置重新定位提示。
function refreshNameTip() {
    if (!nameTipFor || nameTipFor.isConnected) {
        return;
    }
    var el = nameTipTarget(document.elementFromPoint(tipMouseX, tipMouseY));
    if (el) {
        showNameTip(el);
    } else {
        hideNameTip();
    }
}

function initNameTip() {
    document.addEventListener('mousemove', function (event) {
        tipMouseX = event.clientX;
        tipMouseY = event.clientY;
    });
    document.addEventListener('mouseover', function (event) {
        if (document.body.classList.contains('resizing')) {
            return;  // 拖拽列寬時不彈提示,避免干擾。
        }
        if (nameTipFor && !nameTipFor.isConnected) {
            hideNameTip();
        }
        var el = nameTipTarget(event.target);
        if (!el || nameTipFor === el) {
            return;
        }
        showNameTip(el);
    });
    document.addEventListener('mouseout', function (event) {
        var el = nameTipTarget(event.target);
        var to = nameTipTarget(event.relatedTarget);
        if (el && nameTipFor === el && to !== el) {
            hideNameTip();  // 仍在同一元素內移動時不隱藏,避免閃爍。
        }
    });
    window.addEventListener('scroll', hideNameTip, true);  // 滾動後位置失效,直接隱藏。
    document.addEventListener('pointerdown', function (event) {
        if (nameTipTarget(event.target) !== nameTipFor) {
            hideNameTip();  // 點擊提示以外的區域時關閉。
        }
    });
}

/*
 * ===== 漸變背景實現 =====
 * 移植自 telegram-tt(web.telegram.org/a)的 util/gradientBackground.ts;
 * 該漸變算法改編自 http://useless.altervista.org/gradient.html(原腳本作者未知)。
 * 原始代碼以 GNU GPL-3.0 授權,版權歸相應原作者所有。
 * 移植並修改: Gentlesprite, 2026-09
 * 修改內容: 將原 React/TS 實現改寫為原生 JS,並適配本專案 DOM 結構。
 * SPDX-License-Identifier: GPL-3.0-only
 */
/* ===== 漸變背景,逐行移植自官方 web.telegram.org/a(telegram-tt)的 util/gradientBackground.ts =====
   注意:官方 Web A 與 Web K(tweb)的漸變是兩套實現,色點座標、混色公式、顏色順序都不同。 */
var BG_GRADIENT_SIZE = 100;  // 官方 useGradientBackground 的 CANVAS_SIZE = 100,靠 CSS 拉伸獲得柔和觀感。
var BG_GRADIENT_SPEED = 0.1;  // 官方 ANIMATION_SPEED:色點向目標點移動的每幀插值係數。
var BG_GRADIENT_EPSILON = 0.01;  // 官方 POSITION_EPSILON:色點與目標的距離小於該值視為到位。
var BG_GRADIENT_BLEND_POWER = 3;  // 官方 BLEND_POWER:按"與最近色點的距離差"加權的冪次。
var BG_GRADIENT_STEP = 2;  // 官方 KEY_POINT_STEP:每個顏色點每次前進 2 個索引。
var BG_GRADIENT_POINTS = [  // 官方 KEY_POINTS:8 個色點的歸一化座標。
    [0.265, 0.582],
    [0.176, 0.918],
    [0.415, 0.836],
    [0.644, 0.755],
    [0.735, 0.418],
    [0.824, 0.082],
    [0.585, 0.164],
    [0.356, 0.245]
];
var bgCanvas = null;
var bgCtx = null;
var bgHelperCanvas = null;  // 隱藏的小畫布,先寫入 ImageData 再拷貝到主畫布,與官方兩級結構一致。
var bgHelperCtx = null;
var bgColors = [];
var bgKeyShift = 0;
var bgCurrentPositions = [];
var bgTargetPositions = [];
var bgAnimating = false;
var bgLastProgress = -1;  // 上一輪的已完成任務總數,-1 表示尚未記錄基數。
// 塗鴉遮罩烘焙相關:把 pattern.svg 光柵化後逐幀用 destination-in 烙進畫布,取代 CSS mask-image,
// 從而消除 Chrome 對「帶遮罩的 canvas 每幀重繪」的分塊閃爍(Edge 不觸發此 bug)。
var bgDoodleImg = null;     // 載入並補全尺寸的塗鴉原圖。
var bgDoodlePattern = null; // 由遮罩瓦片畫布生成的重複圖案,用於在設備像素空間 1:1 平鋪。
var bgDoodleLoader = null;  // 遮罩圖載入器。
var bgDoodleDpr = 0;        // 目前瓦片所用像素密度,用於判斷是否需要重建。
var bgDoodleTileW = 0;      // 遮罩瓦片寬(設備像素),對應官方 mask-size 的 26.875rem(430px)。
var bgDoodleTileH = 0;      // 遮罩瓦片高(設備像素),按原圖寬高比推算。
var bgDoodleOffX = 0;       // 對應官方 mask-position:center 的平鋪原點橫向偏移(設備像素)。
var bgDoodleOffY = 0;       // 對應官方 mask-position:center 的平鋪原點縱向偏移(設備像素)。
var BG_PATTERN_URL = 'img/pattern.svg';     // 官方塗鴉圖案,與被移除的 CSS mask-image 同一檔案。
var BG_PATTERN_TILE = 430;                   // 官方 26.875rem(1rem=16px)對應的瓦片寬度(CSS px)。
var BG_PATTERN_ASPECT = 2960 / 1440;         // 遮罩原圖 viewBox 寬高比,取不到固有尺寸時兜底。

function bgHexToRgb(hex) {  // 把 #rrggbb 顏色解析為 [r, g, b] 數組。
    var value = parseInt(hex.slice(1, 7), 16);
    return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

function bgGetPositions(shift) {  // 官方 buildTargetPositions:取 keyPoints[(shift + i × 2) % 8] 的 4 個點。
    var result = [];
    for (var i = 0; i < 4; i++) {
        var point = BG_GRADIENT_POINTS[(shift + i * BG_GRADIENT_STEP) % BG_GRADIENT_POINTS.length];
        result.push([point[0], point[1]]);
    }
    return result;
}

var bgImageData = null;  // 複用的 ImageData:每幀新建會產生大量 GC 壓力。

function bgGetGradientImageData() {  // 官方 drawStaticGradient:按與最近色點的距離差 3 次冪加權混合四色。
    // 優化點:複用 ImageData、取消每像素的數組分配、用乘法替代 Math.pow,視覺結果完全一致。
    if (!bgImageData) {
        bgImageData = bgHelperCtx.createImageData(BG_GRADIENT_SIZE, BG_GRADIENT_SIZE);
    }
    var pixels = bgImageData.data;
    var offset = 0;
    var size = BG_GRADIENT_SIZE;
    // 色點座標與顏色提到循環外,避免每個像素重複讀取數組。
    var px0 = bgCurrentPositions[0][0], py0 = bgCurrentPositions[0][1];
    var px1 = bgCurrentPositions[1][0], py1 = bgCurrentPositions[1][1];
    var px2 = bgCurrentPositions[2][0], py2 = bgCurrentPositions[2][1];
    var px3 = bgCurrentPositions[3][0], py3 = bgCurrentPositions[3][1];
    var c0r = bgColors[0][0], c0g = bgColors[0][1], c0b = bgColors[0][2];
    var c1r = bgColors[1][0], c1g = bgColors[1][1], c1b = bgColors[1][2];
    var c2r = bgColors[2][0], c2g = bgColors[2][1], c2b = bgColors[2][2];
    var c3r = bgColors[3][0], c3g = bgColors[3][1], c3b = bgColors[3][2];
    for (var y = 0; y < size; y++) {
        var yRatio = y / size;
        // 行方向的差值在外層算一次,內層複用。
        var ay = yRatio - py0, by = yRatio - py1, cy = yRatio - py2, dy = yRatio - py3;
        var ay2 = ay * ay, by2 = by * by, cy2 = cy * cy, dy2 = dy * dy;
        for (var x = 0; x < size; x++) {
            var xRatio = x / size;
            var ax = xRatio - px0, bx = xRatio - px1, cx = xRatio - px2, dx = xRatio - px3;
            var d0 = Math.sqrt(ax * ax + ay2);
            var d1 = Math.sqrt(bx * bx + by2);
            var d2 = Math.sqrt(cx * cx + cy2);
            var d3 = Math.sqrt(dx * dx + dy2);
            var min = d0;
            if (d1 < min) {
                min = d1;
            }
            if (d2 < min) {
                min = d2;
            }
            if (d3 < min) {
                min = d3;
            }
            // 權重 = (1 - (距離 - 最近距離)) 的 BG_GRADIENT_BLEND_POWER(3) 次冪;
            // 常數 3 用連乘代替 Math.pow,速度快一個量級。
            var k0 = 1 - (d0 - min), k1 = 1 - (d1 - min);
            var k2 = 1 - (d2 - min), k3 = 1 - (d3 - min);
            var w0 = k0 * k0 * k0, w1 = k1 * k1 * k1;
            var w2 = k2 * k2 * k2, w3 = k3 * k3 * k3;
            var total = w0 + w1 + w2 + w3;
            if (total < 0) {
                total = -total;
            }
            if (total === 0) {
                total = 1;
            }  // 避免除零(原實現會產出 NaN)。
            var n0 = w0 / total, n1 = w1 / total, n2 = w2 / total, n3 = w3 / total;
            pixels[offset++] = c0r * n0 + c1r * n1 + c2r * n2 + c3r * n3;
            pixels[offset++] = c0g * n0 + c1g * n1 + c2g * n2 + c3g * n3;
            pixels[offset++] = c0b * n0 + c1b * n1 + c2b * n2 + c3b * n3;
            pixels[offset++] = 255;
        }
    }
    return bgImageData;
}

function bgDrawImageData(id) {  // 先寫入隱藏畫布,再拉伸拷貝到設備分辨率主畫布,隨後用 destination-in 烘焙塗鴉。
    var viewW = bgCanvas.width || BG_GRADIENT_SIZE;
    var viewH = bgCanvas.height || BG_GRADIENT_SIZE;
    bgHelperCtx.putImageData(id, 0, 0);
    bgCtx.save();
    bgCtx.globalCompositeOperation = 'source-over';
    bgCtx.clearRect(0, 0, viewW, viewH);
    bgCtx.imageSmoothingEnabled = true;
    bgCtx.drawImage(bgHelperCanvas, 0, 0, BG_GRADIENT_SIZE, BG_GRADIENT_SIZE, 0, 0, viewW, viewH);
    if (bgDoodlePattern) {
        /* 用 destination-in 把塗鴉烘焙進畫布像素,取代 CSS mask-image:遮罩不再由瀏覽器合成層處理,
           每幀只剩兩次全屏繪製,Chrome 不再有逐幀重合成遮罩導致的分塊閃爍。
           圖案在設備像素空間 1:1 平鋪,不縮放,清晰度與矢量遮罩一致。 */
        bgCtx.globalCompositeOperation = 'destination-in';
        bgCtx.setTransform(1, 0, 0, 1, 0, 0);
        bgCtx.translate(bgDoodleOffX, bgDoodleOffY);
        bgCtx.fillStyle = bgDoodlePattern;
        bgCtx.fillRect(-bgDoodleOffX, -bgDoodleOffY, viewW, viewH);
    }
    bgCtx.restore();
}

function bgDoodleAspect() {  // 遮罩原圖寬高比:優先取固有尺寸,退化成預設 300×150 等異常時按 viewBox 兜底。
    var width = bgDoodleImg.naturalWidth;
    var height = bgDoodleImg.naturalHeight;
    if (width > 0 && height > 0) {
        var ratio = height / width;
        if (ratio > 1.2 && ratio < 3.0) {  // 合理塗鴉寬高比區間,排除瀏覽器預設 300×150 退化尺寸。
            return ratio;
        }
    }
    return BG_PATTERN_ASPECT;
}

function bgBuildDoodle() {  // 把遮罩原圖按目前設備像素密度光柵化為瓦片畫布,再生成重複圖案。
    if (!bgDoodleImg || !bgCtx) {
        return;
    }
    var dpr = window.devicePixelRatio || 1;  // 不封頂:放大時瀏覽器 dpr 會升高,按真實值光柵化才 1:1 清晰。
    if (bgDoodlePattern && bgDoodleDpr === dpr) {
        return;  // 像素密度未變化無需重建,避免拖動視窗時反覆光柵化 SVG。
    }
    bgDoodleDpr = dpr;
    var tileW = Math.max(1, Math.round(BG_PATTERN_TILE * dpr));
    var tileH = Math.max(1, Math.round(BG_PATTERN_TILE * bgDoodleAspect() * dpr));
    var tile = document.createElement('canvas');
    tile.width = tileW;
    tile.height = tileH;
    var tileCtx = tile.getContext('2d');
    // 瓦片寬高比與 viewBox 一致,SVG 矢量按目標尺寸清晰光柵化,不會出現發虛或留白。
    tileCtx.drawImage(bgDoodleImg, 0, 0, tileW, tileH);
    bgDoodlePattern = bgCtx.createPattern(tile, 'repeat');
}

function bgUpdateDoodleGeometry() {  // 依據瓦片寬高比與畫布尺寸計算居中平鋪偏移(設備像素)。
    if (!bgDoodleImg || !bgCanvas) {
        return;
    }
    var dpr = window.devicePixelRatio || 1;  // 不封頂:與瓦片光柵化、畫布分辨率保持一致,放大才清晰。
    bgDoodleTileW = BG_PATTERN_TILE * dpr;
    bgDoodleTileH = bgDoodleTileW * bgDoodleAspect();
    bgDoodleOffX = ((bgCanvas.width - bgDoodleTileW) / 2) % bgDoodleTileW;
    bgDoodleOffY = ((bgCanvas.height - bgDoodleTileH) / 2) % bgDoodleTileH;
}

function bgResizeCanvas() {  // 按視口設備分辨率設定主畫布,並同步遮罩平鋪偏移與圖案,隨後立即重繪。
    if (!bgCanvas || !bgCtx) {
        return;
    }
    var dpr = window.devicePixelRatio || 1;  // 不封頂:畫布按真實設備分辨率建立,放大時隨 resize 重建且清晰。
    var width = Math.max(1, Math.round((bgCanvas.clientWidth || window.innerWidth || 1) * dpr));
    var height = Math.max(1, Math.round((bgCanvas.clientHeight || window.innerHeight || 1) * dpr));
    if (bgCanvas.width !== width || bgCanvas.height !== height) {
        bgCanvas.width = width;  // 重設寬高會清空畫布並重置狀態,需重建變換。
        bgCanvas.height = height;
    }
    bgUpdateDoodleGeometry();
    bgBuildDoodle();
    bgDrawImageData(bgGetGradientImageData());
}

function bgEnsureSvgSize(text) {  // 給無固有尺寸的 SVG 補上與 viewBox 一致的 width/height,避免被縮放模糊。
    return text.replace(/<svg([^>]*)>/i, function (match, attrs) {
        if (/\bwidth\s*=/.test(attrs) && /\bheight\s*=/.test(attrs)) {
            return match;
        }
        var box = attrs.match(/viewBox\s*=\s*["']\s*[\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)/i);
        if (!box) {
            return match;
        }
        return '<svg' + attrs + ' width="' + box[1] + '" height="' + box[2] + '">';
    });
}

function bgLoadDoodle() {  // 異步載入塗鴉遮罩,就緒後烘焙進畫布並顯示背景,失敗則退化為純漸變。
    bgDoodleLoader = new Image();
    bgDoodleLoader.onload = function () {
        bgDoodleImg = bgDoodleLoader;
        bgUpdateDoodleGeometry();
        bgBuildDoodle();
        bgDrawImageData(bgGetGradientImageData());
        bgCanvas.classList.add('on');
        if (bgDoodleLoader.src.indexOf('blob:') === 0) {
            URL.revokeObjectURL(bgDoodleLoader.src);
        }
    };
    bgDoodleLoader.onerror = function () {  // 遮罩載入失敗:退化為無塗鴉的純漸變背景,至少不再閃。
        bgCanvas.classList.add('on');
    };
    // 直接載入無固有尺寸的 SVG 會讓瀏覽器退化成 300×150 再放大,導致塗鴉模糊;
    // 故先取文字、補上與 viewBox 一致的 width/height 再生成 Blob URL,確保按目標尺寸清晰光柵化。
    if (typeof fetch === 'function') {
        fetch(BG_PATTERN_URL).then(function (response) {
            return response.text();
        }).then(function (text) {
            var blob = new Blob([bgEnsureSvgSize(text)], {type: 'image/svg+xml'});
            bgDoodleLoader.src = URL.createObjectURL(blob);
        }).catch(function () {
            bgDoodleLoader.src = BG_PATTERN_URL;  // 取文字失敗則退回直接載入(可能發虛,僅兜底)。
        });
    } else {
        bgDoodleLoader.src = BG_PATTERN_URL;
    }
}

function bgStepPositions() {  // 官方 stepPositions:色點向目標點做 0.1 線性插值,到位後停止。
    var moving = false;
    for (var i = 0; i < 4; i++) {
        var current = bgCurrentPositions[i];
        var target = bgTargetPositions[i];
        if (Math.abs(current[0] - target[0]) > BG_GRADIENT_EPSILON
            || Math.abs(current[1] - target[1]) > BG_GRADIENT_EPSILON) {
            moving = true;
        }
        current[0] = current[0] * (1 - BG_GRADIENT_SPEED) + target[0] * BG_GRADIENT_SPEED;
        current[1] = current[1] * (1 - BG_GRADIENT_SPEED) + target[1] * BG_GRADIENT_SPEED;
    }
    return moving;
}

function bgAnimate() {  // 官方 animate:僅在色點移動期間逐幀重繪,靜止後自動停止,開銷幾乎為零。
    var moving = bgStepPositions();
    bgDrawImageData(bgGetGradientImageData());
    if (moving) {
        requestAnimationFrame(bgAnimate);
    } else {
        bgAnimating = false;
    }
}

function bgAdvancePosition() {  // 官方 advancePosition:推進到下一個目標位並啟動補間;官方在發送訊息時調用。
    bgTargetPositions = bgGetPositions(bgKeyShift);
    bgKeyShift = (bgKeyShift + 1) % BG_GRADIENT_POINTS.length;
    if (!bgAnimating) {
        bgAnimating = true;
        requestAnimationFrame(bgAnimate);
    }
}

function initBackgroundGradient() {
    bgCanvas = document.getElementById('bgGradient');
    if (!bgCanvas || !bgCanvas.getContext) {
        return;
    }
    bgHelperCanvas = document.createElement('canvas');
    bgHelperCanvas.width = BG_GRADIENT_SIZE;
    bgHelperCanvas.height = BG_GRADIENT_SIZE;
    bgHelperCtx = bgHelperCanvas.getContext('2d', {alpha: false});
    var colors = (bgCanvas.getAttribute('data-colors') || '').split(',');
    for (var i = 0; i < colors.length; i++) {
        var color = colors[i].trim();
        if (/^#[0-9a-fA-F]{6}$/.test(color)) {
            bgColors.push(bgHexToRgb(color));
        }
    }
    if (!bgColors.length) {
        return;
    }
    // 官方初始布點為 keyPoints[0,2,4,6],首個目標與目前位置相同,因此載入後與官方靜止狀態一致。
    bgCurrentPositions = bgGetPositions(0);
    bgTargetPositions = bgGetPositions(0);
    bgKeyShift = 1;
    // 啟用 alpha:塗鴉以外區域透明,露出頁面底色,觀感與原 CSS mask 一致。
    bgCtx = bgCanvas.getContext('2d', {alpha: true});
    bgResizeCanvas();  // 按設備分辨率建立主畫布並完成首次繪製(此時尚無塗鴉,僅漸變)。
    window.addEventListener('resize', bgResizeCanvas);
    bgLoadDoodle();  // 遮罩就緒後再添加 on 類顯示背景,避免未遮罩的全屏漸變閃現。
}

bindSections();
bindListenTabs();
bindListenRemove();
bindConfirm();
bindLogin();
initLogout();
bindStatFilter();
bindMenu();
initVersion();
applyBotVisibility();  // 未設定機械人時隱藏整個側邊欄,隨後switchSection會強制鎖定到下載頁。
switchSection(savedSection);
switchListen(savedListen);
document.getElementById('toggleAll').onclick = toggleAll;
document.getElementById('toggleUpload').onclick = toggleUploadAll;
bindAdmin();
initCols();  // 恢復上次的列寬並生成拖拽分隔條。
initNameTip();  // 懸停檔案名稱時顯示完整名稱。
initBackgroundGradient();  // 啟動 Telegram 風格的動畫漸變背景。

/* 頁面不可見(切到後台標籤/最小化)時暫停輪詢。
   後台標籤不會被合成顯示,繼續每秒拉取資料、比對指紋、重建 DOM 只是白白吃 CPU;
   回到前台時立即補一次重新整理,觀感完全不受影響。 */
var pollTimer = 0;

function startPolling() {
    if (!pollTimer) {
        pollTimer = setInterval(refresh, POLL_INTERVAL_MS);
    }
}

function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = 0;
    }
}

document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
        stopPolling();
    } else {
        refresh();  // 回到前台先補一次,避免看到後台期間滯留的舊資料。
        startPolling();
    }
});

refresh(true);  // 首屏強制按最新資料渲染,跳過去重,確保進度列開局即正確顯示。
startPolling();
