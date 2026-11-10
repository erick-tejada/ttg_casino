# ttg_casino
Modulos de Control de Ingresos para Casinos

## Auditoría de Contadores de Slot (DRGT) — 18.0.0.23

- El Auditor importa el reporte "Slot Analysis" de DRGT (`.xls` XML tal como lo exporta DRGT, o `.xlsx`/`.xls`)
  desde la pestaña **Auditoría de Contadores** del cuadre, cuando Caja ya lo presentó (Auditoría, Contabilidad o
  Cerrado, para cargar días anteriores).
- Cada fila de máquina queda como `casino.slot.meter` ligada al cuadre (todas las columnas; las desconocidas en
  `extra_data`). Informe: Casino > Auditoría > Informes > Contadores de Slot (DRGT).
- Bloqueos: máquinas del archivo que no existen en Odoo, archivo ya importado en otro cuadre, suma de filas distinta
  a la fila de totales, encabezados obligatorios faltantes.
- Fórmula: NGWINE + Handpay Liability + Sobrantes − Rifas − Devoluciones + Variación de Efectivo + Billetes No
  Registrados + Crédito en Máquina (CRE). Se compara con Resultado Caja Máquina.
- Presentar a Contabilidad exige el archivo (configurable) y una justificación si la diferencia supera la
  tolerancia (RD$3 por defecto). Ajustes en Casino > Configuraciones.
