# secretos_ejemplo.py -> copiar como secretos.py, completar y subirlo a la Pico.
# secretos.py NO se sube a git (esta en .gitignore): tiene la clave de la red.

MODO_RED = "hotspot"            # "hotspot" = conectarse a la zona Wi-Fi (ROS 2)
                                # "ap"      = crear la red FutBot_1 (control WASD sin Raspberry)

HOTSPOT_SSID = "Nombre de la zona Wi-Fi"      # tal cual aparece en el iPhone (Ajustes > General > Informacion > Nombre)
HOTSPOT_PASSWORD = "clave de la zona Wi-Fi"

# IP fija del Pico dentro de la zona Wi-Fi del iPhone (red 172.20.10.0/28, puerta 172.20.10.1).
# El iPhone reparte las IP desde la .2 hacia arriba; la .12 queda libre si hay pocos equipos.
# Debe ser la misma que ip_pico en futbot/config/parametros.yaml (seccion puente_pico).
# None = la que entregue el iPhone (se ve en la consola de Thonny al arrancar).
IP_FIJA = ("172.20.10.12", "255.255.255.240", "172.20.10.1", "8.8.8.8")

HOSTNAME = "futbot-pico"
PAIS = "CL"
