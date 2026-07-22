# Report fragments

## Зачем сделаны single-point расчеты

Сканирование `RUNTYP=SURFACE` использовано для построения ППЭ, но такие output-файлы не содержат полного набора свойств волновой функции. Поэтому дополнительно подготовлена ветка `new_runs/single_points_properties/` с расчетами `RUNTYP=ENERGY` в отдельных характерных точках R.

Single-point точки покрывают R = 1.30-9.20 A, всего 34 расстояний.

## Выбор расстояний

Точки выбраны из `analysis/lif_all_data.csv`: минимум основного состояния около 1.60 A, область квазипересечения E3-E2 около 5.85 A, область малого E2-E1 на больших R около 9.00 A, а также диссоциационная область 8.00-9.00 A.

## Три нижние ППЭ

ППЭ построены по surface-output для состояний [1, 2, 3]; диапазон R = 0.50-9.00 A.
Графики для отчета: `lif_pes.pdf`, `lif_pes_relative_ev.pdf`, `lif_crossing_zoom.pdf`, `lif_pes_with_property_points.pdf`.

## Перезарядка

Дипольные моменты извлечены из single-point output и вынесены в `lif_single_point_properties.csv` и `lif_dipoles.pdf`.
Ведущие CI-конфигурации и коэффициенты извлечены из блоков `STATE ... ENERGY= ...` / `ALPHA | BETA | COEFFICIENT`; использовать `lif_ci_weights.pdf` и таблицу CSV.
Все напечатанные Firefly CI-коэффициенты выше порога вывода собраны в `lif_ci_coefficients_all.csv`, всего строк: 1188.
Mulliken-заряды Li/F извлечены из блока `TOTAL MULLIKEN AND LOWDIN ATOMIC POPULATIONS`; использовать `lif_charges.pdf`.

## Мультиплетность

Мультиплетность подтверждается строками `STATE ... S= ...`; значения сохранены в столбцах `s2` и `multiplicity`.

## Энергия диссоциации

Оценка энергии диссоциации записана в `dissociation_energy.csv`: минимум берется по state 1, предел - по самой дальней успешной surface-точке. Проверять устойчивость предела нужно по последним точкам R.

## Output-фрагменты для скриншотов

- `properties_audit.md`: строки output, где найдены диполи, заряды, CI-коэффициенты, natural occupations и S.
- `lif_single_point_properties.csv`: компактная таблица значений по R и state.
- `fci_basis_summary.md`: подтверждение метода FCI/ALDET, активного пространства и базиса.

## File provenance

- `extended_scan/lif_coarse.out`: status=incomplete, type=unknown, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=4.
- `lif_scan/LiF_CI.out`: status=normal, type=surface, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/scan_crossing/lif_crossing_scan.out`: status=normal, type=surface, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/scan_dissociation/lif_dissociation_scan.out`: status=normal, type=surface, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/scan_selected/lif_selected_scan.out`: status=normal, type=surface, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_1_30.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_1_40.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_1_50.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_1_60.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_1_70.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_1_80.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_4_50.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_5_00.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_5_30.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_5_50.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_5_60.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_5_65.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_5_70.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_5_75.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_5_80.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_5_85.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_5_90.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_5_95.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_6_00.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_6_05.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_6_10.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_6_20.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_6_50.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_7_00.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_7_50.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_8_00.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_8_25.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_8_50.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_8_75.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_8_80.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_8_90.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_9_00.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_9_10.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.
- `new_runs/single_points_properties/outputs/lif_sp_R_9_20.out`: status=normal, type=single_point, basis=ACC-PVDZ, functions=50, CIDET NACT=29, NELS=6, NSTATE=3.