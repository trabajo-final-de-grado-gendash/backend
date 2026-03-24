# Feature Specification: Agente Decisor y API de Orquestación para Gen BI

**Feature Branch**: `TFG-13-crear-agente-decisor`
**Created**: 23 de marzo de 2026
**Status**: Draft
**Input**: User description: "Agente decisor que orquesta la generación de dashboards a través de lenguaje natural, coordinando Vanna AI (text2sql) y el agente de visualización. Luego una API REST para exponer los agentes."

## Clarifications

### Session 2026-03-23

- Q: ¿La API requiere autenticación para este sprint? → A: Sin autenticación — acceso libre en entorno local (Opción B)
- Q: ¿Qué base de datos se usa para persistencia de la API? → A: PostgreSQL — más robusta para el proyecto de tesis
- Q: ¿Cómo se implementa el flujo de clarificación interactiva? → A: El agente retorna la pregunta como respuesta; el usuario responde en el siguiente request de la misma sesión (Opción A)
- Q: ¿El agente decisor reintenta la generación SQL si Vanna AI falla? → A: Un reintento — el agente reformula el prompt y reintenta una sola vez antes de retornar error (Opción B)
- Q: Para consultas ambíguas pero válidas, ¿el agente pregunta o asume? → A: El agente pregunta de forma orientada, explicando qué no entiende y ofreciendo interpretaciones concretas posibles (Opción A)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generación de Visualización End-to-End (Priority: P1)

El usuario final envía una consulta en lenguaje natural (ej: "mostrame las ventas por mes del último año") y el sistema devuelve una visualización interactiva completa. El agente decisor es quien orquesta el flujo: interpreta la intención, coordina la generación de SQL mediante Vanna AI, ejecuta la consulta y pasa los datos al agente de visualización.

**Why this priority**: Es el flujo principal del sistema. Sin este pipeline funcionando de punta a punta, el resto no tiene valor. Representa la promesa central del producto: lenguaje natural → dashboard.

**Independent Test**: Puede ser probado enviando una consulta de texto al agente decisor con una conexión a base de datos funcional y verificando que se retorne un JSON de visualización Plotly válido y datos SQL correspondientes.

**Acceptance Scenarios**:

1. **Scenario**: Consulta simple de agregación
   - **Given** una base de datos Chinook disponible y el agente decisor inicializado
   - **When** el usuario envía "total de ventas por género de cliente"
   - **Then** el agente decisor debe:
     - Interpretar la intención de la consulta
     - Delegar la generación de SQL a Vanna AI
     - Ejecutar la consulta y obtener un DataFrame con los resultados
     - Delegar la generación del gráfico al agente de visualización
     - Retornar el JSON de la figura Plotly y el código Python generado

2. **Scenario**: Consulta con filtro temporal
   - **Given** una base de datos con datos históricos disponible
   - **When** el usuario envía "ventas mensuales del último año"
   - **Then** el agente debe:
     - Generar SQL correcto con filtro de fecha relativa
     - Obtener datos temporales en el DataFrame
     - Producir un gráfico de líneas temporal
     - Retornar resultado completo al cliente

3. **Scenario**: Consulta que retorna resultado vacío
   - **Given** la base de datos Chinook conectada
   - **When** el usuario consulta un período sin datos (ej: un año sin ventas)
   - **Then** el sistema debe retornar un mensaje descriptivo indicando que no hay datos para el período solicitado, sin fallar silenciosamente

---

### User Story 2 - Decisión Inteligente de Flujo (Priority: P2)

El agente decisor debe ser capaz de determinar si una consulta en lenguaje natural requiere acceso a datos (y por ende invocar Vanna AI + agente de visualización) o si puede ser respondida de otra forma. Debe enrutar correctamente los diferentes tipos de intención del usuario.

**Why this priority**: La inteligencia de routing es lo que diferencia un sistema robusto de un pipeline rígido. Sin esta capacidad, consultas mal formuladas o fuera de scope podrían generar errores confusos para el usuario.

**Independent Test**: Puede ser probado enviando diferentes tipos de consultas (preguntas ambiguas, consultas fuera de alcance, consultas bien formadas) y verificando que el enrutamiento sea el correcto en cada caso.

**Acceptance Scenarios**:

1. **Scenario**: Consulta totalmente fuera de alcance
   - **Given** el agente decisor configurado con el contexto de la base de datos
   - **When** el usuario envía algo completamente ajeno al análisis de datos (ej: "haceme un código en JavaScript", "qué es la relatividad?", "redactá un email")
   - **Then** el agente debe retornar una **respuesta de tipo `message`** que:
     - Indique que eso está fuera de lo que el sistema puede hacer
     - Explique brevemente qué hace el sistema (ej: "Soy un asistente especializado en visualizar datos de la base Chinook a partir de consultas en lenguaje natural")
     - Sugiera al usuario cómo reformular o qué tipo de preguntas puede hacer

2. **Scenario**: Consulta bien formada que requiere datos
   - **Given** el agente decisor y todas las dependencias activas
   - **When** el usuario envía una consulta válida sobre métricas de negocio
   - **Then** el agente debe iniciar el pipeline completo (SQL → datos → visualización) sin intervención manual

3. **Scenario**: Detección de múltiples intenciones con clarificación interactiva
   - **Given** una consulta que implica más de una visualización
   - **When** el usuario envía "ventas por mes y también top 10 artistas"
   - **Then** el agente debe:
     - Detectar que hay múltiples intenciones en la consulta
     - Retornar al cliente una **respuesta de tipo clarificación** (no una visualización) con la pregunta: "¿Desea los gráficos combinados, separados, o que el agente decida?"
     - Guardar el mensaje de clarificación en el historial de la sesión
     - En el **siguiente request del usuario** dentro de la misma sesión, interpretar la respuesta como elección de formato y ejecutar el pipeline completo con esa decisión
     - Si el usuario elige "que decida el agente", el agente selecciona el formato más apropiado según el tipo y cantidad de datos

---

### User Story 3 - API REST para Exposición del Pipeline (Priority: P2)

Los agentes deben ser accesibles a través de una API REST que permita a clientes externos (como el frontend web) enviar consultas y recibir visualizaciones. La API actúa como punto de entrada unificado al sistema.

**Why this priority**: Sin API, el sistema sólo puede usarse internamente. La API es la interfaz que conecta los agentes con el frontend y cualquier otro consumidor externo, siendo esencial para que el sprint goal ("el usuario escribe en la web y ve el gráfico") sea alcanzable.

**Independent Test**: Puede ser probado realizando llamadas HTTP a los endpoints definidos y verificando que se retornen respuestas válidas con los datos de visualización esperados.

**Acceptance Scenarios**:

1. **Scenario**: Endpoint de generación de dashboard con sesión
   - **Given** la API en ejecución con todos los agentes disponibles
   - **When** un cliente HTTP realiza un POST con `{"query": "ventas por mes", "session_id": "uuid"}` al endpoint `/generate`
   - **Then** la API debe:
     - Recibir y validar el payload
     - Recuperar el historial de los últimos 5 mensajes de la sesión desde la BD
     - Invocar el agente decisor con la consulta y el historial de contexto
     - Guardar el mensaje del usuario y la respuesta del sistema en BD
     - Persistir el resultado (SQL + viz JSON) en BD asociado al `session_id`
     - Retornar un JSON con el gráfico Plotly, el SQL generado, el `result_id` y los datos resultantes

2. **Scenario**: Manejo de errores en la API
   - **Given** la API en ejecución
   - **When** se envía un payload inválido o una consulta que el agente no puede resolver
   - **Then** la API debe retornar un error HTTP con código apropiado (400 o 422) y un mensaje descriptivo del problema

3. **Scenario**: Estado de salud del sistema
   - **Given** la API y los agentes desplegados
   - **When** se realiza un GET al endpoint `/health`
   - **Then** la API debe retornar el estado de disponibilidad de cada componente (agente decisor, Vanna AI, agente de visualización)

---

### User Story 4 - Integración y Wrapper de Agentes (Priority: P3)

El sistema debe tener un wrapper unificado que permita importar y usar los agentes (decisor, Vanna AI, visualización) de forma desacoplada, facilitando el testing, el reemplazo de componentes y la evolución del sistema.

**Why this priority**: El wrapper no aporta valor al usuario final directamente, pero es fundamental para la mantenibilidad del backend y para que los subtasks de Jira (TFG-16 "Wrapper de Agentes" y TFG-40 "Importar agentes") queden correctamente implementados.

**Independent Test**: Puede ser probado instanciando cada agente a través del wrapper y verificando que las interfaces sean consistentes y que los agentes sean intercambiables sin modificar el código del pipeline.

**Acceptance Scenarios**:

1. **Scenario**: Instanciación del agente decisor via wrapper
   - **Given** el módulo wrapper disponible
   - **When** se importa y se instancia el agente decisor desde el wrapper
   - **Then** el agente debe estar listo para recibir consultas sin configuración adicional

2. **Scenario**: Intercambio de implementación de agente
   - **Given** el wrapper con interfaz definida
   - **When** se reemplaza la implementación del agente de visualización por una alternativa
   - **Then** el pipeline completo debe seguir funcionando sin cambios en el código de orquestación

---

### User Story 5 - Persistencia de Resultados de Visualización (Priority: P2)

Cada vez que el pipeline completo llega a generar una visualización exitosa, el sistema debe guardar automáticamente el resultado (consulta original, SQL generado, JSON de visualización) en base de datos. Esto permite recuperar dashboards previos y construir un historial de análisis.

**Why this priority**: La persistencia habilita la trazabilidad de lo que el sistema generó, es requisito para implementar historial de sesión, y tiene alto valor demostrativo para la tesis. Sin ella, cada visualización se pierde al terminar el request.

**Independent Test**: Puede ser probado ejecutando una consulta exitosa y luego consultando la BD para verificar que el resultado fue persistido con todos los campos esperados.

**Acceptance Scenarios**:

1. **Scenario**: Resultado guardado tras pipeline exitoso
   - **Given** una consulta que produce una visualización exitosa
   - **When** la API recibe la respuesta del agente de visualización
   - **Then** la API debe guardar en BD: query original, SQL generado, JSON Plotly, session_id y timestamp; y retornar el `result_id` al cliente

2. **Scenario**: Fallo en pipeline no genera persistencia
   - **Given** una consulta que falla en alguna etapa del pipeline
   - **When** la API recibe el error del agente decisor
   - **Then** NO se debe guardar ningún resultado en BD; sólo se guarda el mensaje de error en el historial de conversación

3. **Scenario**: Recuperación de resultado previo
   - **Given** un `result_id` válido
   - **When** el cliente consulta `/results/{result_id}`
   - **Then** la API debe retornar el JSON Plotly, el SQL y la query original del resultado guardado

---

### User Story 6 - Historial de Conversación con Contexto (Priority: P2)

El sistema mantiene el historial de mensajes de cada sesión de usuario en base de datos y lo utiliza como contexto para el agente decisor. Esto permite consultas de refinamiento natural como "el mismo gráfico pero por año" o "ahora filtrado por Argentina".

**Why this priority**: Sin contexto conversacional, el sistema fuerza al usuario a repetir información en cada consulta. La memoria de sesión es lo que transforma un pipeline de una sola vuelta en una experiencia de análisis iterativo, que es el valor diferencial del producto.

**Independent Test**: Puede ser probado enviando una secuencia de dos consultas relacionadas en la misma sesión y verificando que la segunda consulta se resuelve correctamente usando el contexto de la primera.

**Acceptance Scenarios**:

1. **Scenario**: Consulta de refinamiento con historial
   - **Given** una sesión donde el usuario previamente consultó "ventas por mes"
   - **When** el mismo usuario envía "ahora el mismo pero por año" en la misma sesión
   - **Then** el agente decisor debe usar el historial de contexto para entender a qué se refiere "el mismo" y generar el SQL correcto

2. **Scenario**: Sesión nueva sin historial
   - **Given** un `session_id` nuevo o no enviado
   - **When** el usuario envía su primera consulta
   - **Then** la API genera un `session_id` nuevo si no se proporcionó, procesa la consulta sin contexto previo y retorna el `session_id` al cliente para uso futuro

3. **Scenario**: Recuperación del historial de sesión
   - **Given** un `session_id` con múltiples interacciones previas
   - **When** se consulta GET `/sessions/{session_id}/history`
   - **Then** la API retorna todos los mensajes de la sesión ordenados cronológicamente con su `role` (user/system) y `timestamp`

---

### Edge Cases

- ¿Qué pasa cuando Vanna AI no puede generar SQL para la consulta?
  - **Respuesta**: El agente decisor reformula el prompt con más contexto y reintenta **una sola vez**. Si el segundo intento también falla, retorna un error descriptivo al usuario indicando que no fue posible interpretar la consulta y sugiere reformularla

- ¿Qué pasa cuando Vanna AI genera SQL con operaciones destructivas (`DELETE`, `DROP`, `UPDATE`, etc.)?
  - **Respuesta**: La capa de validación de SQL DEBE interceptar y rechazar la consulta **antes de ejecutarla**, sin importar por qué se generó. El sistema retorna un error descriptivo al usuario y registra el intento bloqueado en el log. El agente nunca ejecuta SQL que no sea `SELECT` contra Chinook, bajo ninguna circunstancia.

- ¿Qué pasa cuando el SQL generado retorna un error de base de datos?
  - **Respuesta**: El agente decisor debe detectar el error de ejecución SQL, reintentarlo con una corrección automática o informar al usuario con contexto suficiente para reformular

- ¿Qué pasa cuando el DataFrame resultante del SQL está vacío?
  - **Respuesta**: El agente decisor debe retornar un mensaje indicando que la consulta no produjo datos, sin intentar generar una visualización vacía

- ¿Qué pasa cuando el agente de visualización falla después de 5 reintentos?
  - **Respuesta**: El agente decisor debe propagar el error con contexto (SQL generado, datos obtenidos, error de visualización) para facilitar el debugging

- ¿Qué pasa cuando la API recibe múltiples requests concurrentes?
  - **Respuesta**: Cada request se procesa de forma independiente; el sistema debe soportar al menos 5 solicitudes concurrentes sin degradación

- ¿Qué pasa cuando la conexión a la base de datos no está disponible?
  - **Respuesta**: La API debe retornar un error 503 con mensaje claro indicando que el servicio de datos no está disponible

- ¿Qué pasa cuando el usuario no especifica el tipo de gráfico?
  - **Respuesta**: El agente de visualización elige el tipo de gráfico más apropiado según los datos; el agente decisor no debe imponer restricciones en este caso

- ¿Qué pasa cuando el request del usuario es válido pero ambiguo (ej: "dame algo de ventas")?
  - **Respuesta**: El agente retorna una **respuesta de tipo `clarification`** explicando qué parte no entiende y ofreciendo al menos dos interpretaciones concretas posibles (ej: "¿Por ventas totales, por mes o por género?"). Si la respuesta del usuario sigue siendo ambigua, el agente procede con la interpretación que considera más razonable e informa al usuario qué asumió. El agente **nunca pregunta dos veces seguidas** sobre la misma ambigüedad.

- ¿Qué pasa cuando el usuario envía un saludo o mensaje social (ej: "hola", "gracias", "sos un bot?")?
  - **Respuesta**: El agente responde en tono amigable con una **respuesta de tipo `message`** y orienta al usuario hacia una consulta de datos (ej: "¡Hola! Puedo ayudarte a visualizar información de la base de datos Chinook. ¿Qué te gustaría analizar?"). No inicia el pipeline ni pide clarificación.

- ¿Qué pasa cuando el `session_id` enviado no existe en la BD?
  - **Respuesta**: La API lo trata como una sesión nueva: crea el registro de sesión y procesa la consulta sin historial previo

- ¿Qué pasa cuando la BD de persistencia no está disponible al momento de guardar un resultado?
  - **Respuesta**: El pipeline completa igualmente y retorna la visualización al cliente; el sistema registra el fallo de persistencia en el log de orquestación y continúa operando en modo degradado

- ¿Qué pasa si el historial de una sesión tiene mensajes muy antiguos que ya no son relevantes?
  - **Respuesta**: El sistema utiliza sólo los últimos 5 mensajes como ventana de contexto, ignorando mensajes anteriores; el historial completo sigue disponible en BD vía el endpoint `/sessions/{session_id}/history`

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE aceptar consultas en lenguaje natural como único input del usuario y devolver una visualización completa sin pasos intermedios expuestos al usuario

- **FR-002**: El agente decisor DEBE interpretar la intención de la consulta del usuario y determinar si el pipeline de datos (SQL → datos → visualización) debe ser activado

- **FR-003**: El agente decisor DEBE invocar a Vanna AI para convertir la consulta en lenguaje natural a SQL válido compatible con la base de datos Chinook. Si Vanna AI falla, el agente DEBE reformular el prompt con más contexto y reintentar **una sola vez**; si el reintento también falla, retorna un error descriptivo al usuario

- **FR-004**: El sistema DEBE implementar una capa de validación de SQL que se ejecute **siempre, antes de toda ejecución contra Chinook**. Esta capa DEBE:
  - Parsear la consulta SQL y rechazar cualquiera que contenga operaciones `DELETE`, `DROP`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, `REPLACE` u otras operaciones no-`SELECT`
  - Retornar un error descriptivo indicando que el sistema sólo permite consultas de lectura y registrar el intento bloqueado en el log
  - Esta validación es una salvaguarda de última línea ineludible. Si es exitosa, el agente decisor ejecuta el SQL generado por Vanna.

- **FR-005**: El agente decisor DEBE invocar al agente de visualización con el DataFrame obtenido y la consulta original del usuario como contexto

- **FR-006**: El agente decisor DEBE recibir el código Plotly y el JSON de figura del agente de visualización y retornarlos como parte de la respuesta final

- **FR-007**: El agente decisor DEBE manejar fallos en cualquier etapa del pipeline (generación SQL, ejecución SQL, visualización) con mensajes de error descriptivos

- **FR-008**: El agente decisor DEBE registrar en un log las decisiones tomadas, los tiempos de ejecución de cada etapa y los errores encontrados

- **FR-009**: La API REST DEBE exponer un endpoint POST `/generate` que reciba una consulta en texto y retorne el JSON de visualización Plotly, el SQL generado y el DataFrame resultante

- **FR-010**: La API REST DEBE exponer un endpoint GET `/health` que retorne el estado de disponibilidad de cada componente del sistema

- **FR-011**: La API REST DEBE validar los payloads de entrada y retornar errores HTTP con códigos apropiados (400 para payload inválido, 503 para servicio no disponible, 500 para errores no previstos)

- **FR-012**: La API REST DEBE soportar CORS para permitir su consumo desde el frontend web

- **FR-013**: El sistema DEBE contar con un wrapper o módulo de integración que permita instanciar y coordinar los tres agentes (decisor, Vanna AI, visualización) de forma desacoplada

- **FR-014**: El agente decisor DEBE clasificar toda consulta entrante en una de cuatro categorías y actuar en consecuencia:
  1. **Válida y clara** — inicia el pipeline completo (SQL → datos → visualización)
  2. **Válida pero ambígua** — retorna una respuesta `clarification` explicando qué no entiende y ofreciendo al menos dos interpretaciones posibles; si la respuesta siguiente sigue siendo ambígua, asume la más razonable e informa al usuario; **máximo una ronda de clarificación por ambigüedad**
  3. **Fuera de alcance** (pedidos que el sistema no puede ni debe atender: escribir código, responder preguntas generales, tareas no relacionadas con datos) — retorna una respuesta `message` que explica qué hace el sistema, qué tipos de consultas acepta y sugiere cómo reformular. **El agente nunca responde la tarea fuera de alcance aunque pueda hacerlo**; su función es exclusivamente la visualización de datos
  4. **Conversacional / social** (saludos, agradecimientos, chit-chat) — retorna una respuesta `message` en tono amigable y orienta al usuario hacia una consulta de datos (ej: "¡Hola! Puedo ayudarte a visualizar datos de Chinook. ¿Qué te gustaría analizar?")

- **FR-015**: El sistema DEBE utilizar el dataset Chinook como caso de prueba de referencia durante el desarrollo y testing de integración

- **FR-016**: La API DEBE aceptar un campo opcional `session_id` en el request del endpoint `/generate`; si no se proporciona, DEBE generarlo automáticamente y retornarlo en la respuesta

- **FR-017**: La API DEBE recuperar los últimos 5 mensajes de la sesión desde la BD antes de invocar al agente decisor, y pasarlos como contexto conversacional

- **FR-018**: La API DEBE guardar cada mensaje del usuario y cada respuesta del sistema en BD, asociados al `session_id` y con un `timestamp`, independientemente de si el pipeline fue exitoso o no

- **FR-019**: La API DEBE guardar en BD el resultado completo del pipeline (query original, SQL generado, JSON de visualización Plotly, `session_id`, `timestamp`) únicamente cuando el agente de visualización retorne éxito

- **FR-020**: La API REST DEBE exponer un endpoint GET `/sessions/{session_id}/history` que retorne el historial de mensajes de una sesión ordenados cronológicamente

- **FR-021**: La API REST DEBE exponer un endpoint GET `/results/{result_id}` que retorne el resultado de visualización guardado para un `result_id` dado

- **FR-022**: El fallo de persistencia en BD NO DEBE interrumpir la respuesta al cliente; el sistema DEBE operar en modo degradado y registrar el fallo en el log

- **FR-023**: La respuesta del endpoint `/generate` DEBE indicar su tipo mediante un campo `response_type` con tres valores posibles:
  - `"visualization"`: el pipeline produjo un gráfico válido
  - `"clarification"`: el agente necesita más información antes de continuar (consulta ambígua o múLTiples intenciones)
  - `"message"`: el agente retorna texto plano sin visualización (consulta fuera de alcance, saludo, error descriptivo)
  
  El frontend usa este campo para saber cuándo renderizar un gráfico, cuándo mostrar una pregunta de seguimiento y cuándo mostrar solo un mensaje de texto

### Non-Functional Requirements

- **NFR-001**: El pipeline completo (lenguaje natural → visualización) DEBE completarse en menos de 15 segundos para consultas sobre datasets de hasta 50,000 filas

- **NFR-002**: La API DEBE soportar al menos 5 solicitudes concurrentes sin degradación de rendimiento

- **NFR-003**: Los errores en cualquier etapa del pipeline DEBEN incluir contexto suficiente para que un desarrollador pueda reproducir y corregir el problema

- **NFR-004**: El agente decisor DEBE ser extensible para incorporar nuevas fuentes de datos o nuevos agentes especializados sin modificar el pipeline existente

- **NFR-005**: La API DEBE tener documentación de endpoints accesible (al menos un esquema de request/response por endpoint)

- **NFR-006**: La API NO requiere autenticación en este sprint; todos los endpoints son de acceso libre asumiendo un entorno de red local controlado. La autenticación queda declarada fuera del alcance del Sprint 2.

- **NFR-007**: (**Requisito de seguridad crítico**) El sistema DEBE garantizar que **ningún SQL generado por el agente pueda modificar, eliminar o alterar datos o estructura de la base de datos Chinook**. Solo se permiten operaciones `SELECT`. Esta restricción DEBE aplicarse mediante validación programada del SQL antes de cada ejecución y NO puede depender exclusivamente del comportamiento del modelo de lenguaje.

### Key Entities

- **Consulta de Usuario (User Query)**: String en lenguaje natural que describe qué información o visualización desea el usuario. Es el único input del sistema desde la perspectiva del usuario final.

- **Agente Decisor (Decisor Agent)**: Componente central de orquestación que recibe la consulta del usuario, determina el flujo de trabajo apropiado e invoca a los agentes especializados en el orden correcto.

- **Vanna AI (Text2SQL Agent)**: Componente externo que convierte consultas en lenguaje natural a SQL ejecutable, especializado en la estructura de la base de datos configurada.

- **SQL Generado**: Consulta SQL producida por Vanna AI a partir del lenguaje natural, lista para ser ejecutada contra la base de datos.

- **DataFrame de Resultados**: Estructura tabular con los datos obtenidos al ejecutar el SQL, que sirve como input al agente de visualización.

- **Agente de Visualización (Viz Agent)**: Componente ya implementado que recibe un DataFrame y una descripción en lenguaje natural y genera código Plotly y un JSON de figura.

- **Respuesta del Pipeline**: Objeto que contiene el SQL generado, los datos tabulares resultantes, el código Plotly y el JSON de la figura Plotly lista para renderizar.

- **API REST**: Interfaz HTTP que actúa como punto de entrada unificado para clientes externos (frontend web, herramientas de testing).

- **Wrapper de Agentes**: Módulo de integración que abstrae la instanciación y configuración de cada agente, permitiendo usarlos de forma desacoplada.

- **Log de Orquestación**: Registro de las decisiones, tiempos de ejecución y errores de cada invocación del pipeline, para fines de debugging y análisis.

- **Sesión (Session)**: Agrupador de interacciones de un mismo usuario o contexto de trabajo. Identificada por un `session_id` (UUID). Permite vincular múltiples consultas y sus resultados dentro de un mismo hilo conversacional.

- **Mensaje de Conversación (ConversationMessage)**: Unidad atómica del historial de sesión. Contiene el `role` (user o system), el `content` (texto de la consulta o respuesta), el `session_id` al que pertenece y el `timestamp`.

- **Resultado de Generación (GenerationResult)**: Registro persistido de un pipeline exitoso. Contiene la `query` original, el `sql` generado, el `viz_json` (JSON Plotly completo), el `session_id`, el `result_id` y el `timestamp` de creación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El pipeline completo (consulta en lenguaje natural → visualización Plotly renderizable) debe funcionar de extremo a extremo en al menos el 85% de las consultas de prueba sobre el dataset Chinook

- **SC-002**: El tiempo total de respuesta del pipeline no debe superar los 15 segundos en el percentil 90 de las consultas procesadas durante el testing

- **SC-003**: La API debe responder con códigos HTTP correctos en el 100% de los casos probados, incluyendo errores y casos de borde

- **SC-004**: El agente decisor debe enrutar correctamente (activar pipeline vs. responder sin datos) el 90% de las consultas de prueba incluyendo consultas válidas, ambiguas y fuera de alcance

- **SC-005**: El sistema debe poder procesar al menos 30 consultas distintas de extremo a extremo durante la fase de integración sin errores no manejados

- **SC-006**: El frontend web debe poder consumir la API y renderizar el gráfico resultante para al menos 10 consultas distintas sin intervención manual

- **SC-007**: Los logs generados deben permitir reconstruir el flujo completo de cada invocación en el 100% de los casos, incluyendo qué agente fue invocado, con qué parámetros y con qué resultado

- **SC-008**: El endpoint `/health` debe reflejar el estado real de cada componente con una latencia menor a 1 segundo

- **SC-009**: El 100% de los pipelines exitosos deben resultar en un registro persistido en BD recuperable a través del endpoint `/results/{result_id}`

- **SC-010**: El agente decisor debe resolver correctamente al menos el 80% de las consultas de refinamiento conversacional (ej: "el mismo pero por año") cuando se le proporciona el historial de los últimos 5 mensajes de la sesión

## Assumptions

- Vanna AI ya está configurado para conectarse a la base de datos Chinook y tiene suficiente contexto de esquema para generar SQL relevante
- El agente de visualización (viz_agent) ya está implementado y tiene una interfaz estable que acepta DataFrame + query string y retorna código Plotly + JSON
- La base de datos Chinook estará disponible en el entorno de desarrollo para todas las pruebas de integración
- El frontend web ya existe o está siendo desarrollado en paralelo y consumirá la API REST en formato JSON; es responsabilidad del frontend enviar y almacenar el `session_id` entre requests
- La API se ejecutará en un entorno local durante el Sprint 2; el despliegue en producción no es parte de este alcance
- CORS deberá estar habilitado para el origen del frontend (localhost durante desarrollo)
- Los logs se almacenarán en archivos locales durante la fase de pruebas; no se requiere sistema de logging centralizado en este sprint
- La persistencia de sesiones, mensajes y resultados de generación se realizará en una base de datos **PostgreSQL** propia de la API, separada de Chinook
- La ventana de contexto conversacional es de 5 mensajes; este valor puede ajustarse en el plan técnico según las limitaciones del modelo
