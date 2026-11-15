# Установка локального MCP по stdio

Этот режим предназначен для **локально запускаемых доверенных AI-агентов**. Он не открывает сетевой порт и не заменяет OAuth для удалённых клиентов.

## 1. Установка

Требования: Python 3.11+ и [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/amonrapmon/yougile-mcp.git
cd yougile-mcp
uv sync --locked --all-extras
uv run --locked yougile-mcp doctor
```

`Dockerfile` и `compose.yaml` в репозитории сейчас предназначены для проверки конфигурации, а не запуска публичного MCP.

## 2. Файл идентичности агента

Создайте приватный JSON-файл с **точно такой структурой**. В примере разрешено только чтение досок.

```json
{
  "subject": "my-local-agent",
  "company_id": "YOUR_COMPANY_ID",
  "scopes": ["yougile.boards.read"],
  "allowed_projects": [],
  "company_wide": true
}
```

- `company_id` должен совпадать с `YOUGILE_COMPANY_ID`.
- Разрешённые `scopes` определяются реальным манифестом `src/yougile_mcp/mcp/policy-manifest.json`. Неизвестные значения приводят к ошибке запуска.
- Если `company_wide: false`, укажите допустимые ID проектов в `allowed_projects`. Не выдавайте агенту больше прав, чем необходимо.

Путь к файлу должен быть **абсолютным**. В POSIX файл должен принадлежать пользователю, запускающему процесс, и быть доступен только владельцу:

```sh
chmod 600 /absolute/private/path/yougile-agent.json
```

Загрузчик отклоняет символические ссылки, неполный JSON, файл с небезопасными правами, превышение лимита размера и несовпадение компании.

## 3. Переменные окружения

Процессу MCP необходимо передать:

```text
MCP_TRANSPORT=stdio
MCP_AUTH_MODE=required
YOUGILE_COMPANY_ID=YOUR_COMPANY_ID
YOUGILE_API_KEY=<private value, not committed>
MCP_STDIO_IDENTITY_FILE=/absolute/private/path/yougile-agent.json
```

Храните API-ключ в защищённом хранилище секретов или окружении доверенного процесса запуска. **Не добавляйте его в Git, публичную конфигурацию агента или историю команд.** Команда `doctor` проверяет конфигурацию офлайн, не проверяет файл идентичности и не обращается к YouGile.

## 4. Запуск из AI-клиента

Настройте клиент на запуск дочернего stdio-процесса:

```text
/absolute/path/to/yougile-mcp/.venv/bin/yougile-mcp serve
```

В Windows используйте исполняемый файл `.venv\\Scripts\\yougile-mcp.exe`. MCP-клиент должен управлять стандартными потоками ввода/вывода процесса. Нельзя выводить отладочные сообщения в stdout вместо ответов протокола.

Примеры конфигурации: [Codex](codex.md), [Claude Code](claude-code.md), [Cursor](cursor.md), [VS Code](vscode.md).

## 5. Проверка

Убедитесь, что клиент видит разрешённые инструменты, и выполните операцию чтения. Ошибка `permission_denied` означает, что идентичность агента, права YouGile или политика ресурса не позволили выполнить вызов. Операциям с отдельным серверным подтверждением требуется дополнительный доверенный обработчик; stdio-хост не подключает его по умолчанию.

[Общий обзор подключения](README.md)
