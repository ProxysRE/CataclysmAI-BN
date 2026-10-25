# Контракт manifest — schema_version: 1

Версия 1 предложена конструктором; действующий runtime её пока не читает.
Изменения структуры требуют новой версии и описания миграции. Версия самой
карты `version` независима от `schema_version`.

Все координаты — локальные клетки карты: x на восток, y на юг, z вверх.
Точка — массив `[x,y,z]` целых чисел. Область — объект `min`/`max` с такими
массивами: min включён, max исключён. Для z=0 используется `[0,1)`.
Смещения в абсолютный мир здесь нет. Габариты `size=[width,height]`, `levels=[0]`.

| Поле | Смысл |
|---|---|
| location_id, version, name | Устойчивый ID, версия карты, русское имя |
| base_commit, bn_commit | Исходная проектная база и точная база движка |
| coordinates | Направления осей и включительность областей |
| blocks | terrain_id overmap, origin в локальных клетках, size каждого блока |
| zones | id, русское name, area, соседние zones и IDs connections |
| connections | id, пара zones, область прохода, kind |
| spawn_areas | id, name, zone, area, capacity, primary и fallback точки |
| spawn_pair_policy | deny_unlisted: неописанные сочетания запрещены |
| spawn_pairs | areas: ровно два ID, allowed, reason; все пока запрещены |
| extraction_areas | id, name, zone, area, approach точка, runtime_enabled=false |
| pois | id, name, zone, position доступной рабочей точки |
| loot_candidates | id, position мебели, furniture ID, соседняя interaction_from |
| doors | position, terrain ID, locked=false |
| lighting | position, furniture ID, power, runtime_verified |
| cover | ID группы объектов, terrain/furniture, areas при явной группе, свойства |
| runtime_status | not_integrated до отдельного принятия адаптером |

Зоны семантические: поперечная связь пересекает служебную галерею, а области
соединений могут включать прилегающие клетки обеих зон. Они не являются новой
таблицей terrain. `opening` означает открытый проход, `doors` — обычные двери,
`mixed_door_opening` — дверная группа с открытым обходом. Соседство двустороннее.

Вместимость — число одновременно размещаемых участников. Для каждой группы
есть три различных primary и одна fallback; менеджер обязан повторно проверять
проходимость/занятость. Fallback не даёт права увеличить группу сверх capacity.

POI обозначает место будущей деятельности, не объект с уже работающим действием.
loot_candidates не содержат предметов, цен или окончательных групп добычи.
interaction_from — доступная соседняя клетка для будущего взаимодействия.

`bullet_proof` допускает bool либо `unverified`; последнее означает отсутствие
игрового доказательства. Ни false, ни true не заменяют расчёт конкретного патрона.
`runtime_verified=false`, `allowed=false` и `runtime_enabled=false` нельзя трактовать
как готовую механику. `static_report.json` содержит отдельный предварительный
расчёт видимости/длин путей для всех сочетаний входов, а не разрешающий список.
