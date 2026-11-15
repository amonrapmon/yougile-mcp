# Подключение к Claude Code

**Транспорты:** удалённый Streamable HTTP + OAuth либо локальный stdio. **Статус:** примеры конфигурации без подтверждённого E2E с нашим сервером.

## Удалённый MCP

```sh
claude mcp add --transport http yougile https://YOUR-HOST.example/mcp
claude mcp list
```

Замените адрес на URL реально развёрнутого HTTPS-сервера. Запустите `/mcp` в Claude Code, откройте подключение и завершите вход через браузер. Авторизация выполняется под личной учётной записью YouGile, с выбором компании при необходимости.

Сервер разрешает локальные loopback callback по умолчанию. Если Claude использует другой адрес возврата OAuth, оператор должен добавить только этот доверенный origin.

## Локальный stdio

Выполните [локальную установку](local-stdio.md), настройте защищённый файл идентичности и приватную передачу `YOUGILE_API_KEY`. После этого:

```sh
claude mcp add --transport stdio yougile-local -- /absolute/path/to/yougile-mcp/.venv/bin/yougile-mcp serve
```

Дочернему процессу должны быть переданы `MCP_TRANSPORT=stdio`, `YOUGILE_COMPANY_ID`, `YOUGILE_API_KEY`, `MCP_STDIO_IDENTITY_FILE`. Без них сервер не запустится. В Windows используйте полный путь к `.venv\Scripts\yougile-mcp.exe`.

Проверьте подключение через `claude mcp list` или `/mcp` и сначала выполните операцию чтения.

Официальная документация: [Claude Code MCP](https://code.claude.com/docs/en/mcp).

[Общий обзор подключения](README.md)
