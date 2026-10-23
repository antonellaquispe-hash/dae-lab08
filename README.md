# API headless — contrato, cliente de consola y frontera del agente

Repositorio del laboratorio **extra de la semana 8** de Desarrollo de Aplicaciones Empresariales (DAE).
Parte de la API de cuestionarios del Lab 8 **ya construida** (exámenes, preguntas y opciones, con Django
REST Framework) y se usa de tres maneras que no necesitan una pantalla: leyendo su **contrato** OpenAPI,
llamándola desde un **cliente de consola** y poniéndole una **frontera** a un agente de IA.

La guía del laboratorio (con su rúbrica) está en el campus virtual; aquí está el código.

## Puesta en marcha

```bash
python -m venv .venv
.venv\Scripts\activate          # en Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_quiz      # datos fijos + los usuarios «profe» y «agente», con su token
python manage.py runserver      # déjalo corriendo; el resto va en OTRA terminal
```

`seed_quiz` imprime los dos tokens (copia las líneas de tu terminal). **El de la persona (`profe`) puede
todo; el del agente (`agente`) no debe poder borrar.** Se puede repetir cuando quieras: los tokens no cambian.

En la otra terminal (PowerShell):

```powershell
$env:QUIZ_URL = "http://127.0.0.1:8000"
$env:QUIZ_TOKEN_HUMANO = "..."     # lo que imprimió seed_quiz
$env:QUIZ_TOKEN_AGENTE = "..."
$env:QUIZ_TOKEN = $env:QUIZ_TOKEN_HUMANO      # el token con el que llama quizctl (cámbialo según la prueba)
```

## Parte 1 — El contrato

La API se describe a sí misma. Abre `http://127.0.0.1:8000/api/docs/` y mira cómo cada operación declara su método,
su dirección, sus parámetros, su cuerpo y sus respuestas. Eso mismo, en formato de máquina:

```bash
python manage.py spectacular --file schema.yml
```

El contrato es lo que leen un cliente generado, la documentación y —en la Parte 4— la pasarela del agente.

## Parte 2 — El cliente de consola (de rojo a verde)

`quizctl.py` es un cliente sin pantalla. Está escrito salvo **dos funciones** marcadas `TODO(equipo)`:
el **código de salida** según el estado HTTP y el **cuerpo** de una pregunta nueva. Complétalas:

```bash
python manage.py test quiz.tests.test_quizctl
```

Ejemplos, una vez completas:

```bash
python quizctl.py exams list
python quizctl.py questions list --search select_related --json
python quizctl.py questions create --exam 1 --text "¿Qué es REST?" --choice "Un estilo:ok" --choice "Un lenguaje"
python quizctl.py --dry-run questions delete 3        # describe la petición, no la envía
python quizctl.py ops                                 # las operaciones del contrato
```

| Código | Significa |
|---|---|
| 0 | funcionó |
| 1 | otro error o mal uso |
| 2 | validación (HTTP 400) |
| 3 | no permitido (HTTP 401 o 403) |
| 4 | no existe (HTTP 404) |
| 5 | error del servidor (5xx) |
| 6 | no hay conexión |

## Parte 3 — Dos identidades, permisos en el servidor (de rojo a verde)

`quiz/permissions.py` deja pasar todo (`return True`): con el token del agente se puede **borrar**. Implementa la regla
(persona: todo; grupo «agente»: leer, crear y modificar, nunca borrar; los demás: solo leer):

```bash
python manage.py test quiz.tests.test_permissions
```

## Parte 4 — La frontera del agente

`agent/gateway.py` es una pasarela **cerrada** entre un modelo y la API. Pruébala con intenciones escritas a mano:

```bash
python -m agent --intent '{"op": "exams_list"}'
python -m agent --intent '{"op": "questions_list", "query": {"search": "prefetch"}}'
python -m agent --intent '{"op": "exams_destroy", "path": {"id": 1}}'
python -m agent --intent '"Exam.objects.all().delete()"'
python -m agent --intent '{"op": "run_sql"}'
```

Lee con atención la pregunta que contiene «IGNORA TUS INSTRUCCIONES». Para aprobar un plan hace falta el token de
**la persona** (`QUIZ_TOKEN_HUMANO`), nunca el del agente: `python -m agent --intent '...' --approve <hash>`.
Cada decisión queda en `agent_audit.jsonl`.

## Todas las pruebas

```bash
python manage.py test
```

Mientras no hayas hecho las Partes 2 y 3 fallarán las de `test_quizctl` y `test_permissions`; `test_api` y `test_agent`
pasan desde el principio.

## Estructura

| Ruta | Para qué |
|---|---|
| `quiz/` | La API: modelos, serializadores, vistas y rutas (la del Lab 8, ya hecha) |
| `quiz/permissions.py` | **Tuyo (Parte 3):** la regla de quién puede qué |
| `quizctl.py` | **Tuyo (Parte 2):** el cliente de consola; dos funciones por completar |
| `agent/` | La pasarela del agente (Parte 4) y un adaptador opcional a un modelo local |
| `quiz/tests/` | Las pruebas de cada parte |

## Convenciones del curso

Código, nombres y comentarios en inglés; explicaciones y entregables en español. PEP 8.
