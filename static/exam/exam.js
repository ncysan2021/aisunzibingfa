(function () {
  "use strict";

  var API_QUESTIONS = "/api/questions";
  var API_SUBMIT = "/api/submit";

  var state = {
    questions: [],
    answers: {},
    result: null,
  };

  var els = {};

  function init() {
    els.status = document.getElementById("exam-status");
    els.viewTake = document.getElementById("exam-view-take");
    els.viewReview = document.getElementById("exam-view-review");
    els.viewResult = document.getElementById("exam-view-result");
    els.questions = document.getElementById("exam-questions");
    els.reviewList = document.getElementById("exam-review-list");
    els.result = document.getElementById("exam-result");

    document.getElementById("btn-submit").addEventListener("click", onGoReview);
    document.getElementById("btn-back").addEventListener("click", function () {
      showView("take");
      window.scrollTo(0, 0);
    });
    document.getElementById("btn-confirm").addEventListener("click", onConfirmSubmit);
    document.getElementById("btn-retry").addEventListener("click", loadQuestions);

    loadQuestions();
  }

  function loadQuestions() {
    setStatus("正在加载题目...");
    showView("none");
    state.answers = {};
    state.result = null;

    fetch(API_QUESTIONS, { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (!data.questions || !data.questions.length) {
          throw new Error("题库为空");
        }
        state.questions = data.questions;
        renderQuestions();
        setStatus("");
        showView("take");
      })
      .catch(function (err) {
        setStatus("加载失败：" + err.message + "。请刷新页面重试。");
      });
  }

  function renderQuestions() {
    els.questions.innerHTML = "";
    state.questions.forEach(function (q, i) {
      var card = document.createElement("div");
      card.className = "exam-q";

      var head = document.createElement("div");
      head.className = "exam-q-num";
      head.innerHTML = "第 " + (i + 1) + " 题 <span class='exam-q-topic'>[" + escapeHtml(q.topic) + "]</span>";
      card.appendChild(head);

      var text = document.createElement("div");
      text.className = "exam-q-text";
      text.textContent = q.question;
      card.appendChild(text);

      var opts = document.createElement("div");
      opts.className = "exam-opts";

      ["A", "B", "C", "D"].forEach(function (letter) {
        var optText = q["option_" + letter.toLowerCase()];
        var inputId = "q" + q.id + "-" + letter;

        var label = document.createElement("label");
        label.className = "exam-opt";
        label.setAttribute("for", inputId);

        var input = document.createElement("input");
        input.type = "radio";
        input.name = "q" + q.id;
        input.value = letter;
        input.id = inputId;
        if (state.answers[q.id] === letter) input.checked = true;
        input.addEventListener("change", function () {
          state.answers[q.id] = letter;
        });

        var letterSpan = document.createElement("span");
        letterSpan.className = "exam-opt-letter";
        letterSpan.textContent = letter + ".";

        var textSpan = document.createElement("span");
        textSpan.className = "exam-opt-text";
        textSpan.textContent = optText;

        label.appendChild(input);
        label.appendChild(letterSpan);
        label.appendChild(textSpan);
        opts.appendChild(label);
      });

      card.appendChild(opts);
      els.questions.appendChild(card);
    });
  }

  function onGoReview() {
    var unanswered = state.questions.filter(function (q) {
      return !state.answers[q.id];
    });
    if (unanswered.length > 0) {
      if (!confirm("还有 " + unanswered.length + " 题未作答，确定进入检查页吗？")) return;
    }
    renderReview();
    showView("review");
    window.scrollTo(0, 0);
  }

  function renderReview() {
    els.reviewList.innerHTML = "";
    state.questions.forEach(function (q, i) {
      var chosen = state.answers[q.id];

      var row = document.createElement("div");
      row.className = "exam-review-row";

      var qDiv = document.createElement("div");
      qDiv.className = "exam-review-q";
      qDiv.textContent = "第 " + (i + 1) + " 题：" + q.question;
      row.appendChild(qDiv);

      var aDiv = document.createElement("div");
      aDiv.className = "exam-review-a";
      if (chosen) {
        aDiv.textContent = "你的答案：" + chosen + ". " + q["option_" + chosen.toLowerCase()];
      } else {
        aDiv.innerHTML = "你的答案：<span class='exam-miss'>未作答</span>";
      }
      row.appendChild(aDiv);

      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "exam-edit-btn";
      btn.textContent = "返回修改";
      btn.addEventListener("click", function () {
        showView("take");
        var cards = els.questions.querySelectorAll(".exam-q");
        if (cards[i]) cards[i].scrollIntoView({ behavior: "smooth", block: "center" });
      });
      row.appendChild(btn);

      els.reviewList.appendChild(row);
    });
  }

  function onConfirmSubmit() {
    var payload = {
      answers: state.questions.map(function (q) {
        return { id: q.id, choice: state.answers[q.id] || "" };
      }),
    };

    var missing = payload.answers.filter(function (a) {
      return !a.choice;
    });
    if (missing.length > 0) {
      alert("还有 " + missing.length + " 题未作答，请返回补全。");
      return;
    }

    if (!confirm("确认提交？提交后不可修改。")) return;

    setStatus("正在判分...");
    showView("none");

    fetch(API_SUBMIT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        return r.json().then(function (data) {
          return { ok: r.ok, data: data };
        });
      })
      .then(function (res) {
        if (!res.ok) throw new Error(res.data.error || "提交失败");
        state.result = res.data;
        renderResult();
        setStatus("");
        showView("result");
        window.scrollTo(0, 0);
      })
      .catch(function (err) {
        setStatus("提交失败：" + err.message);
        showView("review");
      });
  }

  function renderResult() {
    var score = state.result.score;
    var total = state.result.total;
    var results = state.result.results || [];
    var pct = total ? Math.round((score / total) * 100) : 0;

    var html = "";
    html += "<div class='exam-score'>";
    html += "<div class='exam-score-num'>" + score + " / " + total + "</div>";
    html += "<div class='exam-score-pct'>得分 " + pct + "%</div>";
    html += "</div>";

    results.forEach(function (r, i) {
      var your = r.your
        ? r.your + ". " + r["option_" + r.your.toLowerCase()]
        : "未作答";
      var correct = r.correct + ". " + r["option_" + r.correct.toLowerCase()];

      html += "<div class='exam-result-q " + (r.is_correct ? "is-right" : "is-wrong") + "'>";
      html += "<div class='exam-result-head'>第 " + (i + 1) + " 题 " + (r.is_correct ? "✅" : "❌") + "</div>";
      html += "<div class='exam-result-text'>" + escapeHtml(r.question) + "</div>";
      html += "<div class='exam-result-line'><b>你的答案：</b>" + escapeHtml(your) + "</div>";
      if (!r.is_correct) {
        html += "<div class='exam-result-line'><b>正确答案：</b>" + escapeHtml(correct) + "</div>";
      }
      if (r.explanation) {
        html += "<div class='exam-result-exp'><b>解析：</b>" + escapeHtml(r.explanation) + "</div>";
      }
      html += "</div>";
    });

    els.result.innerHTML = html;
  }

  function showView(name) {
    els.viewTake.style.display = name === "take" ? "" : "none";
    els.viewReview.style.display = name === "review" ? "" : "none";
    els.viewResult.style.display = name === "result" ? "" : "none";
  }

  function setStatus(msg) {
    els.status.textContent = msg;
    els.status.style.display = msg ? "" : "none";
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
