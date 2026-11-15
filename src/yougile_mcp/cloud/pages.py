# Adapted from indalo-tech/yougile-mcp-cloud, pinned upstream commit ea88a0d5c5c055262cba9cf9741fd51828481ba5
# Copyright (c) Indalo; upstream licensed AGPL-3.0-only.
# Changes: project source URL, refreshed interface and source link; upstream credit stays in NOTICE.
# SPDX-License-Identifier: AGPL-3.0-only

"""Server-rendered HTML. Every interpolated value goes through ``e()``: no raw input in HTML."""

from __future__ import annotations

from html import escape

# AGPL: people using the service can always reach the code that runs it.
SOURCE = "https://github.com/amonrapmon/yougile-mcp"
AVATAR = "https://avatars.githubusercontent.com/u/167690761?v=4"

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--text:#1d2330;--muted:#5d6675;--line:#dfe3ea;--accent:#2f6fed;
--accent-text:#fff;--error-bg:#fdecec;--error:#a4262c;--ok-bg:#e8f5ec;--ok:#1d6b36}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1d2128;--text:#e7eaf0;--muted:#a3abb9;
--line:#303642;--accent:#5b8cff;--accent-text:#0d1017;--error-bg:#3a1d1f;--error:#ff9aa0;
--ok-bg:#16301f;--ok:#8fdca9}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:420px;margin:8vh auto;padding:0 16px}main.wide{max-width:960px;margin-top:4vh}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:28px}
h1{font-size:22px;margin:0 0 6px}p.lead{color:var(--muted);margin:0 0 20px}
label{display:block;font-weight:600;margin:14px 0 6px}
input[type=text],input[type=email],input[type=password],select,textarea{width:100%;
padding:10px 12px;
border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--text);font:inherit}
textarea{min-height:110px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:14px}
button{margin-top:20px;width:100%;padding:11px;border:0;border-radius:8px;background:var(--accent);
color:var(--accent-text);font:inherit;font-weight:600;cursor:pointer}
button.inline{width:auto;padding:8px 16px;margin-top:12px}
.note{color:var(--muted);font-size:13px;margin-top:16px}
.error{background:var(--error-bg);color:var(--error);border-radius:8px;padding:10px 12px;
margin:12px 0}
.ok{background:var(--ok-bg);color:var(--ok);border-radius:8px;padding:10px 12px;margin:12px 0}
.choice{display:block;width:100%;text-align:left;margin-top:10px;background:var(--bg);
color:var(--text);border:1px solid var(--line)}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:8px;
border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-weight:600}
.checks label{display:inline-flex;gap:6px;font-weight:400;margin:4px 14px 4px 0}
nav{display:flex;gap:16px;margin:4px 0 20px;flex-wrap:wrap}nav a{color:var(--accent);
text-decoration:none}nav a[aria-current]{color:var(--text);font-weight:600}
a{color:var(--accent)}h2{font-size:18px;margin:28px 0 8px}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
.top button{margin-top:0}.muted{color:var(--muted)}.hint{color:var(--muted);font-size:13px;
margin:4px 0 0}fieldset{border:1px solid var(--line);border-radius:8px;padding:8px 14px 12px;
margin:18px 0 0}legend{font-weight:600;padding:0 4px}
.list label{display:flex;gap:8px;align-items:baseline;font-weight:400;margin:6px 0}
.pill{display:inline-block;font-size:12px;padding:0 8px;border-radius:999px;margin:2px 6px 0 0;
border:1px solid var(--line);color:var(--muted)}
button.secondary{background:var(--bg);color:var(--text);border:1px solid var(--line)}
button.danger{background:var(--error-bg);color:var(--error)}
.actions{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-top:8px}
.actions form{margin:0;display:flex;gap:8px;align-items:center}
.actions select{width:auto;margin-top:12px;padding:7px 10px}
textarea.prose{font-family:inherit;font-size:15px}p.foot{text-align:center;margin-top:20px}
code.url{display:block;padding:10px 12px;border:1px solid var(--line);border-radius:8px;
background:var(--bg);font-size:15px;user-select:all;overflow-wrap:anywhere}ol{padding-left:20px}
@media (max-width:640px){table,thead,tbody,tr,td,th{display:block}thead{display:none}
td{border:0;padding:4px 0}tr{border-bottom:1px solid var(--line);padding:8px 0}
td[data-label]::before{content:attr(data-label) ": ";color:var(--muted)}}


/* Landing page only; OAuth and admin forms keep their existing layout. */
main.landing{max-width:810px;margin:clamp(42px,9vh,94px) auto 28px;padding:0 20px}
main.landing .card{padding:clamp(28px,5vw,49px);border-radius:24px;overflow:hidden;
background:radial-gradient(ellipse at 100% 0%,rgba(70,111,240,.12),transparent 48%),var(--card);
box-shadow:0 22px 85px rgba(30,48,98,.08)}
.landing-brand{display:flex;align-items:center;gap:14px;margin-bottom:40px}
.landing-avatar{display:block;flex:none;width:54px;height:54px;border-radius:16px;overflow:hidden;
border:1px solid var(--line);background:var(--bg);box-shadow:0 6px 15px rgba(34,50,96,.10)}
.landing-avatar img{display:block;width:100%;height:100%;object-fit:cover}
.landing-brand-name{font-size:18px;font-weight:760;letter-spacing:-.45px;line-height:1.25}
.landing-by{font-weight:550;color:var(--muted);white-space:nowrap}
.landing-brand-label{font-size:12px;color:var(--muted);margin-top:4px}
.landing-eyebrow{font-size:11px;letter-spacing:.095em;font-weight:750;text-transform:uppercase;
color:var(--accent);margin:0 0 10px}
.landing h1{max-width:680px;font-size:clamp(34px,5.6vw,52px);font-weight:800;
letter-spacing:-1.8px;line-height:1.09;margin:0 0 22px}
.landing-hero-accent{color:var(--accent)}
.landing .hero-copy{max-width:630px;color:var(--muted);font-size:16px;line-height:1.75;margin:0 0 28px}
.landing .hero-copy strong{color:var(--text);font-weight:650}
.landing-hero-sep{color:var(--accent);opacity:.8;padding:0 4px}
.landing-integrations{margin:0 0 32px}
.landing-integrations-label{display:block;font-size:12px;color:var(--muted);font-weight:650;margin-bottom:11px}
.landing-integrations-list{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.landing-client{padding:6px 10px;border:1px solid var(--line);background:var(--card);
border-radius:10px;color:var(--text);font-size:12px;font-weight:650;white-space:nowrap}
.landing-client-more{font-size:12px;color:var(--muted);padding:6px 2px}
.landing-endpoint-label{font-size:13px;font-weight:700;color:var(--text);margin:0 0 9px}
.landing-endpoint{display:flex;align-items:center;gap:10px;background:var(--bg);
border:1px solid var(--line);border-radius:15px;padding:10px 12px 10px 17px;
transition:border-color .2s,box-shadow .2s}
.landing-endpoint:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px rgba(47,111,237,.11)}
.landing-endpoint code{flex:1;min-width:0;display:block;font-size:clamp(12px,2.3vw,15px);
line-height:1.6;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-weight:650;
letter-spacing:-.3px;user-select:all;overflow-wrap:anywhere}
.landing-copy{width:36px;height:36px;min-width:36px;display:inline-flex;justify-content:center;
align-items:center;margin:0;padding:0;border:1px solid var(--line);border-radius:10px;
background:var(--card);color:var(--muted);cursor:pointer;transition:background .16s,color .16s}
.landing-copy:hover{background:var(--card);color:var(--accent);border-color:var(--accent)}
.landing-copy:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.landing-copy[data-copied="true"]{color:#138453;border-color:#71c8a5}
.landing-copy svg{display:block;width:17px;height:17px;fill:none;stroke:currentColor;
stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.landing-copy .landing-check{display:none}
.landing-copy[data-copied="true"] .landing-check{display:block}
.landing-copy[data-copied="true"] .landing-copy-icon{display:none}
.landing-endpoint-hint{min-height:19px;margin:10px 2px 0;font-size:12px;line-height:1.55;
color:var(--muted);transition:color .2s}
.landing-endpoint-hint[data-copied="true"]{color:#138453;font-weight:650}
.landing-disclaimer{padding-top:19px;margin:27px 0 0;border-top:1px solid var(--line);
text-align:center;font-size:12px;color:var(--muted);line-height:1.6}
.visually-hidden{position:absolute;width:1px;height:1px;padding:0;margin:-1px;
overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.landing-steps{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px 28px;
border-top:1px solid var(--line);margin-top:34px;padding-top:28px}
.landing-step{font-size:12px;color:var(--muted);line-height:1.65}
.landing-step b{display:block;color:var(--text);font-size:14px;margin:5px 0 4px}
.landing-step-num{font:700 11px ui-monospace,SFMono-Regular,Consolas,monospace;color:var(--accent)}
.landing-step:last-child .landing-step-num{color:#138453}
.site-footer{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:8px 16px;
font-size:12px;color:var(--muted);margin:20px 0 0}
.site-footer a{color:var(--muted);text-decoration:none;font-weight:650;display:inline-flex;align-items:center;gap:6px}
.site-footer a:hover,.site-footer a:focus-visible{color:var(--accent);text-decoration:underline}
@media (max-width:640px){
main.landing{margin-top:24px;padding:0 14px}
main.landing .card{border-radius:19px}
.landing-brand{margin-bottom:30px}
.landing h1{letter-spacing:-1.15px}
.landing .hero-copy{font-size:15px}
.landing-steps{grid-template-columns:1fr;gap:17px}
.landing-step{display:grid;grid-template-columns:32px 1fr;column-gap:8px}
.landing-step-num{grid-row:span 2;padding-top:6px}
.landing-step b{margin:0}
.landing-client{font-size:11px}
}


/* OAuth flow skin. Scoped so company-admin and host-admin layouts stay unchanged. */
main.auth-flow{max-width:552px;margin:clamp(30px,7vh,76px) auto 30px;padding:0 18px}
main.auth-flow .card{padding:clamp(25px,5vw,39px);border-radius:23px;overflow:hidden;
background:radial-gradient(ellipse at 100% 0%,rgba(70,111,240,.12),transparent 48%),var(--card);
box-shadow:0 20px 72px rgba(30,48,98,.085)}
.auth-brand{display:flex;align-items:center;gap:12px;margin-bottom:35px}
.auth-brand-avatar{display:block;width:46px;height:46px;flex:none;overflow:hidden;
border:1px solid var(--line);border-radius:14px;background:var(--bg)}
.auth-brand-avatar img{display:block;width:100%;height:100%;object-fit:cover}
.auth-brand-name{font-size:15px;line-height:1.3;font-weight:760;letter-spacing:-.3px}
.auth-brand-by{color:var(--muted);font-weight:500}
.auth-brand-subtitle{font-size:12px;color:var(--muted);margin-top:3px}
.auth-eyebrow{margin:0 0 9px;color:var(--accent);letter-spacing:.09em;text-transform:uppercase;
font-size:11px;font-weight:750}
.auth-flow h1{font-size:clamp(27px,5vw,33px);line-height:1.16;letter-spacing:-.9px;margin:0 0 10px}
.auth-flow .auth-lead{color:var(--muted);font-size:15px;line-height:1.65;margin:0 0 24px}
.auth-client-request{padding:16px 18px;margin:0 0 25px;border:1px solid rgba(75,115,206,.25);
background:rgba(75,115,206,.065);border-radius:14px}
.auth-client-label{margin:0 0 6px;font-size:12px;font-weight:650;color:var(--muted)}
.auth-client-name{font-size:17px;line-height:1.35;font-weight:760;overflow-wrap:anywhere}
.auth-client-return{font-size:13px;line-height:1.6;color:var(--muted);margin:9px 0 0;
overflow-wrap:anywhere}
.auth-client-return strong{color:var(--text);font-weight:650}
.auth-safety{display:flex;align-items:flex-start;gap:10px;margin:0 0 25px;
font-size:12px;line-height:1.55;color:var(--muted)}
.auth-safety-icon{font-size:15px;line-height:1.2;flex:none;color:var(--accent)}
.auth-flow form label{font-size:13px;font-weight:650;margin:17px 0 7px}
.auth-flow input[type=email],.auth-flow input[type=password],.auth-flow input[type=text]{
min-height:47px;padding:11px 14px;border-radius:12px;background:var(--card);
border:1px solid var(--line);font-size:15px;transition:border-color .15s,box-shadow .15s}
.auth-flow input[type=email]:focus,.auth-flow input[type=password]:focus,.auth-flow input[type=text]:focus{
outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(47,111,237,.13)}
.auth-flow button[type=submit]:not(.choice){display:block;width:100%;min-height:48px;
margin-top:25px;border-radius:12px;font-weight:700}
.auth-flow button[type=submit]:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.auth-flow .auth-note{padding-top:17px;border-top:1px solid var(--line);margin:25px 0 0;
font-size:12px;line-height:1.7;color:var(--muted)}
.auth-flow .error{margin:0 0 20px;border:1px solid rgba(164,38,44,.2);
border-radius:12px;padding:12px 14px;font-size:13px;line-height:1.6}
.auth-flow .auth-companies{display:grid;gap:10px}
.auth-flow button.choice{width:100%;display:flex;align-items:center;justify-content:space-between;
gap:12px;text-align:left;min-height:53px;padding:13px 15px;margin:0;border:1px solid var(--line);
border-radius:12px;background:var(--card);color:var(--text);font-size:14px;font-weight:680;
overflow-wrap:anywhere;cursor:pointer;transition:border-color .15s,background .15s}
.auth-flow button.choice:hover,.auth-flow button.choice:focus-visible{
background:var(--bg);border-color:var(--accent)}
.auth-flow .auth-choice-chevron{color:var(--accent);flex:none;font-weight:800}
.auth-flow .auth-message{padding:17px 18px;border-radius:13px;margin:18px 0 0;
font-size:14px;line-height:1.65;overflow-wrap:anywhere}
.auth-flow .auth-message.error{background:var(--error-bg);color:var(--error)}
.auth-flow .auth-message.ok{background:var(--ok-bg);color:var(--ok)}
.auth-flow .auth-message-link{margin:18px 0 0;font-size:13px}
.auth-flow .auth-message-link a{font-weight:650;text-decoration:none}
.auth-flow .auth-message-link a:hover{text-decoration:underline}
@media (max-width:640px){main.auth-flow{padding:0 14px;margin-top:24px}
main.auth-flow .card{border-radius:19px}
.auth-brand{margin-bottom:29px}
.auth-flow .auth-client-request{padding:14px}
}
"""


LANDING_COPY_JS = r"""
(() => {
  "use strict";
  const button = document.querySelector("[data-copy-mcp]");
  const value = document.getElementById("mcp-url");
  const status = document.getElementById("copy-status");
  const hint = document.getElementById("copy-hint");
  if (!button || !value || !status || !hint) return;
  const originalHint = hint.textContent;

  let resetTimer = null;
  button.addEventListener("click", async () => {
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        throw new Error("Clipboard API unavailable");
      }
      await navigator.clipboard.writeText(value.textContent.trim());
      window.clearTimeout(resetTimer);
      button.dataset.copied = "true";
      button.setAttribute("aria-label", "Адрес MCP скопирован");
      button.title = "Скопировано. Вербуйте своего агента!";
      hint.textContent = "Скопировано. Вербуйте своего агента!";
      hint.dataset.copied = "true";
      status.textContent = "Адрес MCP скопирован. Вербуйте своего агента!";
      resetTimer = window.setTimeout(() => {
        delete button.dataset.copied;
        button.setAttribute("aria-label", "Скопировать адрес MCP-сервера");
        button.title = "Скопировать адрес";
        hint.textContent = originalHint;
        delete hint.dataset.copied;
      }, 2200);
    } catch (_err) {
      const range = document.createRange();
      range.selectNodeContents(value);
      const selection = window.getSelection();
      if (selection) {
        selection.removeAllRanges();
        selection.addRange(range);
      }
      hint.textContent = "Автокопирование недоступно. Адрес выделен для ручного копирования.";
      delete hint.dataset.copied;
      status.textContent = "Не удалось скопировать автоматически. Адрес выделен для ручного копирования.";
    }
  });
})();
"""


def e(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def page(
    title: str, body: str, *, wide: bool = False,
    landing: bool = False, auth_flow: bool = False,
) -> str:
    main_class = "landing" if landing else "auth-flow" if auth_flow else "wide" if wide else ""
    return (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="robots" content="noindex"><title>{e(title)}</title><style>{CSS}</style>'
        f'</head><body><main class="{main_class}"><div class="card">{body}</div>'
        f'<footer class="site-footer"><a href="{SOURCE}" target="_blank" '
        'rel="noopener noreferrer" aria-label="Исходный код на GitHub">'
        'Исходный код на GitHub <span aria-hidden="true">↗</span></a>'
        '<span>Открытый проект · AGPL-3.0</span></footer>'
        + ('<script src="/assets/landing.js" defer></script>' if landing else '')
        + "</main></body></html>"
    )


def auth_brand() -> str:
    """Shared static identity for the OAuth screens, never an identity claim for the client."""
    return (
        '<header class="auth-brand">'
        f'<a class="auth-brand-avatar" href="{SOURCE}" target="_blank" '
        'rel="noopener noreferrer" aria-label="Исходный код YouGile MCP на GitHub">'
        f'<img src="{AVATAR}" width="46" height="46" alt="Аватар Amonrapmon" '
        'referrerpolicy="no-referrer"></a>'
        '<div><div class="auth-brand-name">YouGile MCP '
        '<span class="auth-brand-by">by Amonrapmon</span></div>'
        '<div class="auth-brand-subtitle">Подключение AI-ассистента</div></div>'
        '</header>'
    )


def login_page(
    *,
    action: str,
    hidden: dict[str, str],
    heading: str,
    lead: str,
    error: str | None = None,
    login: str = "",
    client: tuple[str, str] | None = None,  # client-provided name and redirect destination
) -> str:
    fields = "".join(
        f'<input type="hidden" name="{e(k)}" value="{e(v)}">' for k, v in hidden.items()
    )
    asking = ""
    if client:
        name, back = client
        asking = (
            '<section class="auth-client-request" role="note" '
            'aria-label="Запрос доступа">'
            '<div class="auth-client-label">Доступ к вашему YouGile запрашивает</div>'
            f'<div class="auth-client-name">{e(name or "приложение без названия")}</div>'
            '<p class="auth-client-return">После входа вы вернётесь: '
            f'<strong>{e(back)}</strong></p></section>'
            '<p class="auth-safety"><span class="auth-safety-icon" aria-hidden="true">◇</span>'
            '<span>Название приложения задаётся самим подключаемым клиентом. '
            'Если вы не начинали подключение, закройте страницу и не вводите пароль.'
            '</span></p>'
        )
    return page(
        heading,
        auth_brand()
        + '<p class="auth-eyebrow">Разрешение на подключение</p>'
        + f'<h1>{e(heading)}</h1><p class="auth-lead">{e(lead)}</p>'
        + asking
        + (f'<div class="error" role="alert">{e(error)}</div>' if error else "")
        + f'<form method="post" action="{e(action)}">{fields}'
        '<label for="login">Логин YouGile (email)</label>'
        '<input id="login" name="login" type="email" autocomplete="username" '
        'inputmode="email" required '
        f'value="{e(login)}">'
        '<label for="password">Пароль YouGile</label>'
        '<input id="password" name="password" type="password" '
        'autocomplete="current-password" required>'
        '<button type="submit">Войти и продолжить</button></form>'
        '<p class="auth-note">Пароль нужен только для первого подключения '
        'и выпуска персонального ключа. При выборе компании данные могут '
        'временно храниться в зашифрованном виде до пяти минут. '
        'Дальше используется зашифрованный ключ с вашими правами в YouGile.</p>',
        auth_flow=True,
    )


def company_page(
    *,
    action: str,
    hidden: dict[str, str],
    companies: list[tuple[str, str]],
    lead: str = "Вы состоите в нескольких компаниях YouGile. "
    "Подключение будет работать с одной из них.",
) -> str:
    fields = "".join(
        f'<input type="hidden" name="{e(k)}" value="{e(v)}">' for k, v in hidden.items()
    )
    buttons = "".join(
        '<button class="choice" type="submit" name="company" '
        f'value="{e(cid)}"><span>{e(name)}</span>'
        '<span class="auth-choice-chevron" aria-hidden="true">↗</span></button>'
        for cid, name in companies
    )
    return page(
        "Выбор компании",
        auth_brand()
        + '<p class="auth-eyebrow">Почти готово</p>'
        + '<h1>Выберите компанию</h1>'
        + f'<p class="auth-lead">{e(lead)}</p>'
        + f'<form class="auth-companies" method="post" action="{e(action)}">'
        + fields + buttons + '</form>'
        + '<p class="auth-note">Агент получит доступ только к компании, '
        'которую вы выберете, и только с вашими правами в YouGile.</p>',
        auth_flow=True,
    )


def home_page(mcp_url: str) -> str:
    """Friendly MCP landing; authentication is still OAuth-only."""
    return page(
        "YouGile MCP by Amonrapmon",
        '<header class="landing-brand">'
        f'<a class="landing-avatar" href="{SOURCE}" target="_blank" '
        'rel="noopener noreferrer" aria-label="Репозиторий YouGile MCP на GitHub">'
        f'<img src="{AVATAR}" alt="Аватар Amonrapmon" width="54" height="54" '
        'referrerpolicy="no-referrer"></a>'
        '<div><div class="landing-brand-name">YouGile MCP '
        '<span class="landing-by">by Amonrapmon</span></div>'
        '<div class="landing-brand-label">Прокачиваем YouGile через MCP</div></div></header>'
        '<p class="landing-eyebrow">72 инструмента · никакой магии, только API</p>'
        '<h1>YouGile <span class="landing-hero-accent">на стероидах.</span></h1>'
        '<p class="hero-copy">Подключай своего <strong>AI-агента</strong>'
        '<span class="landing-hero-sep"> | </span>кота'
        '<span class="landing-hero-sep"> | </span>собаку'
        '<span class="landing-hero-sep"> | </span>команду.<br>'
        '<strong>И позволь им разделять и властвовать в твоих проектах.</strong></p>'
        '<section class="landing-integrations" aria-label="MCP-совместимые клиенты">'
        '<span class="landing-integrations-label">Для MCP-совместимых клиентов</span>'
        '<div class="landing-integrations-list">'
        '<span class="landing-client">Codex</span>'
        '<span class="landing-client">Claude Code</span>'
        '<span class="landing-client">ChatGPT</span>'
        '<span class="landing-client">Cursor</span>'
        '<span class="landing-client">Harness</span>'
        '<span class="landing-client-more">и других с поддержкой MCP</span>'
        '</div></section>'
        '<div class="landing-endpoint-label">Адрес MCP-сервера</div>'
        '<section class="landing-endpoint" aria-label="Адрес подключения">'
        f'<code id="mcp-url">{e(mcp_url)}</code>'
        '<button class="landing-copy" type="button" data-copy-mcp '
        'aria-label="Скопировать адрес MCP-сервера" title="Скопировать адрес">'
        '<svg class="landing-copy-icon" viewBox="0 0 24 24" aria-hidden="true">'
        '<rect x="8" y="8" width="12" height="12" rx="2"></rect>'
        '<path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"></path>'
        '</svg>'
        '<svg class="landing-check" viewBox="0 0 24 24" aria-hidden="true">'
        '<path d="m5 12 4 4L19 6"></path></svg>'
        '</button></section>'
        '<p id="copy-hint" class="landing-endpoint-hint">'
        'Один адрес. Семьдесят два инструмента. Никакого шаманского бубна.</p>'
        '<span id="copy-status" class="visually-hidden" role="status" aria-live="polite"></span>'
        '<div class="landing-steps" aria-label="Как подключиться">'
        '<div class="landing-step"><span class="landing-step-num">01/</span>'
        '<b>Добавьте сервер</b>Скопируйте адрес в настройках вашего AI-клиента.</div>'
        '<div class="landing-step"><span class="landing-step-num">02/</span>'
        '<b>Войдите в YouGile</b>Авторизуйтесь в открывшемся окне.</div>'
        '<div class="landing-step"><span class="landing-step-num">03/</span>'
        '<b>Выберите компанию</b>Если у вас их несколько, укажите нужную.</div>'
        '<div class="landing-step"><span class="landing-step-num">04/</span>'
        '<b>Откиньтесь в кресле</b>Отправляйте пионов в работу.</div>'
        '</div>'
        '<p class="landing-disclaimer">🐾 Коты и собаки в списке поддерживаемых '
        'агентов пока проходят испытательный срок.</p>',
        landing=True,
    )


def message_page(
    title: str, text: str, *, error: bool = True, link: tuple[str, str] | None = None
) -> str:
    kind = "error" if error else "ok"
    role = "alert" if error else "status"
    more = (
        f'<p class="auth-message-link"><a href="{e(link[0])}">{e(link[1])} ↗</a></p>'
        if link else ""
    )
    return page(
        title,
        auth_brand()
        + '<p class="auth-eyebrow">Подключение YouGile MCP</p>'
        + f'<h1>{e(title)}</h1>'
        + f'<div class="auth-message {kind}" role="{role}">{e(text)}</div>'
        + more,
        auth_flow=True,
    )
