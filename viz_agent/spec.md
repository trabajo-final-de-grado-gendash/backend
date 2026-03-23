# Feature Specification: Agente de Visualización para Gen BI

**Created**: 16 de febrero de 2026

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generación de Gráfico Simple (Priority: P1)

El usuario proporciona un request en lenguaje natural para crear una visualización básica de datos (ej: "gráfico de barras de ventas por mes"), y el agente debe generar automáticamente el código Plotly correspondiente y el JSON de la visualización.

**Why this priority**: Este es el caso de uso fundamental que demuestra la capacidad básica del agente. Sin esta funcionalidad, el sistema no tiene valor. Representa el MVP que puede ser probado y demostrado independientemente.

**Independent Test**: Puede ser probado proporcionando un DataFrame de Chinook, un input simple del usuario (ej: "ventas por género"), y verificando que se genere código Plotly ejecutable y un JSON válido del gráfico.

**Acceptance Scenarios**:

1. **Scenario**: Usuario solicita gráfico de barras básico
   - **Given** un DataFrame con datos de ventas de Chinook y una lista de gráficos disponibles (bar, line, pie, scatter, histogram, heatmap, box)
   - **When** el usuario ingresa "quiero un gráfico de barras de ventas totales por género"
   - **Then** el agente debe:
     - Analizar el DataFrame y el input del usuario
     - Decidir usar un gráfico de barras
     - Generar código Python con Plotly (`plotly.express` o `plotly.graph_objects`)
     - Ejecutar el código para validar que funcione
     - Retornar el código ejecutable y el JSON de la figura (`fig.to_json()`)

2. **Scenario**: Usuario solicita gráfico de líneas temporal
   - **Given** un DataFrame con datos temporales de Chinook
   - **When** el usuario ingresa "mostrar ventas por mes en los últimos 12 meses"
   - **Then** el agente debe:
     - Identificar que es una serie temporal
     - Decidir usar un gráfico de líneas
     - Generar código Plotly con el eje X como fecha/mes
     - Validar la ejecución del código
     - Retornar código y JSON

3. **Scenario**: Usuario solicita gráfico de torta
   - **Given** un DataFrame con datos categóricos
   - **When** el usuario ingresa "distribución porcentual de ventas por artista"
   - **Then** el agente debe:
     - Identificar que requiere proporciones/porcentajes
     - Decidir usar un gráfico de torta (pie chart)
     - Generar código Plotly apropiado
     - Validar y retornar código + JSON

---

### User Story 2 - Validación y Corrección Automática de Código (Priority: P2)

El agente debe validar automáticamente que el código generado se ejecute sin errores, y en caso de fallo, debe autocorregirse hasta 5 veces antes de devolver un error al usuario.

**Why this priority**: La robustez del agente es crítica para la experiencia del usuario. Sin validación automática, podríamos entregar código que falla, lo cual rompe la confianza en el sistema.

**Independent Test**: Puede ser probado inyectando errores intencionalmente en el código generado o proporcionando inputs ambiguos, y verificando que el agente corrija automáticamente.

**Acceptance Scenarios**:

1. **Scenario**: Código generado con error de sintaxis
   - **Given** el agente genera código con un error de sintaxis (ej: paréntesis sin cerrar)
   - **When** intenta validar ejecutando el código
   - **Then** debe:
     - Detectar el error de sintaxis
     - Capturar el mensaje de error
     - Enviar el error a Gemini 2.5 Flash para corrección
     - Reintentar hasta 5 veces
     - Si se corrige, retornar código + JSON
     - Si falla 5 veces, retornar error descriptivo

2. **Scenario**: Error en runtime por incompatibilidad de tipos
   - **Given** el código intenta usar una columna numérica como categórica
   - **When** se ejecuta el código
   - **Then** debe:
     - Capturar el error en runtime
     - Enviar contexto del error y del DataFrame a Gemini
     - Recibir código corregido
     - Validar nuevamente
     - Continuar hasta éxito o 5 intentos

3. **Scenario**: Código genera gráfico vacío
   - **Given** el código se ejecuta sin errores pero genera una figura sin datos
   - **When** el agente valida el resultado
   - **Then** debe:
     - Detectar que el gráfico está vacío o no es válido
     - Solicitar corrección a Gemini
     - Reintentar hasta generar un gráfico con datos

---

### User Story 3 - Soporte para Múltiples Variables y Subplots (Priority: P3)

El usuario puede solicitar visualizaciones más complejas con múltiples variables o múltiples gráficos en la misma figura (subplots), y el agente debe determinar la mejor forma de representarlos según el contexto.

**Why this priority**: Extiende la funcionalidad básica para casos de uso más sofisticados. Es importante pero no crítico para el MVP inicial.

**Independent Test**: Puede ser probado solicitando "comparar ventas por mes Y por género" y verificando que el agente genere subplots o gráficos con múltiples series según corresponda.

**Acceptance Scenarios**:

1. **Scenario**: Usuario solicita comparar dos métricas
   - **Given** un DataFrame con múltiples métricas
   - **When** el usuario ingresa "comparar ventas y cantidad de órdenes por mes"
   - **Then** el agente debe:
     - Decidir si usar subplots (dos gráficos) o doble eje Y
     - Generar código Plotly con `make_subplots` o `secondary_y`
     - Validar que ambas métricas se visualicen correctamente

2. **Scenario**: Usuario solicita desglose multidimensional
   - **Given** un DataFrame con datos categóricos y temporales
   - **When** el usuario ingresa "ventas por mes separado por género"
   - **Then** el agente debe:
     - Decidir usar múltiples líneas en un mismo gráfico (color por género)
     - O generar subplots (un gráfico por género)
     - Basarse en el contexto y cantidad de categorías

3. **Scenario**: Usuario solicita dashboard con múltiples gráficos
   - **Given** un input complejo que requiere varios gráficos
   - **When** el usuario ingresa "dashboard con ventas por mes, distribución por género, y top 10 artistas"
   - **Then** el agente debe:
     - Generar código con `make_subplots` de Plotly
     - Crear 3 subplots con diferentes tipos de gráficos
     - Validar que todos se rendericen correctamente

---

### User Story 4 - Personalización Visual según Input del Usuario (Priority: P3)

El usuario puede especificar preferencias visuales (colores, títulos, etiquetas) en su request, y el agente debe aplicarlas al código generado.

**Why this priority**: Mejora la experiencia del usuario permitiendo customización, pero no es esencial para la funcionalidad core.

**Independent Test**: Solicitar "gráfico de barras de ventas en color azul con título 'Reporte Q1'" y verificar que el código generado incluya esos estilos.

**Acceptance Scenarios**:

1. **Scenario**: Usuario especifica color
   - **Given** un request con especificación de color
   - **When** el usuario ingresa "gráfico de líneas de ventas en color rojo"
   - **Then** el código generado debe incluir `color='red'` o equivalente en Plotly

2. **Scenario**: Usuario especifica título y labels
   - **Given** un request con preferencias de texto
   - **When** el usuario ingresa "barras de ventas con título 'Ventas Mensuales' y eje Y 'Monto en USD'"
   - **Then** el código debe incluir:
     - `title='Ventas Mensuales'`
     - `labels={'y': 'Monto en USD'}`

3. **Scenario**: Usuario no especifica estilos
   - **Given** un request sin preferencias visuales
   - **When** el usuario ingresa "gráfico de ventas por mes"
   - **Then** el agente debe:
     - Aplicar estilos por defecto razonables
     - Incluir título descriptivo basado en los datos
     - Usar paleta de colores estándar de Plotly

---

### Edge Cases

- ¿Qué pasa cuando el DataFrame está completamente vacío?
  - **Respuesta**: El agente debe retornar un error descriptivo indicando que no hay datos para graficar
  
- ¿Qué pasa cuando todas las filas tienen valores NULL en las columnas relevantes?
  - **Respuesta**: El agente debe retornar un error indicando que las columnas seleccionadas no contienen datos válidos

- ¿Qué pasa cuando el usuario solicita graficar una columna que no existe en el DataFrame?
  - **Respuesta**: El agente debe retornar un error descriptivo indicando qué columnas están disponibles

- ¿Qué pasa cuando el usuario solicita un tipo de gráfico que no está en la lista de permitidos?
  - **Respuesta**: El agente debe seleccionar el tipo de gráfico más cercano de la lista permitida y registrarlo en el log

- ¿Qué pasa si después de 5 intentos el código sigue fallando?
  - **Respuesta**: El agente debe retornar un error con el último código generado, el mensaje de error, y sugerencias para resolver el problema manualmente

- ¿Qué pasa cuando el request del usuario es extremadamente ambiguo (ej: "muéstrame algo")?
  - **Respuesta**: El agente debe generar una visualización exploratoria por defecto (ej: primeras columnas numéricas encontradas) y registrar en el log la ambigüedad

- ¿Qué pasa cuando el DataFrame es muy grande (>100k filas)?
  - **Respuesta**: El agente debe generar el gráfico normalmente (Plotly puede manejar datasets grandes, aunque puede ser lento)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE aceptar como input un DataFrame de pandas, un string con el request del usuario, y una lista de tipos de gráficos permitidos

- **FR-002**: El sistema DEBE utilizar Gemini 2.5 Flash como modelo de lenguaje para todas las decisiones y generación de código

- **FR-003**: El sistema DEBE analizar el DataFrame (tipos de datos de columnas, valores únicos, rangos) y el input del usuario para decidir el tipo de gráfico más apropiado

- **FR-004**: El sistema DEBE generar código Python válido utilizando la librería Plotly (plotly.express o plotly.graph_objects)

- **FR-005**: El sistema DEBE validar el código generado ejecutándolo en un entorno sandbox/controlado con el DataFrame proporcionado

- **FR-006**: El sistema DEBE capturar errores de sintaxis y runtime durante la ejecución del código

- **FR-007**: El sistema DEBE implementar un mecanismo de autocorrección que permita hasta 5 reintentos en caso de que el código falle

- **FR-008**: El sistema DEBE enviar el contexto del error (mensaje de error, código que falló, información del DataFrame) a Gemini para solicitar corrección

- **FR-009**: El sistema DEBE retornar como output el código Plotly ejecutable y el JSON de la figura generada usando `fig.to_json()`

- **FR-010**: El sistema DEBE manejar casos de datos vacíos o con valores NULL retornando errores descriptivos

- **FR-011**: El sistema DEBE aplicar personalizaciones visuales (colores, títulos, etiquetas) cuando el usuario las especifique en su request

- **FR-012**: El sistema DEBE aplicar estilos visuales por defecto razonables cuando el usuario no especifique preferencias

- **FR-013**: El sistema DEBE ser capaz de generar gráficos simples (una variable) y complejos (múltiples variables, subplots) según el contexto del request

- **FR-014**: El sistema DEBE validar que las columnas solicitadas existan en el DataFrame y retornar error si no existen

- **FR-015**: El sistema DEBE generar un archivo de log para propósitos de debugging que incluya:
  - El tipo de gráfico seleccionado
  - La razón de la selección (inferida del análisis)
  - Intentos de corrección realizados
  - Errores encontrados y resueltos

- **FR-016**: El sistema DEBE restringir la generación de gráficos a los tipos incluidos en la lista de gráficos permitidos proporcionada como input

- **FR-017**: El sistema DEBE utilizar el dataset Chinook como caso de prueba durante el desarrollo y testing

### Non-Functional Requirements

- **NFR-001**: El código generado DEBE ejecutarse sin errores de sintaxis en el 99% de los casos después de las correcciones

- **NFR-002**: El agente DEBE seleccionar el tipo de gráfico correcto (según mejores prácticas de visualización de datos) en al menos el 90% de los casos

- **NFR-003**: El sistema DEBE ser extensible para trabajar con cualquier DataFrame de pandas, no solo Chinook

- **NFR-004**: El código generado DEBE seguir las mejores prácticas de Plotly y ser legible/mantenible

- **NFR-005**: El sistema DEBE manejar DataFrames con columnas de diferentes tipos (numéricos, categóricos, temporales, booleanos)

- **NFR-006**: Los logs generados DEBEN ser en formato texto plano o JSON y almacenarse en archivos locales durante la fase de pruebas

### Key Entities

- **DataFrame**: Estructura de datos de pandas que contiene los datos a visualizar. Incluye columnas de diferentes tipos (numéricos, categóricos, temporales) y filas de datos.

- **User Request**: String en lenguaje natural que describe qué visualización desea el usuario. Puede incluir especificaciones de tipo de gráfico, columnas, colores, títulos, etc.

- **Allowed Charts**: Lista de tipos de gráficos permitidos. Para este proyecto incluye: bar (barras), line (líneas), pie (torta), scatter (dispersión), histogram (histograma), heatmap (mapa de calor), box (caja y bigotes).

- **Plotly Code**: Código Python generado que utiliza la librería Plotly para crear la visualización. Debe ser ejecutable y producir una figura válida.

- **Plotly JSON**: Representación JSON de la figura de Plotly generada mediante `fig.to_json()`. Contiene toda la información de la visualización en formato serializable.

- **Validation Result**: Resultado de ejecutar el código generado. Puede ser exitoso (con la figura generada) o fallido (con mensaje de error).

- **Log Entry**: Registro de debugging que documenta las decisiones del agente, intentos de corrección, y errores encontrados durante el proceso.

- **Error Context**: Información enviada a Gemini cuando se requiere corrección, incluyendo el mensaje de error, el código que falló, y metadatos del DataFrame.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El agente debe generar código Plotly ejecutable sin errores en al menos el 99% de los casos después del proceso de validación y corrección

- **SC-002**: El agente debe seleccionar el tipo de gráfico apropiado (según mejores prácticas de visualización de datos) en al menos el 90% de los casos de prueba

- **SC-003**: El sistema debe manejar exitosamente al menos 50 requests diferentes con el dataset Chinook durante la fase de testing, cubriendo todos los tipos de gráficos permitidos

- **SC-004**: El proceso de validación y corrección automática debe resolver al menos el 85% de los errores sin intervención manual (dentro del límite de 5 reintentos)

- **SC-005**: El código generado debe ejecutarse y producir una visualización válida en menos de 10 segundos para DataFrames de hasta 10,000 filas

- **SC-006**: Los logs generados deben permitir a los desarrolladores entender las decisiones del agente en el 100% de los casos analizados

- **SC-007**: El sistema debe retornar errores descriptivos y accionables en el 100% de los casos donde no puede generar una visualización (ej: datos vacíos, columnas inexistentes)

- **SC-008**: El agente debe aplicar correctamente las personalizaciones visuales especificadas por el usuario (colores, títulos) en al menos el 95% de los casos donde se soliciten

- **SC-009**: El sistema debe ser capaz de procesar DataFrames con diferentes estructuras sin necesidad de configuración adicional (extensibilidad más allá de Chinook)
