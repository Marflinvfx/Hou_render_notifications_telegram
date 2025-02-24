# Telegram Render Notifications for Houdini

Esta herramienta permite enviar notificaciones a través de Telegram cuando se completan renders en Houdini. Es útil para monitorear renders largos desde cualquier lugar.

## Características

- **Configuración fácil**: Configura tu bot de Telegram y los IDs de chat directamente desde la interfaz de usuario.
- **Notificaciones personalizables**: Recibe notificaciones cuando los renders comienzan, terminan o fallan.
- **Prueba de conexión**: Verifica que tu configuración de Telegram esté correcta antes de usarla.
- **Integración con Shelf**: Añade la herramienta a cualquier estante en Houdini para un acceso rápido.

## Requisitos

- Houdini 18.0 o superior.
- Una cuenta de Telegram y un bot creado a través de BotFather.

## Instalación

1. **Descarga el script**: Coloca el script de Python en un directorio accesible desde Houdini.
2. **Ejecuta el script**: En Houdini, abre un editor de Python y ejecuta el script para iniciar la interfaz de usuario.
3. **Configura tu bot**: Usa la interfaz para ingresar tu `BOT_TOKEN` y `CHAT_ID`.

## Uso

- **Configuración**: Haz clic en "Configure Telegram Bot" para ingresar los detalles de tu bot.
- **Prueba de conexión**: Usa el botón "Test Telegram Connection" para asegurarte de que todo esté configurado correctamente.
- **Habilitar/Deshabilitar notificaciones**: Usa el botón "Enable Notifications" para activar o desactivar las notificaciones.
- **Añadir a Shelf**: Si deseas acceder rápidamente a la herramienta, usa el botón "Create Shelf Tool" para añadirla a un estante en Houdini.

## Soporte

Para más información sobre cómo obtener un `BOT_TOKEN` y un `CHAT_ID`, consulta la sección de ayuda dentro de la herramienta o visita la [documentación oficial de Telegram Bots](https://core.telegram.org/bots#creating-a-new-bot).

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o un pull request si tienes alguna mejora o encuentras algún problema.

## Licencia

Este proyecto está licenciado bajo la MIT License - ver el archivo [LICENSE](LICENSE) para más detalles.
