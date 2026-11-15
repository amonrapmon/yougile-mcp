<p align="right"><strong>Русский</strong> · <a href="README.en.md">English</a></p>

<h1 align="center">YouGile MCP</h1>

<p align="center"><strong>Подключение AI-агентов к YouGile через Model Context Protocol</strong></p>

<p align="center">Единый MCP-сервер для работы с задачами, проектами, командой и другими возможностями YouGile REST API v2.</p>

<p align="center">
  <a href="https://github.com/amonrapmon/yougile-mcp/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/amonrapmon/yougile-mcp/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="LICENSE"><img alt="AGPL-3.0" src="https://img.shields.io/badge/license-AGPL--3.0-0f766e"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB">
  <img alt="72 операции REST API v2" src="https://img.shields.io/badge/REST%20API%20v2-72%20operations-555e75">
  <img alt="Pre-release" src="https://img.shields.io/badge/status-pre--release-a16207">
</p>

<p align="center">
  <a href="#возможности">Возможности</a> ·
  <a href="#подключение">Подключение</a> ·
  <a href="#быстрый-старт">Быстрый старт</a> ·
  <a href="#архитектура">Архитектура</a> ·
  <a href="#документация">Документация</a>
</p>

---

> [!IMPORTANT]
> **Проект готовится к публичному выпуску.** Локальный stdio и приватный OAuth-сервер на Streamable HTTP реализованы. Публичное HTTPS-развёртывание и сквозные проверки с конкретными AI-клиентами ещё продолжаются. Готового общедоступного адреса подключения пока нет.

## Возможности

### Рабочее пространство

**Проекты, доски и колонки:** чтение и изменение структуры рабочего пространства через официальный REST API.

**Задачи:** поиск, просмотр, создание и изменение задач и связанных данных.

### Команда и коммуникации

**Пользователи, роли и отделы:** доступ к поддерживаемым данным о сотрудниках и структуре компании.

**Чаты и сообщения:** операции с групповыми чатами и сообщениями YouGile.

### Интеграции и администрирование

**CRM, файлы и вебхуки:** поддерживаемые операции CRM, загрузка вложений, управление вебхуками.

**Управление доступом к MCP:** подключения сотрудников, блокировки, отзыв доступа, отдельная панель оператора хостинга.

<details>
<summary><strong>Что означает поддержка 72 операций API?</strong></summary>

Сервер регистрирует **72 прямых MCP-инструмента**, соответствующих официальным операциям YouGile REST API v2. Это не 72 готовых высокоуровневых AI-сценария: составные действия и специализированные агентские инструменты развиваются отдельно.

Наличие инструмента в каталоге не гарантирует его выполнение. Права пользователя, политики сервера и обязательные подтверждения проверяются при каждом вызове. Операции, которым необходим отсутствующий серверный механизм подтверждения или работы с секретами, блокируются.

Подробнее: [архитектура](docs/ARCHITECTURE.md) · [проверки REST API](docs/verification/gen-229-live-e2e.md) · [происхождение контракта](docs/PROVENANCE.md).

</details>

## Подключение

Выберите способ подключения в зависимости от того, где работает ваш AI-клиент.

### Удалённый сервер · Streamable HTTP + OAuth

Для ChatGPT, Codex, Claude, Cursor и VS Code. Пользователь входит через свою учётную запись YouGile и выбирает компанию. Пример адреса после собственного проверенного развёртывания:

`https://YOUR-HOST.example/mcp`

**Инструкции по клиентам**

[ChatGPT](docs/clients/chatgpt.md) ·
[Codex CLI / IDE](docs/clients/codex.md) ·
[Claude Code](docs/clients/claude-code.md) ·
[Claude Web / Desktop](docs/clients/claude.md) ·
[Cursor](docs/clients/cursor.md) ·
[VS Code / GitHub Copilot](docs/clients/vscode.md)

> Адрес выше приведён только для примера. Текущие Dockerfile и Compose не публикуют MCP наружу.

### Локальный сервер · stdio

Для агентов, запускающих MCP-процесс на своём компьютере. Использует API-ключ YouGile, ID компании и отдельный защищённый файл идентичности агента.

**[Пошаговая установка локального stdio →](docs/clients/local-stdio.md)**

Сравнение способов подключения, требования к OAuth и типовые ошибки: **[руководство по AI-клиентам](docs/clients/README.md)**.

## Быстрый старт

Нужны **Python 3.11+** и [uv](https://docs.astral.sh/uv/).

~~~bash
git clone https://github.com/amonrapmon/yougile-mcp.git
cd yougile-mcp

uv sync --locked --all-extras
uv run --locked yougile-mcp doctor
~~~

Команда `doctor` проверяет конфигурацию **офлайн** и не подключается к YouGile. Для запуска рабочего локального MCP настройте идентичность и учётные данные согласно [инструкции stdio](docs/clients/local-stdio.md).

<details>
<summary><strong>Проверка каталога, тесты и линтер</strong></summary>

~~~bash
uv run --locked python scripts/check_catalog.py
uv run --locked python -m unittest discover -s tests -v
uv run --locked ruff check .
~~~

Полный набор проверок, включая контракты агентов, описан в [AGENTS.md](AGENTS.md).

</details>

## Архитектура

~~~mermaid
flowchart LR
    L["Локальные AI-агенты"] --> S["stdio"]
    R["Удалённые AI-клиенты"] --> H["Streamable HTTP + OAuth"]
    subgraph MCP["YouGile MCP"]
        S --> T["Реестр инструментов"]
        H --> T
        T --> P["Права · политики · валидация"]
        P --> C["Единый API-клиент"]
    end
    C --> Y["YouGile REST API v2"]
~~~

Оба транспорта используют общий реестр инструментов и единый API-клиент. При обращении проверяются идентичность пользователя, компания, права и принадлежность ресурсов. Ошибки нормализуются, секреты не передаются в ответы инструментов.

В серверном режиме OAuth привязан к личной учётной записи YouGile. Доступ предоставляется **в пределах полномочий пользователя**; настройка OAuth-прав по отдельным проектам пока не реализована. PostgreSQL и Valkey используются для хранения состояния авторизации и подключений. Панель администратора компании отделена от панели оператора хостинга.

**[Подробнее об архитектуре и ограничениях →](docs/ARCHITECTURE.md)**

## Документация

**Подключение и эксплуатация**  
[AI-клиенты](docs/clients/README.md) · [Локальный stdio](docs/clients/local-stdio.md) · [Архитектура](docs/ARCHITECTURE.md)

**Самостоятельное серверное развёртывание (pre-release)**  
[Docker Compose](deploy/README.md) · [Traefik на DE](deploy/TRAEFIK-DE.md) · [Cloudflare Tunnel](deploy/CLOUDFLARE.md)

Публикация сервера требует проверки OAuth с AI-клиентом, ограничений запросов и резервного восстановления.

**Возможности и проверки**  
[Отчёт о live-проверках API](docs/verification/gen-229-live-e2e.md) · [Проверка администрирования](docs/verification/gen-231-indalo-company-admin.md) · [План развития](docs/ROADMAP.md)

**Разработка и лицензирование**  
[Contributing](CONTRIBUTING.md) · [Правила для агентов](AGENTS.md) · [Контракты](docs/contracts/README.md) · [Provenance](docs/PROVENANCE.md)

---

<sub>Исходный код распространяется по лицензии <a href="LICENSE">GNU AGPL-3.0-only</a>. Адаптированные компоненты Indalo сохраняют уведомления об авторстве. Лицензирование сторонних компонентов и статус распространения снимка OpenAPI описаны в <a href="docs/PROVENANCE.md">PROVENANCE.md</a>.</sub>
