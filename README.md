# Firefly Projects

Учебные и исследовательские расчёты Firefly 8.2.0.

## Структура

- `projects/` — активные проекты и практикумы.
- `src/firefly_parser/` — небольшой parser результатов Firefly/GAMESS.
- `shared/firefly/8.2.0/` — исполняемый Firefly и runtime-модули.
- `shared/basis_sets/` — внешние базисные наборы.

## Быстрый старт

Описание parser и примеры находятся в `QUICKSTART.md`.

Каждый активный проект содержит собственный `README.md` и скрипты запуска.
Результаты Firefly обычно лежат рядом с соответствующим `.inp` и имеют
расширения `.out` и `.dat`.

## Активные проекты

- `projects/01_hartree_fock/` — RHF/UHF и локализация орбиталей.
- `projects/02_h2_potential_curves/` — потенциальные кривые H₂.
- `projects/03_lif_potential_surfaces/` — поверхности LiF и CI-состояния.
- `projects/04_benzoquinones/` — pipeline для p-/o-бензохинона.
- `projects/05_markovnikov_reaction/` — поиск переходного состояния HF + C₃H₆.
- `projects/h2_method_comparison/` — сравнение RHF, UHF, MP2, UMP2 и FCI.
