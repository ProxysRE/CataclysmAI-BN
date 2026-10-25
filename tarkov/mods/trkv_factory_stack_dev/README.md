# Завод: многоэтажный экспериментальный макет

Отдельный debug-мод для закреплённого Cataclysm: Bright Nights. Не подключён к
рейду. Собственный world_type используется для native-теста подъёма/спуска.
Материалы условные; крыша, свет, падение и движение персонажа по лестницам
ещё требуют проверки. Полное описание и состояние проверок:
`tarkov/locations/factory_01/README.md` в репозитории CataclysmAI-BN.

Геометрические данные основаны на **Factory.svg, автор Shebuka**:
https://github.com/the-hideout/tarkov-dev-svg-maps/blob/5a8b6115d1c0cf56f2ebaac1a96fa5ae3074d178/Factory.svg

Лицензия исходной схемы и производной геометрии: **CC BY-NC-SA 4.0**.
https://creativecommons.org/licenses/by-nc-sa/4.0/
Текст лицензии находится в `LICENSE.geometry.txt`.

Изменения: дискретизация на четыре уровня, разбиение на блоки BN, условная
палитра terrain, 27 пар лестничных клеток и ограниченные воздушные объёмы цехов.
Визуальная сверка объёмов: карта re3mr Factory 1.7C, https://reemr.se/factory/.
Её текстуры и графика в игровые mapgen JSON не перенесены.
