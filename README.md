# API de cuestionarios con Django REST Framework

Este proyecto expone exámenes, preguntas y opciones como recursos HTTP. Los serializadores validan los datos recibidos, los conjuntos de vistas publican las operaciones CRUD y un enrutador registra las rutas. La API entrega opciones anidadas al consultar una pregunta y también permite administrar cada opción desde su propio recurso.

## Capacidades

- Utiliza Django REST Framework para exponer los modelos como servicio web.
- Deriva serializadores de los modelos y valida los datos entrantes, incluida la regla de una sola opción correcta por pregunta.
- Publica los recursos mediante conjuntos de vistas y un enrutador.
- Permite listar, consultar, crear, reemplazar, modificar parcialmente y eliminar recursos por HTTP.
- Filtra preguntas por examen, busca por texto y pagina las listas en grupos de cinco.
- Publica el esquema OpenAPI y una interfaz navegable.

## Requisitos y puesta en marcha

Se requiere Python 3.12 o superior.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_quiz
python manage.py runserver
```

`seed_quiz` crea datos de ejemplo y dos credenciales locales: `profe` puede realizar todas las operaciones; `agente` puede leer, crear y modificar, pero no eliminar. Copia los tokens que imprime el comando en otra terminal:

```powershell
$env:QUIZ_URL = "http://127.0.0.1:8000"
$env:QUIZ_TOKEN_HUMANO = "token de profe"
$env:QUIZ_TOKEN_AGENTE = "token de agente"
$env:QUIZ_TOKEN = $env:QUIZ_TOKEN_HUMANO
```

La API requiere `Authorization: Token <token>`. `quizctl.py` lee `QUIZ_URL` y `QUIZ_TOKEN` del entorno.

## Recursos y contrato HTTP

Las rutas usan `/api/` como prefijo. Las listas devuelven paginación con `count`, `next`, `previous` y `results`.

| Recurso | Dirección | Métodos | Cuerpo de escritura | Respuesta correcta |
|---|---|---|---|---|
| Exámenes | `/api/exams/` y `/api/exams/{id}/` | GET lista/detalle, POST, PUT, PATCH, DELETE | `{"title":"Django REST"}` | Lista/detalle: 200; POST: 201; PUT/PATCH: 200; DELETE: 204 |
| Preguntas | `/api/questions/` y `/api/questions/{id}/` | GET lista/detalle, POST, PUT, PATCH, DELETE | `{"exam":1,"text":"¿Qué es REST?","choices":[{"text":"Un estilo","is_correct":true},{"text":"Un lenguaje","is_correct":false}]}` | Lista/detalle: 200; POST: 201; PUT/PATCH: 200; DELETE: 204 |
| Opciones | `/api/choices/` y `/api/choices/{id}/` | GET lista/detalle, POST, PUT, PATCH, DELETE | `{"question":1,"text":"Una opción","is_correct":false}` | Lista/detalle: 200; POST: 201; PUT/PATCH: 200; DELETE: 204 si se conserva la regla de respuesta correcta |

En el cuerpo de una pregunta, `exam` identifica el examen por ID y `choices` contiene las opciones anidadas. Al consultar una opción por su ruta propia, `question` identifica la pregunta por ID. La API impide que una pregunta quede con menos de dos opciones o con un número de respuestas correctas distinto de uno.

### Filtros y paginación

`GET /api/questions/?exam=1` limita los resultados a un examen; `GET /api/questions/?search=ORM` busca en el enunciado y `GET /api/questions/?page=2` solicita otra página. Los parámetros se pueden combinar.

### Ejemplo de creación y validación por HTTP

```powershell
$headers = @{ Authorization = "Token $env:QUIZ_TOKEN" }
$body = @{
  exam = 1
  text = "¿Qué es REST?"
  choices = @(
    @{ text = "Un estilo de arquitectura"; is_correct = $true }
    @{ text = "Un lenguaje de programación"; is_correct = $false }
  )
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri "$env:QUIZ_URL/api/questions/" -Headers $headers -ContentType "application/json" -Body $body
```

Una solicitud válida de creación devuelve `201 Created`. Un campo obligatorio ausente, un tipo incompatible o una pregunta con cero o más de una respuesta correcta devuelve `400 Bad Request`. Sin token válido la API responde `401 Unauthorized`; una operación prohibida por el rol responde `403 Forbidden`; un ID inexistente responde `404 Not Found`.

El esquema está en `/api/schema/` y la documentación interactiva en `/api/docs/`.

## Cliente de consola

```powershell
python quizctl.py exams list
python quizctl.py questions list --exam 1 --search ORM --json
python quizctl.py questions create --exam 1 --text "¿Qué es REST?" --choice "Un estilo:ok" --choice "Un lenguaje"
python quizctl.py questions get 1
python quizctl.py questions delete 1
python quizctl.py ops
```

`--dry-run` describe una escritura sin enviarla. Con `--json`, el cliente conserva el código HTTP, los datos y el error en una salida estable. Los códigos de salida son 0 para éxito, 1 para otros errores o uso incorrecto, 2 para validación, 3 para autorización, 4 para no encontrado, 5 para error del servidor y 6 para falta de conexión.

## Permisos

La autenticación por token identifica al usuario. El usuario `profe` (staff) puede todas las operaciones; un usuario del grupo `agente` puede GET, POST, PUT y PATCH; los demás usuarios autenticados solo pueden leer. DELETE queda reservado a `profe`.

## Comprobaciones

Las pruebas recorren las operaciones de los tres recursos, las respuestas de validación, permisos, filtros, búsqueda, paginación y el contrato OpenAPI. También usan un cliente HTTP externo contra un servidor real de pruebas.

```powershell
python manage.py test
```
