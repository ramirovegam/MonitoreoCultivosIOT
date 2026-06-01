#include <WiFi.h>
#include <esp_now.h>

uint8_t macReceptor[] = {0x8C, 0x4F, 0x00, 0x2F, 0x7A, 0xB4};

unsigned long tiempoAnterior = 0;
const long intervaloHumedad = 1000; 

void setup() {
  Serial.begin(115200); 

  WiFi.mode(WIFI_STA);

  
  analogReadResolution(10); 

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error al inicializar ESP-NOW");
    return;
  }

  esp_now_peer_info_t informacionPeer;
  memset(&informacionPeer, 0, sizeof(informacionPeer));
  memcpy(informacionPeer.peer_addr, macReceptor, 6);
  informacionPeer.channel = 0;  
  informacionPeer.encrypt = false;
  
  if (esp_now_add_peer(&informacionPeer) != ESP_OK) {
    Serial.println("Error al agregar el Peer");
    return;
  }
}

void loop() {
  unsigned long tiempoActual = millis();

  // --- TAREA A: Leer Humedad nativa en 10 bits ---
  if (tiempoActual - tiempoAnterior >= intervaloHumedad) {
    tiempoAnterior = tiempoActual;
    
    // Al usar el pin 34, la lectura ya sale directo entre 0 y 1023 gracias al setup()
    int valor_escala_arduino = analogRead(34); 

    // Mandamos el dato limpio a tu interfaz de Python
    Serial.println(valor_escala_arduino); 
  }

  // --- TAREA B: Escuchar órdenes de Python ---
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();

    if (comando == "RIEGO_ON" || comando == "RIEGO_OFF") {
      char mensaje[32]; 
      comando.toCharArray(mensaje, sizeof(mensaje));
      esp_now_send(macReceptor, (uint8_t *) mensaje, strlen(mensaje) + 1);
    }
  }
}