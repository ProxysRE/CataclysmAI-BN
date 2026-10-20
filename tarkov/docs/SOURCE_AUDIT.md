# Использование готовых механизмов

## Источники

- BN: `cataclysmbn/Cataclysm-BN@554950f3635f50ddd1d32c6e1b6e2bdee9842bd6`.
- Sky Island BN: `graysonchao/CBN-Sky-Island@9e2f4606f37b1f006ddd70a52d25acfff8b2eb33`.
- DDA Sky Island: `CleverRaven/Cataclysm-DDA@9d42bf0f33c15f73421967f661bd4bde0af506a2`.

Sky Island создан TGWeaver; BN-порт опубликован graysonchao. Мы изучали его как
пример использования API. DEV0.1 не включает его карты, тексты, предметы или Lua-файлы.
При дальнейшем прямом заимствовании проверять лицензии и сохранять авторство.

## Берём из движка BN

- `src/catalua_bindings_game.cpp`: dimension travel, bounds/layout, reset/delete, current time.
- `tests/lua/pocket_dimension_api_test.lua`: штатные примеры и ограничения API.
- `src/catalua_bindings_creature.cpp`: инвентарь, HP и drop_all_items.
- `src/catalua_hooks.cpp`: события старта/загрузки/смерти.
- `src/game.cpp`: очистка измерения с внутренним сохранением игры.
- `src/catalua.cpp` / `src/catalua_serde.cpp`: восстановление storage, замена
  вложенных таблиц и запуск load hooks.
- `src/game.cpp::load` / `data/json/world_types.json`: восстановление типа измерения
  по save_prefix. Наш тип пространства использует префикс имён наших измерений.
- Штатный JSON mapgen и `lua:` действия мебели.

## Уроки Sky Island

- Можно реализовать базовый цикл и улучшения через Lua/JSON.
- BN-порт отправляет в обычный мир; наш прототип использует отдельное измерение.
- Не повторяем распознавание квестов по отображаемому имени.
- Не пересоздаём произвольное снаряжение по item ID.
- Не отмечаем постройку выполненной до проверки фактического результата.
- DDA-контейнеры используют pockets/integrated armor; перенос в BN не объявляем готовым.

## Изменения движка

В DEV0.1 нет патчей C++ игровых механик. Native harness добавляется только к тестам
во временном checkout. Расширять движок будем после воспроизводимого ограничения API.
