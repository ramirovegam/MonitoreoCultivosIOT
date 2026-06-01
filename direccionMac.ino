#include <WiFi.h>
#include <esp_now.h>

// Configuramos el Pin 13 para el Relé (como lo hicimos funcionar ayer)
const int RELE_PIN = 13; 

// Función callback: Se ejecuta automáticamente CADA VEZ que llega un mensaje por el aire
void alRecibirDatos(const uint8_t * mac, const uint8_t *datosEntrantes, int longitud) {
  // Creamos un buffer para guardar el texto que llegó
  char mensaje[10];
  memcpy(mensaje, datosEntrantes, longitud);
  mensaje[longitud] = '\0'; // Aseguramos el cierre de la cadena de texto

  String comando = String(mensaje);
  comando.trim();

  // Evaluamos el comando recibido por el aire
  if (comando == "RIEGO_ON") {
    Serial.println("Comando Recibido por Aire: ENCENDIENDO BOMBA");
    digitalWrite(RELE_PIN, LOW);  // Activa el relé (Lógica inversa)
  } 
  else if (comando == "RIEGO_OFF") {
    Serial.println("Comando Recibido por Aire: APAGANDO BOMBA");
    digitalWrite(RELE_PIN, HIGH); // Desactiva el relé
  }
}

void setup() {
  Serial.begin(115200);
  
  // Configurar el pin del relé
  pinMode(RELE_PIN, OUTPUT);
  digitalWrite(RELE_PIN, HIGH); // Arranca apagado por seguridad

  // Inicializar Wi-Fi en modo Estación (necesario para ESP-NOW)
  WiFi.mode(WIFI_STA);

  // Inicializar ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error al inicializar ESP-NOW en el Receptor");
    return;
  }

  // Registramos la función que va a cachar los mensajes
  esp_now_register_recv_cb(esp_now_recv_cb_t(alRecibirDatos));

  Serial.println("RECEPTOR LISTO. Esperando comandos por el aire...");
}

void loop() {
 
}