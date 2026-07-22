# Практикум 3. LiF: full CI, ППЭ и перезарядка

## Цель

Построить три нижние потенциальные поверхности LiF методом полного конфигурационного взаимодействия, определить мультиплетность состояний, исследовать область перезарядки и оценить энергию диссоциации.

## Что требуется посчитать

- Full CI/aug-cc-pVDZ surface scan трех нижних состояний LiF по координате удаления F от Li.
- Скан задается в Firefly через `$SURF DISP1=0.25 NDISP1=30 IGRP1(1)=2 IVEC1(1)=1,2 NSURF=3`, как в старом расчете `~/historical projects/prak3/LiF_CI`.
- По `LiF_CI.out` получить три нижние ППЭ, мультиплетности, изменение зарядов в области перезарядки и асимптотическую область для оценки диссоциации.

## Папка запуска

Вся серия лежит в одной папке `lif_scan`. Один файл `LiF_CI.inp` запускает весь surface scan full CI/aug-cc-pVDZ.

## Запуск

```bash
./run_all.sh
```

Расчеты используют внешний basis-файл:

```text
shared/basis_sets/lif_aug-cc-pVDZ.lib
```

## Основные файлы

Входной файл: `lif_scan/LiF_CI.inp`.

Результаты: `lif_scan/LiF_CI.out` и `lif_scan/LiF_CI.dat` рядом с input. Для ППЭ нужны блоки `OVERALL RESULTS OF THE POTENTIAL SURFACE SCAN`; для мультиплетностей - строки `STATE ... S= ...` в full CI output.

## Что сделано

Параметры full CI и surface scan перенесены из старого `~/historical projects/prak3/LiF_CI`: `CITYP=ALDET`, `NCORE=3`, `NACT=29`, `NELS=6`, `NSTATE=3`, `GROUP=c2v`, `$SURF DISP1=0.25 NDISP1=30 IGRP1(1)=2 IVEC1(1)=1,2 NSURF=3`. Базис `aug-cc-pVDZ` подключен через внешний файл из `shared/basis_sets`. Структура оставлена как одна папка запуска и один короткий `run.sh`; по умолчанию задано `NP=10`, запуск идет через штатный Firefly/P4 `-p4pg`.
