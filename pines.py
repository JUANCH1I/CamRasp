import RPi.GPIO as GPIO
import time

# Desactivar advertencias
GPIO.setwarnings(False)

# Configuracion del GPIO
GPIO.setmode(GPIO.BCM)

relay_pins = [17, 27, 22]

# Configuracion de los pines como salida
for pin in relay_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# Prueba para encender y apagar cada rele
for pin in relay_pins:
    print(f"Encendiendo rele en pin {pin}")
    GPIO.output(pin, GPIO.HIGH)  # Encender el rele
    time.sleep(10)  # Mantener encendido por 2 segundos
    print(f"Apagando rele en pin {pin}")
    GPIO.output(pin, GPIO.LOW)  # Apagar el rele
    time.sleep(1)

# Limpiar configuracion
GPIO.cleanup()
