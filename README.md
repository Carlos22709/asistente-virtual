# Kirby Assistant

Aplicación móvil personal. Incluye tareas, ingresos, gastos, flujo de caja, presupuesto, tarjetas, préstamos, metas de ahorro y agenda mediante una app Expo que consume una API REST FastAPI. El backend incorpora un orquestador con IA que usa function calling para delegar solicitudes a Secretaría, Finanzas o ambos agentes. Los agentes consultan y modifican los datos reales del proyecto, y un webhook protegido puede convertir notificaciones bancarias en gastos automáticamente.

## Arquitectura

```text
Expo / React Native  →  HTTP + JSON  →  FastAPI  →  SQLAlchemy
                                                        ↓
                                           PostgreSQL local / Supabase
                                           ↓
                                  Ollama / llama3.2
```

El repositorio separa las responsabilidades en dos aplicaciones:

- `mobile/`: cliente Expo/React Native. `app/` contiene las pantallas,
  `components/` los controles reutilizables y `services/` encapsula API,
  almacenamiento seguro y notificaciones locales.
- `backend/`: API FastAPI. `routes/` expone HTTP, `schemas/` valida los
  contratos, `services/` contiene la lógica de negocio y los agentes, y
  `models/` define la persistencia SQLAlchemy.
- Ollama se ejecuta localmente para decidir el agente y estructurar comandos;
  PostgreSQL local o Supabase conserva los datos; Gmail es una integración
  opcional y nunca se consulta directamente desde el teléfono.

En el flujo de voz, el cliente graba el audio, el backend lo transcribe con
Whisper y el orquestador selecciona Secretaría, Finanzas o ambos. La respuesta
regresa al móvil y puede reproducirse mediante síntesis de voz.

Las tablas se crean automáticamente al arrancar el backend. Esta decisión simplifica la primera versión; si el esquema evoluciona, el paso natural será incorporar migraciones más adelante.

El agente de Secretaría también puede trabajar con Gmail: lista, busca y prioriza mensajes, resume hilos con Ollama, crea borradores y los envía únicamente después de una confirmación explícita.

## Requisitos

- Node.js 22.13 o posterior y npm.
- Python 3.11 o posterior.
- PostgreSQL 15 o posterior para desarrollo local, o un proyecto de Supabase.
- Ollama 0.34 o posterior y el modelo local `llama3.2`.
- Expo Go en el teléfono, o un emulador Android/iOS.
- Teléfono y computador en la misma red para probar en un dispositivo físico.

Comprueba las instalaciones con:

```powershell
node --version
npm --version
python --version
psql --version
pg_isready
ollama --version
ollama list
```

## 1. Crear la base de datos

> En este equipo PostgreSQL está instalado para el usuario en `%LOCALAPPDATA%/Programs/PostgreSQL/18` y el clúster está en `%LOCALAPPDATA%/PostgreSQL/18/data`. Los scripts de `scripts/` lo inician automáticamente.

Las credenciales administrativas locales están en `%LOCALAPPDATA%/PostgreSQL/18/admin.env` y las credenciales limitadas de la aplicación en `backend/.env`. Ambos archivos están excluidos de Git.

Abre `psql` como el usuario administrador de PostgreSQL:

```sql
CREATE USER kirby_user WITH PASSWORD 'elige_una_clave_segura';
CREATE DATABASE kirby OWNER kirby_user;
```

La contraseña solo debe escribirse en `backend/.env`; nunca la agregues al repositorio.

### Usar Supabase

La app móvil no se conecta directamente a Supabase. Expo continúa llamando a
FastAPI y el backend conecta a PostgreSQL en Supabase. Así, toda la lógica de los
agentes y las credenciales permanecen en el backend; no hace falta instalar el
SDK de Supabase ni guardar una clave pública en el cliente móvil.

1. Crea un proyecto en Supabase y conserva la contraseña de la base de datos.
2. En el proyecto abre **Connect > Session pooler** y copia la URI del puerto
   `5432`. Reemplaza `[YOUR-PASSWORD]`; si la contraseña contiene caracteres
   especiales, codifícalos para una URL.
3. Desde la raíz del proyecto ejecuta:

   ```powershell
   .\scripts\configure-supabase.ps1
   ```

   La URI se solicita de forma oculta, se guarda en archivos excluidos de Git y
   se añade `sslmode=require`.
4. Para crear las tablas vacías y comprobar la conexión:

   ```powershell
   .\scripts\initialize-database.ps1
   ```

5. Si quieres copiar los datos que ya existen en PostgreSQL local, deja el
   proyecto de Supabase vacío y ejecuta:

   ```powershell
   .\scripts\migrate-to-supabase.ps1
   ```

   El script pide escribir `MIGRAR`, copia todas las tablas y reajusta sus
   secuencias. Se cancela si detecta datos previos en Supabase para no duplicarlos.

Puedes alternar entre ambas bases y después reiniciar el backend:

```powershell
.\scripts\switch-database.ps1 -Target Supabase
.\scripts\switch-database.ps1 -Target Local
```

Al inicializar o migrar, el proyecto activa RLS en sus tablas y revoca el acceso
de los roles `anon` y `authenticated`. FastAPI sigue accediendo mediante la
conexión privada de PostgreSQL. Supabase mueve la base a la nube, pero FastAPI y
Ollama continúan ejecutándose en el computador; el iPhone todavía necesita
Tailscale para alcanzar la API fuera de la red local.

## 2. Iniciar el backend

Desde la raíz del proyecto, en PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `backend/.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://kirby_user:elige_una_clave_segura@localhost:5433/kirby
CORS_ORIGINS=*
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
LLM_TIMEOUT_SECONDS=30
BANK_WEBHOOK_TOKEN=elige_un_secreto_aleatorio_de_al_menos_24_caracteres
GMAIL_CLIENT_SECRETS_FILE=credentials/gmail_client_secret.json
GMAIL_TOKEN_FILE=credentials/gmail_token.json
```

Descarga el modelo una sola vez y comprueba que aparezca en la lista:

```powershell
ollama pull llama3.2
ollama list
```

### Conectar Gmail

Esta configuración se hace una sola vez en el computador:

1. En Google Cloud crea o selecciona un proyecto, habilita **Gmail API** y configura la pantalla de consentimiento OAuth.
2. Crea un cliente OAuth de tipo **Aplicación de escritorio**. Si la aplicación está en modo de prueba, agrega tu cuenta de Gmail como usuario de prueba.
3. Descarga el JSON y guárdalo como `backend/credentials/gmail_client_secret.json`.
4. Desde la raíz ejecuta:

   ```powershell
   .\scripts\connect-gmail.ps1
   ```

5. Inicia sesión en la ventana de Google y acepta acceso para leer correos y administrar borradores/envíos.

La autorización queda en `backend/credentials/gmail_token.json`. Toda la carpeta está excluida de Git; no compartas esos archivos. La app no envía un correo al crearlo: primero guarda un borrador y muestra su identificador. Para enviarlo debes responder con una confirmación como `Sí, envía el borrador` dentro de la misma conversación.

Arranca FastAPI:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

- `--host 0.0.0.0` escucha en las interfaces de red del computador y permite el acceso desde el teléfono.
- `--port 3000` expone la API en el puerto 3000.
- `--reload` reinicia el servidor al cambiar código y solo debe usarse durante desarrollo.

La instancia PostgreSQL propia de Kirby usa el puerto `5433`, porque en este equipo Docker ya reserva `5432` para otro proyecto. Los scripts respetan esa separación y no detienen ni modifican el contenedor ajeno.

Abre `http://127.0.0.1:3000/docs` para Swagger y `http://127.0.0.1:3000/health` para comprobar el estado básico. Al iniciar se crean `tasks`, `incomes`, `expenses`, `budgets`, `financial_accounts`, `savings_goals`, `events` y `bank_notifications` sin borrar datos existentes.

### CORS

`CORS_ORIGINS=*` es práctico en desarrollo local. Para restringirlo, indica una lista separada por comas, por ejemplo:

```dotenv
CORS_ORIGINS=http://localhost:8081,http://192.168.1.10:8081
```

No uses el comodín en una publicación accesible desde Internet.

## 3. Iniciar la aplicación móvil

Abre otra terminal desde la raíz:

```powershell
cd mobile
npm install
npx expo install --fix
Copy-Item .env.example .env
```

Busca la IPv4 del computador:

```powershell
ipconfig
```

Edita `mobile/.env` y sustituye el ejemplo por esa dirección:

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.1.10:3000
```

Después inicia Expo:

```powershell
npx expo start
```

### Inicio rápido en este equipo

La instalación local ya configurada puede arrancarse con un solo comando:

```powershell
cd C:\DM\asistente-virtual
.\scripts\start-all.ps1
```

El script comprueba las dependencias, levanta Ollama si hace falta, inicia FastAPI y abre Expo en terminales separadas para conservar los logs y el código QR. Para diagnosticar la instalación sin iniciar procesos:

```powershell
.\scripts\start-all.ps1 -CheckOnly
```

El cliente móvil se inicia explícitamente en modo Expo Go. Instala **Expo Go** desde la App Store, abre la aplicación y escanea desde allí el QR nuevo que aparece después de reiniciar Expo. No se necesita una cuenta Apple Developer.

El control por voz funciona así:

1. Toca el micrófono para comenzar a grabar.
2. Habla y vuelve a tocarlo al terminar.
3. El iPhone envía el audio al backend por Tailscale.
4. Whisper lo transcribe localmente y Kirby procesa el texto con el orquestador multiagente.

El modelo gratuito `base` de Whisper se descarga la primera vez y queda guardado en el computador. Puede cambiarse con `WHISPER_MODEL`, `WHISPER_DEVICE` y `WHISPER_COMPUTE_TYPE` en `backend/.env`.

También puedes arrancar los servicios manualmente desde dos terminales PowerShell:

```powershell
cd C:\DM\asistente-virtual
.\scripts\start-backend.ps1
```

```powershell
cd C:\DM\asistente-virtual
.\scripts\start-mobile.ps1
```

Para detener PostgreSQL después de cerrar el backend:

```powershell
.\scripts\stop-postgres.ps1
```

### Acceso remoto con Tailscale

Tailscale es obligatorio para la demostración desde datos móviles. Instálalo en Windows y en el iPhone, inicia sesión con la misma cuenta y comprueba el estado con:

```powershell
.\scripts\tailscale-status.ps1
.\scripts\tailscale-status.ps1 -TestBackend
```

Cuando Tailscale está conectado, `start-mobile.ps1` configura temporalmente la API y Metro con la IP privada `100.x`; `phone-webhook.ps1` también la prefiere para Atajos. Si Tailscale no está disponible, ambos conservan el comportamiento de red local. No se abre ningún puerto público ni se usa Funnel.

Escanea el QR con Expo Go para probar la aplicación completa. El dictado graba con `expo-audio`, incluido en Expo Go, y envía el archivo a `POST /assistant/transcribe`; no requiere una development build. En un teléfono físico, `localhost` apunta al propio teléfono, no al computador, por eso el script configura la IP privada de Tailscale.

Si cambias una variable `EXPO_PUBLIC_*`, reinicia Expo. Si Metro conserva una configuración anterior:

```powershell
npx expo start --clear
```

## Uso

- **Inicio:** muestra tareas pendientes y próximas, gasto diario/semanal, siguiente evento y presupuesto del mes.
- **Tareas:** crea, edita, inicia, pausa, completa, reabre, filtra y elimina tareas con estados Pendiente, En progreso y Completada. Las vencidas tienen tratamiento visual distinto.
- **Finanzas:** registra ingresos y gastos, calcula el flujo neto mensual, administra el presupuesto, controla tarjetas o préstamos y sigue metas de ahorro con aportes y porcentaje de avance.
- **Agenda:** crea, edita, agrupa por fecha, filtra y elimina eventos próximos.
- **Recordatorios:** al guardar una tarea o evento futuro puedes solicitar un recordatorio local. La app conserva su identificador en el dispositivo, lo reemplaza al editar, lo cancela al desactivarlo, eliminar el elemento o completar una tarea, y evita duplicados. Si deniegas el permiso, el resto de la app sigue funcionando. No se usan notificaciones push.
- **Asistente:** la pestaña móvil acepta texto o dictado en español, conserva hasta 20 mensajes de contexto y puede leer la respuesta en voz alta. `POST /assistant/chat` usa un primer function calling para elegir Secretaría, Finanzas o ambos, y un segundo para seleccionar la acción de dominio. Secretaría consulta o crea tareas y eventos; también lista, busca, prioriza y resume Gmail, crea borradores y solo los envía con confirmación explícita. Finanzas consulta el estado financiero o registra gastos. Las acciones locales se guardan inmediatamente en PostgreSQL.
- **Registro bancario automático:** `POST /webhooks/bank-transactions` recibe el texto de una notificación bancaria, Ollama extrae la transacción y la registra como gasto. El texto se trata como contenido no confiable, se ignoran códigos, promociones, saldos y operaciones rechazadas, y una huella evita registrar dos veces la misma notificación. Por seguridad, solo COP se registra automáticamente; otras monedas quedan para revisión manual.

Los campos de fecha usan `AAAA-MM-DD` y los de fecha/hora `AAAA-MM-DDTHH:mm`, por ejemplo `2026-09-10T15:00`. La presentación y los cálculos diarios usan `America/Bogota`.

Ejemplo desde PowerShell, con FastAPI iniciado:

```powershell
$body = @{
  message = "¿Cuánto dinero me queda y qué tareas vencen esta semana?"
  history = @()
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:3000/assistant/chat `
  -ContentType "application/json" `
  -Body $body
```

Ejemplo de una automatización bancaria desde PowerShell. La clave se lee de `backend/.env` y no se imprime:

```powershell
$token = (Get-Content backend\.env |
  Where-Object { $_ -like "BANK_WEBHOOK_TOKEN=*" }).Split("=", 2)[1]
$body = @{
  text = "Compra aprobada por `$45.900 en MERCADO CAMPUS hoy. Ref ABC123."
  source = "android_notification_listener"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:3000/webhooks/bank-transactions `
  -Headers @{ "X-Webhook-Token" = $token } `
  -ContentType "application/json" `
  -Body $body
```

La respuesta usa `created` si creó el gasto, `duplicate` si ya había procesado ese mismo texto, o `ignored` si no detectó una transacción válida. En un teléfono, Tasker/MacroDroid (Android) o una automatización de Atajos (iOS) deben enviar el texto recibido con ese mismo encabezado. No publiques `BANK_WEBHOOK_TOKEN` ni lo incluyas en el código de la app.

Para configurar el iPhone principal —y la alternativa equivalente en Android— sigue [la guía de automatización del teléfono](docs/automatizacion-telefono.md). El ayudante `scripts/phone-webhook.ps1` muestra la URL local, copia la clave sin imprimirla y prueba la conexión sin crear gastos.

## Endpoints

| Área | Endpoints principales |
|---|---|
| Sistema | `GET /health`, `GET /docs` |
| Asistente | `POST /assistant/chat` |
| Automatización bancaria | `GET /webhooks/bank-transactions/status`, `POST /webhooks/bank-transactions` |
| Inicio | `GET /dashboard/summary` |
| Tareas | `GET/POST /tasks`, `GET/PUT/DELETE /tasks/{id}`, `PATCH /tasks/{id}/status`, `PATCH /tasks/{id}/complete` (compatibilidad) |
| Gastos | `GET/POST /expenses`, `GET/PUT/DELETE /expenses/{id}`, `GET /expenses/summary` |
| Ingresos y flujo | `GET/POST /incomes`, `GET/PUT/DELETE /incomes/{id}`, `GET /incomes/cash-flow` |
| Tarjetas y préstamos | `GET/POST /financial-accounts`, `GET/PUT/DELETE /financial-accounts/{id}`, `GET /financial-accounts/summary` |
| Metas de ahorro | `GET/POST /savings-goals`, `GET/PUT/DELETE /savings-goals/{id}`, `POST /savings-goals/{id}/contributions`, `GET /savings-goals/summary` |
| Presupuestos | `GET/POST /budgets`, `GET /budgets/current`, `PUT/DELETE /budgets/{id}` |
| Agenda | `GET/POST /events`, `GET/PUT/DELETE /events/{id}` |

Swagger documenta filtros y cuerpos exactos. La API usa `201` al crear, `204` al eliminar, `404` para recursos inexistentes, `409` al duplicar un presupuesto mensual y `422` para datos inválidos.

## Verificación recomendada

Con PostgreSQL y FastAPI iniciados:

1. Confirma `GET /health` y abre `/docs`.
2. Desde Swagger, crea, lista, edita, completa/reabre y elimina una tarea.
3. Crea, edita y elimina un gasto; revisa `/expenses/summary`.
4. Crea el presupuesto del mes y revisa `/budgets/current`. Intenta repetirlo y confirma el `409`.
5. Crea, edita, filtra y elimina un evento.
6. Prueba `/assistant/chat` con una consulta de agenda, una financiera y otra que combine ambos dominios.
7. Con Gmail conectado, pide correos no leídos, busca uno, resume su hilo y crea un borrador. Comprueba que no se envíe hasta responder `Sí, envía el borrador`.
8. Envía una notificación de compra al webhook con su token; repítela y confirma que la segunda respuesta sea `duplicate` y no cree otro gasto.
9. Envía montos negativos, títulos vacíos, mes `13` y una fecha final anterior para confirmar respuestas `422`.
10. Reinicia Uvicorn y vuelve a listar los recursos para comprobar persistencia.
11. En `mobile`, ejecuta:

   ```powershell
   npm run typecheck
   npx expo-doctor@latest
   ```

12. Abre la app, realiza un CRUD en cada sección y confirma que listas, totales e Inicio cambian al volver a cada pestaña.

La prueba automatizada del contrato HTTP usa una base SQLite temporal únicamente para aislar el test; la aplicación real sigue configurada para PostgreSQL:

```powershell
cd backend
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## Estructura

```text
backend/
  app/
    models/       # tablas SQLAlchemy
    schemas/      # entrada, validación y respuesta Pydantic
    routes/       # API REST
    services/     # cálculos de negocio, cliente Ollama y orquestador
    database.py
    main.py
  tests/          # pruebas unitarias e integrales
mobile/
  app/(tabs)/     # Inicio, Tareas, Finanzas y Agenda
  components/     # controles visuales reutilizables
  services/       # fetch centralizado y recursos de la API
  types/
  utils/
docs/             # automatización bancaria desde el teléfono
scripts/          # configuración, diagnóstico e inicio del entorno
```

## Solución de problemas

- **`connection refused` en FastAPI:** con la base local, confirma que PostgreSQL esté iniciado y que `DATABASE_URL` use el puerto `5433`. Con Supabase, revisa la URI de **Session pooler**, el puerto `5432`, la contraseña y `sslmode=require`.
- **Supabase rechaza la conexión:** comprueba que el proyecto no esté pausado y vuelve a copiar la URI desde **Connect > Session pooler**. No publiques la URI ni la pegues en el chat.
- **Ollama no tiene el modelo:** ejecuta `ollama pull llama3.2`; `ollama list` debe mostrarlo antes de usar `/assistant/chat`.
- **Gmail no está conectado:** confirma que existen ambos JSON dentro de `backend/credentials/`; si falta el token, ejecuta `scripts/connect-gmail.ps1` otra vez.
- **Google muestra “acceso bloqueado”:** revisa que Gmail API esté habilitada, que el cliente sea de tipo aplicación de escritorio y que tu correo esté agregado como usuario de prueba en la pantalla de consentimiento.
- **El webhook responde `401`:** comprueba que el encabezado `X-Webhook-Token` coincida exactamente con `BANK_WEBHOOK_TOKEN` en `backend/.env`.
- **El webhook responde `503`:** confirma que la clave esté configurada y que Ollama esté iniciado. Reinicia FastAPI después de cambiar `.env`.
- **La descarga de Ollama se interrumpe:** vuelve a ejecutar `ollama pull llama3.2`; las capas completas se reutilizan. Si falla repetidamente contra `cloudflarestorage.com`, revisa VPN, proxy, antivirus o firewall.
- **La app no llega a la API:** abre `http://IP_DEL_COMPUTADOR:3000/health` desde el navegador del teléfono. Si no responde, revisa IP, Wi-Fi, firewall y `--host 0.0.0.0`.
- **Error de dependencias Expo:** usa Node compatible, elimina únicamente `mobile/node_modules` si es necesario, ejecuta `npm install` y luego `npx expo install --fix`.
- **Puerto ocupado:** detén el proceso que usa 3000. Cambiar el puerto requiere actualizar también `EXPO_PUBLIC_API_URL`.
