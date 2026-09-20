# Automatización bancaria desde el teléfono

El endpoint es el mismo para iPhone y Android:

```text
POST http://IP_DEL_COMPUTADOR:3000/webhooks/bank-transactions
X-Webhook-Token: CLAVE_PRIVADA
Content-Type: application/json

{
  "text": "texto completo recibido del banco",
  "source": "ios_shortcuts"
}
```

El computador debe tener PostgreSQL, Ollama y FastAPI iniciados. La opción requerida para uso remoto es Tailscale: computador y teléfono deben iniciar sesión en la misma tailnet. El mismo flujo conserva una IP local como respaldo durante el desarrollo.

## Preparar la conexión

Desde la raíz del proyecto:

```powershell
.\scripts\start-backend.ps1
```

En otra terminal:

```powershell
.\scripts\tailscale-status.ps1 -TestBackend
.\scripts\phone-webhook.ps1 -Test
.\scripts\phone-webhook.ps1 -Copy Url
.\scripts\phone-webhook.ps1 -Copy Token
```

El primer comando comprueba la VPN y el backend. `phone-webhook.ps1` prefiere automáticamente la IP privada `100.x` de Tailscale; su prueba valida autenticación sin registrar un gasto. Los otros dos usos copian, por separado, la URL y la clave privada. No compartas la clave y limpia el portapapeles al terminar.

## iPhone: Atajos

iOS no permite que Kirby lea directamente las notificaciones push de otras aplicaciones. La integración recomendada usa Atajos de estas maneras:

1. Automática si el banco también envía la compra por **Mensaje** o **Correo**.
2. Manual desde **Compartir** cuando una aplicación permite compartir o copiar el texto.
3. Mediante el disparador **Transacción** para tarjetas compatibles con Wallet, únicamente si el atajo recibe monto, comercio y fecha suficientes. Un simple toque de tarjeta no demuestra por sí solo que la operación terminó.

### Crear el atajo reutilizable

1. Abre **Atajos** y crea uno llamado `Registrar gasto en Kirby`.
2. En los detalles, activa **Mostrar en hoja para compartir** y limita la entrada a texto.
3. Si no hay entrada, añade **Solicitar entrada** para poder pegar el mensaje manualmente.
4. Añade la acción **Obtener contenido de URL**.
5. Pega la URL obtenida con `phone-webhook.ps1 -Copy Url`.
6. Cambia el método a `POST`.
7. Agrega el encabezado `X-Webhook-Token` y pega la clave obtenida con `-Copy Token`.
8. Selecciona cuerpo `JSON` y crea estos campos:
   - `text`: la variable **Entrada del atajo**.
   - `source`: el texto fijo `ios_shortcuts`.
9. Opcionalmente, toma `message` de la respuesta y muéstralo con **Mostrar notificación**.

### Automatizar mensajes o correos

1. En Atajos entra en **Automatización** y crea una automatización personal.
2. Selecciona **Mensaje** o **Correo** y filtra por el remitente real del banco. Puedes añadir una frase estable como `Compra` o `Pago`.
3. Ejecuta `Registrar gasto en Kirby` pasando como entrada el cuerpo del mensaje o correo recibido.
4. Activa la ejecución automática y, si aparece, **Permitir ejecutar bloqueado**.
5. Prueba primero con una sola notificación y confirma el gasto en Kirby.

Apple documenta que Mensaje, Correo y Transacción pueden activar automatizaciones sin confirmación, pero no ofrece un disparador general para leer las notificaciones push de cualquier aplicación. La hoja Compartir sirve como alternativa manual para texto visible en otras aplicaciones.

## Android: Tasker, MacroDroid o servicio nativo

Android sí ofrece acceso a notificaciones mediante permiso explícito del usuario. En Tasker o MacroDroid:

1. Crea un disparador **Notificación recibida** y limita las aplicaciones a las del banco.
2. Añade una solicitud HTTP `POST` a la misma URL.
3. Agrega los encabezados `Content-Type: application/json` y `X-Webhook-Token: CLAVE_PRIVADA`.
4. Envía un JSON con `text` igual al título más el cuerpo de la notificación y `source` igual a `android_notification_listener`.
5. Concede acceso a notificaciones únicamente a la automatización elegida.

Una futura compilación Android de Kirby puede incorporar su propio `NotificationListenerService`; no existe un equivalente permitido para leer notificaciones ajenas en iPhone.

## Conectividad remota con Tailscale

1. Instala Tailscale en Windows y en el iPhone.
2. Inicia sesión con la misma cuenta en ambos dispositivos y activa la VPN en el iPhone.
3. Ejecuta `.\scripts\tailscale-status.ps1`; debe mostrar una IPv4 privada `100.x` y el iPhone.
4. Inicia el backend y repite con `-TestBackend`.
5. Desactiva el Wi-Fi del iPhone, conserva Tailscale activo y prueba `http://IP_100_X:3000/health` desde Safari.

La IP de Tailscale es estable aunque cambie la red física. El computador debe permanecer encendido y FastAPI iniciado. No abras directamente el puerto 3000 en el router ni uses Tailscale Funnel: la API debe permanecer accesible solo dentro de la tailnet.

Referencias oficiales:

- [Automatizaciones personales en Atajos](https://support.apple.com/guide/shortcuts/add-automations-apdfbdbd7123/ios)
- [Disparadores de Mensaje y Correo](https://support.apple.com/guide/shortcuts/apdd711f9dff/ios)
- [Ejecutar un atajo desde Compartir](https://support.apple.com/guide/shortcuts/run-a-shortcut-from-another-app-apd163eb9f95/ios)
- [Solicitudes POST desde Atajos](https://support.apple.com/guide/shortcuts/apd58d46713f/ios)
- [NotificationListenerService de Android](https://developer.android.com/reference/android/service/notification/NotificationListenerService)
