# ttg_casino
Modulos de Control de Ingresos para Casinos

## Auditoría de Contadores de Slot (DRGT) — 18.0.0.23 (+ fixes 18.0.0.24)

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

### 18.0.0.25 — Reporte imprimible, aprobación y Operation Balance
- Botón "Imprimir Auditoría de Contadores" (PDF Carta, plantilla de Irwing): datos del archivo, cuadre de contadores,
  comparación con Caja, estado de conciliación, observaciones y firmas.
- Observaciones de Auditoría siempre visibles; obligatorias si la diferencia supera la tolerancia. Se bloquean al aprobar
  (al presentar a Contabilidad, o con "Aprobar Auditoría" en cuadres ya en Contabilidad/Cerrados). Devolver a Borrador
  quita la aprobación.
- Estado de conciliación: Sin contadores / Conciliado / Diferencia justificada / Diferencia pendiente de justificación.
- Import opcional del reporte "Operation Balance" (Overview RD$) de DRGT: llena Handpay Liability y Variación de
  Efectivo, valida que el período sea la fecha del cuadre y que su ganancia EGM y crédito en máquina coincidan con el
  Slot Analysis (detecta archivos de días distintos).
- Ajuste "Nombre Comercial" (por defecto CASINO PLATINO) para el encabezado.

### 18.0.0.26 — Rifas y Devoluciones contra el reporte de Caja de DRGT
- Tercer archivo opcional en la importación: reporte de Caja (cuentas) de DRGT. Suma la columna Movement de las cuentas
  RIFA* y DEVOLUCION*, valida el período si el archivo lo trae, y muestra Cuadre vs DRGT con su diferencia (pestaña,
  lista de cuadres y PDF). Solo marca: no cambia la fórmula (usa lo registrado por Caja) ni bloquea la aprobación.
- Billetes No Registrados se sigue digitando a mano (no está en ningún reporte de DRGT).
