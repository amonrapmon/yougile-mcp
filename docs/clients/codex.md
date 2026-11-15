# Подключение к Codex CLI и IDE

**Транспорты:** удалённый Streamable HTTP + OAuth или локальный stdio. **Статус:** примеры конфигурации; реальное E2E-подключение к нашему серверу ещё не подтверждено.

## Вариант 1. Удалённый MCP

После развёртывания доверенного HTTPS-сервера выполните:

```sh
codex mcp add yougile --url https://YOUR-HOST.example/mcp
codex mcp login yougile
codex mcp list
```

Замените `YOUR-HOST.example` адресом своего сервера. Команда входа запускает OAuth: авторизуйтесь в YouGile и при необходимости выберите компанию. В интерфейсе Codex можно использовать `/mcp` для просмотра зарегистрированных серверов и инструментов.

Также сервер можно добавить в `~/.codex/config.toml`:

```toml
[mcp_servers.yougile]
url = "https://YOUR-HOST.example/mcp"
```

После этого выполните `codex mcp login yougile`. Если OAuth не завершается, необходимо проверить точный redirect URI; локальные loopback callback разрешены сервером по умолчанию.

## Вариант 2. Локальный stdio

Сначала выполните [инструкцию локальной установки](local-stdio.md), включая создание приватного файла идентичности агента. Затем добавьте в `~/.codex/config.toml`:

```toml
[mcp_servers.yougile_local]
command = "/absolute/path/to/yougile-mcp/.venv/bin/yougile-mcp"
args = ["serve"]

[mcp_servers.yougile_local.env]
MCP_TRANSPORT = "stdio"
YOUGILE_COMPANY_ID = "YOUR_COMPANY_ID"
MCP_STDIO_IDENTITY_FILE = "/absolute/private/path/yougile-agent.json"
```

API-ключ `YOUGILE_API_KEY` необходимо **отдельно и безопасно** передать в окружение дочернего процесса. Не добавляйте его в файл конфигурации под контролем Git. В Windows укажите путь к `.venv\Scripts\yougile-mcp.exe` и абсолютный путь к приватному файлу идентичности.

## Проверка

Выполните `codex mcp list` и пробный разрешённый запрос на чтение данных. Наличие сервера в списке не подтверждает работоспособность всех операций.

Официальная документация: [Codex и MCP](https://developers.openai.com/codex/mcp).

[Общий обзор подключения](README.md)
