# Cataclysm AI — GitHub CI bootstrap

Этот репозиторий нужен только для серверной сборки Cataclysm: Bright Nights с Cataclysm AI Bridge.

## Что делает GitHub Actions

1. Скачивает свежий `cataclysmbn/Cataclysm-BN`.
2. Применяет минимальный C++ bridge только к `src/catalua_bindings.cpp`.
3. Устанавливает Lua/JSON мод Cataclysm AI.
4. Собирает Windows x64 Tiles+Sound на runner `windows-2022`.
5. Загружает готовую сборку как artifact `CataclysmBN-CataclysmAI-Windows`.

Локальная компиляция НЕ требуется.

## После успешной сборки

Открыть GitHub:
Actions -> Build Cataclysm AI for Windows -> последний успешный run -> Artifacts

Скачать `CataclysmBN-CataclysmAI-Windows`.

Внутри готовой сборки:
`data/mods/CataclysmAI/server/start_echo_server.bat`

Сначала запускается echo server, затем игра.

Версия 0.1 специально использует ECHO вместо настоящего LLM:
сначала проверяется полный транспорт BN -> внешний процесс -> BN.
