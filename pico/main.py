"""
El Pico hace de servidor TCP para recibir las ordenes de movimiento.

Dos modos de red (MODO_RED, en secretos.py):
  "hotspot"  el Pico se CONECTA a una red existente (la zona Wi-Fi del iPhone), la misma
             en la que estan la Raspberry Pi 4 y el PC. Es el modo para ROS 2: el nodo
             /puente_pico de la Raspberry se conecta a <IP del Pico>:8080.
  "ap"       el Pico crea su propia red (FutBot_1, 192.168.4.1), como antes. Sirve para
             el control WASD sin Raspberry (wasd/main_no_camera.py).

Protocolo: lineas de texto "vl,vr,sol,rod\n" (framing por \n). Sin cambios.
Si no llega ningun mensaje nuevo en WATCHDOG_MS, el robot se detiene solo.
Si no llega nada en DESCONECTAR_MS, se cierra esa conexion y se vuelve a esperar otra
(asi una conexion "muerta" por un corte de Wi-Fi no deja al Pico bloqueado).
"""

import network
import socket
import time
import hw

try:
    import secretos            # secretos.py: red y clave (NO se sube a git, ver secretos_ejemplo.py)
except ImportError:
    secretos = None


def _cfg(nombre, defecto):
    return getattr(secretos, nombre, defecto) if secretos else defecto


MODO_RED = _cfg("MODO_RED", "ap")          # "hotspot" o "ap"

# Modo "ap" (igual que antes)
AP_SSID = "FutBot_1"
AP_PASSWORD = "futbot123"   # minimo 8 caracteres (WPA2)

# Modo "hotspot"
HOTSPOT_SSID = _cfg("HOTSPOT_SSID", "")
HOTSPOT_PASSWORD = _cfg("HOTSPOT_PASSWORD", "")
IP_FIJA = _cfg("IP_FIJA", None)            # p. ej. ("172.20.10.12", "255.255.255.240", "172.20.10.1", "8.8.8.8")
HOSTNAME = _cfg("HOSTNAME", "futbot-pico")
PAIS = _cfg("PAIS", "CL")

SERVER_PORT = 8080

WATCHDOG_MS = 500
DESCONECTAR_MS = 3000
RECV_TIMEOUT_S = 0.1


def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.config(ssid=AP_SSID, password=AP_PASSWORD)
    ap.active(True)
    while not ap.active():
        time.sleep(0.1)
    hw.led.on()
    print("AP activo. SSID: {}  IP: {}".format(AP_SSID, ap.ifconfig()[0]))
    return ap


def start_hotspot():
    """Se conecta a la red de la zona Wi-Fi. Parpadea el LED mientras espera."""
    try:
        network.country(PAIS)
    except Exception:
        pass
    try:
        network.hostname(HOSTNAME)
    except Exception:
        pass
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    try:
        sta.config(pm=0xa11140)   # sin ahorro de energia: menos retraso en cada mensaje
    except Exception:
        pass
    while not sta.isconnected():
        print("Conectando a la red '{}' ...".format(HOTSPOT_SSID))
        sta.connect(HOTSPOT_SSID, HOTSPOT_PASSWORD)
        for _ in range(100):                 # hasta 10 s por intento
            if sta.isconnected():
                break
            hw.led.toggle()
            time.sleep(0.1)
    if IP_FIJA:
        sta.ifconfig(IP_FIJA)
    hw.led.on()
    print("Conectado a '{}'. IP del Pico: {}".format(HOTSPOT_SSID, sta.ifconfig()[0]))
    return sta


def start_network():
    if MODO_RED == "hotspot":
        return start_hotspot()
    return start_ap()


def run_server(wlan):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", SERVER_PORT))
    server_socket.listen(1)
    server_socket.settimeout(1.0)   # accept() no bloquea para siempre: permite revisar el Wi-Fi
    print("Esperando conexion en el puerto", SERVER_PORT)

    while True:
        try:
            conn, addr = server_socket.accept()
        except OSError:
            # Nadie se conecto en 1 s. En modo hotspot, si se perdio la red, reconectar.
            if MODO_RED == "hotspot" and not wlan.isconnected():
                hw.stop_all()
                wlan = start_hotspot()
            continue
        conn.settimeout(RECV_TIMEOUT_S)
        print("Conectado desde", addr)
        hw.led_verde.on()

        buf = b""
        prev_sol = 0
        last_msg_ms = time.ticks_ms()

        while True:
            hw.kick_update()

            sin_mensajes = time.ticks_diff(time.ticks_ms(), last_msg_ms)
            if sin_mensajes > WATCHDOG_MS:
                hw.stop_all()
            if sin_mensajes > DESCONECTAR_MS:
                print("Sin mensajes por {} ms: se cierra la conexion".format(DESCONECTAR_MS))
                break

            try:
                chunk = conn.recv(256)
            except OSError:
                chunk = None

            if chunk == b"":
                print("Desconectado")
                break

            if chunk:
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    parts = line.split(b",")
                    if len(parts) != 4:
                        continue
                    try:
                        vl = int(parts[0])
                        vr = int(parts[1])
                        sol_val = int(parts[2])
                        rod_val = int(parts[3])
                    except ValueError:
                        continue

                    hw.set_left(vl)
                    hw.set_right(vr)
                    hw.set_rodillo(rod_val)   # rod ahora es duty (0-100), no solo on/off
                    if sol_val and not prev_sol:
                        hw.kick()
                    prev_sol = sol_val
                    last_msg_ms = time.ticks_ms()

        hw.stop_all()
        hw.led_verde.off()
        conn.close()


def main():
    hw.stop_all()
    wlan = start_network()
    try:
        run_server(wlan)
    finally:
        hw.stop_all()


main()
