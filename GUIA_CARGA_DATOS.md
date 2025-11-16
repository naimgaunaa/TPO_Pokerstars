# 📚 GUÍA DE CARGA DE DATOS MANUAL - POKERSTARS APP

## 🎯 ORDEN RECOMENDADO PARA CARGAR DATOS

Sigue este orden para evitar errores de dependencias:

```
1. Crear Tablas (Opción 1)
2. Crear Usuarios (Opción 2) → Al menos 5 usuarios
3. Crear Métodos de Pago (Opción 3) → 1 por usuario mínimo
4. Crear Torneos (Opción 5) → Opcional, solo si quieres mesas de torneo
5. Crear Mesas (Opción 6) → Al menos 5 mesas
6. Registrar Jugadores en Mesas (Opción 7) → Al menos 2 jugadores por mesa
7. Crear Manos (Opción 8) → Al menos 5 manos por mesa
8. Crear Transacciones (Opción 4) → Al menos 5 transacciones
9. Simular Actividad Redis (Opción 9) → 10 veces aprox
```

---

## 📝 PASO A PASO DETALLADO

### **PASO 1: Crear Usuarios (Opción 2)**

**Objetivo:** Crear al menos **5 usuarios** de diferentes países para caso de uso 6.

**Flujo:**
```
Opción: 2
Nombre del usuario: Carlos Gómez
Email del usuario: carlos@poker.com
País del usuario: Argentina
✔️ Usuario 1 creado en PostgreSQL.
```

**Repetir 4 veces más con:**
- María López | maria@poker.com | Chile
- John Smith | john@poker.com | USA
- Ana Silva | ana@poker.com | Brasil
- Pierre Dubois | pierre@poker.com | Francia

**💡 Tip:** Anota los IDs de los usuarios creados (1, 2, 3, 4, 5...)

---

### **PASO 2: Crear Métodos de Pago (Opción 3)**

**Objetivo:** Cada usuario necesita **al menos 1 método de pago** para hacer transacciones.

**Flujo:**
```
Opción: 3
ID Usuario: 1
Tipos disponibles: paypal, tarjeta, transferencia, criptomoneda
Tipo de método de pago: paypal
✔️ Método de pago 1 (paypal) creado para usuario 1.
```

**Crear al menos 5 métodos:**
- Usuario 1 → paypal (para caso de uso 4)
- Usuario 2 → tarjeta
- Usuario 3 → paypal (para caso de uso 4)
- Usuario 4 → transferencia
- Usuario 5 → paypal (para caso de uso 4)

**💡 Tip:** Crea varios PayPal para poder probar el caso de uso 4 (depósitos por PayPal)

---

### **PASO 3 (Opcional): Crear Torneos (Opción 5)**

**Objetivo:** Crear torneos si quieres mesas asociadas a torneos.

**Flujo:**
```
Opción: 5
Nombre del torneo: Sunday Million
Tipo (Freeroll/Buy-in/Satélite): Buy-in
Modalidad (Texas Holdem/Omaha/Seven Card Stud): Texas Holdem
Buy-in (0 para freeroll): 100
Máximo de jugadores: 500
✔️ Torneo 1 'Sunday Million' creado en PostgreSQL.
```

**Crear 2 torneos:**
- Sunday Million (Buy-in, Texas Holdem)
- Freeroll Diario (Freeroll, Omaha)

---

### **PASO 4: Crear Mesas (Opción 6)**

**Objetivo:** Crear **5 mesas** con diferentes modalidades (para casos de uso 1, 5).

**Flujo para Cash Game:**
```
Opción: 6
Modalidad (Texas Holdem/Omaha/Seven Card Stud): Texas Holdem
Tipo (Cash Game/Sit & Go/Torneo): Cash Game
Máximo jugadores (6/8/9): 9
Ciegas (ej: 5/10, 10/20, 25/50): 5/10
ID Torneo (dejar vacío si es Cash Game): [ENTER]
✔️ Mesa 1 (Texas Holdem - Cash Game) creada en PostgreSQL.
```

**Flujo para Mesa de Torneo:**
```
Opción: 6
Modalidad: Texas Holdem
Tipo: Torneo
Máximo jugadores: 9
Ciegas: 10/20
ID Torneo: 1
✔️ Mesa 2 (Texas Holdem - Torneo) creada en PostgreSQL.
```

**Crear 5 mesas variadas:**
1. Texas Holdem - Cash Game (5/10)
2. Omaha - Cash Game (10/20)
3. Texas Holdem - Sit & Go (10/20)
4. Seven Card Stud - Cash Game (5/10)
5. Texas Holdem - Cash Game (25/50)

---

### **PASO 5: Registrar Jugadores en Mesas (Opción 7)**

**Objetivo:** Sentar **al menos 2 jugadores por mesa** (para casos de uso 9, 10 de Neo4j).

**Flujo:**
```
Opción: 7
ID Usuario a sentar: 1
ID Mesa a la que entra: 1
✔️ Usuario 1 sentado en mesa 1 en PostgreSQL.
```

**Estrategia para detectar colusión (Caso 10):**
- **Usuarios 1 y 2** → Sentar juntos en mesas 1, 2, 3, 4 (4 mesas compartidas = COLUSIÓN)
- **Usuarios 3 y 4** → Sentar juntos en mesas 2, 3, 5 (3 mesas compartidas = SOSPECHOSO)
- Usuario 5 → Sentar en mesa 1

**Ejemplo de registro:**
```
Mesa 1: Usuarios 1, 2, 5
Mesa 2: Usuarios 1, 2, 3, 4
Mesa 3: Usuarios 1, 2, 3, 4
Mesa 4: Usuarios 1, 2
Mesa 5: Usuarios 3, 4
```

---

### **PASO 6: Crear Manos (Opción 8)**

**Objetivo:** Crear **manos** ligadas a mesas y jugadores existentes.

**Flujo Automático (Recomendado):**
```
Opción: 8
ID Mesa: 1
Bote generado automáticamente: $2347.82
¿Personalizar bote? (s/n): n
Fecha (dejar vacío para ahora, o formato YYYY-MM-DD): [ENTER]
✔️ Mano 1 creada:
   Mesa: 1 (Texas Holdem)
   Bote: $2347.82 | Rake: $117.39
   Ganador: Usuario 2
   Fecha: 2025-11-16 14:23:45
   Participantes: 3 jugadores
```

**Flujo Personalizado (para caso de uso 3 - Septiembre):**
```
Opción: 8
ID Mesa: 1
Bote generado automáticamente: $950.00
¿Personalizar bote? (s/n): s
Monto del bote: 1500
Jugadores en mesa: [1, 2, 5]
ID del ganador: 1
Fecha (formato YYYY-MM-DD): 2024-09-15
✔️ Mano 2 creada:
   Mesa: 1 (Texas Holdem)
   Bote: $1500.00 | Rake: $75.00
   Ganador: Usuario 1
   Fecha: 2024-09-15 18:32:00
```

**Crear al menos 15 manos:**
- **7 manos recientes** (dejar fecha vacía) → Caso de uso 1
- **5 manos en septiembre con bote > $1000** → Caso de uso 3
- **3 manos adicionales** → Caso de uso 5 (rake por mesa)

---

### **PASO 7: Crear Transacciones (Opción 4)**

**Objetivo:** Crear transacciones de diferentes tipos y medios (para caso de uso 4).

**Flujo:**
```
Opción: 4
ID Usuario: 1
ID Método de pago: 1
Monto: 500
Tipo (deposito/retiro): deposito
✔️ Transacción (1, 2024-11-16...) creada en PostgreSQL.
```

**Crear al menos 8 transacciones:**
- **5 depósitos por PayPal** (Usuarios 1, 3, 5 con métodos PayPal)
- **2 depósitos por tarjeta**
- **1 retiro**

**💡 Tip:** Para caso de uso 4, crea varios depósitos PayPal del usuario 1.

---

### **PASO 8: Simular Actividad en Redis (Opción 9)**

**Objetivo:** Crear ranking de jugadores activos (caso de uso 7).

**Flujo:**
```
Opción: 9
ID Usuario que jugó una mano: 1
Actividad de 1 registrada en Redis.
```

**Repetir 15 veces con distribución:**
- Usuario 1: 5 veces
- Usuario 3: 4 veces
- Usuario 2: 3 veces
- Usuario 4: 2 veces
- Usuario 5: 1 vez

Esto creará un ranking: 1° Usuario 1, 2° Usuario 3, 3° Usuario 2...

---

## ✅ VERIFICACIÓN: ¿Tengo suficientes datos?

### **Para MongoDB (Casos 1-6):**
- ✅ Caso 1: Al menos 5 manos recientes (última semana)
- ✅ Caso 2: Al menos 5 usuarios con saldos
- ✅ Caso 3: Al menos 5 manos en septiembre con bote > $1000
- ✅ Caso 4: Al menos 3 depósitos PayPal de un mismo usuario
- ✅ Caso 5: Al menos 5 mesas con manos jugadas
- ✅ Caso 6: Al menos 5 usuarios de 3+ países distintos

### **Para Redis (Casos 7-8):**
- ✅ Caso 7: Al menos 5 simulaciones de actividad (opción 9)
- ✅ Caso 8: Al menos 3 usuarios con saldo

### **Para Neo4j (Casos 9-10):**
- ✅ Caso 9: Al menos 3 usuarios sentados en 2+ mesas
- ✅ Caso 10: Al menos 1 par de usuarios en 3+ mesas juntos

---

## 🎮 PROBAR CASOS DE USO

Una vez cargados los datos:

```bash
python pokerstars_app.py
```

- **Opción m** → Ver todos los casos de uso MongoDB (1-6)
- **Opción r** → Ver todos los casos de uso Redis (7-8)
- **Opción n** → Ver todos los casos de uso Neo4j (9-10)

---

## 🔥 CARGA RÁPIDA (15 minutos)

**Script mental rápido:**

1. Crear 5 usuarios (2 min)
2. Crear 5 métodos de pago (1 min)
3. Crear 5 mesas (2 min)
4. Sentar usuarios en mesas - patrón colusión (3 min)
5. Crear 15 manos (5 manos recientes + 5 septiembre + 5 extras) (5 min)
6. Crear 8 transacciones (2 min)
7. Simular actividad Redis 15 veces (1 min)

**Total:** ~15 minutos de carga manual

---

## 💡 TIPS FINALES

1. **Anota los IDs:** Lleva un papel con los IDs de usuarios, mesas, métodos de pago
2. **Septiembre 2024:** Para caso de uso 3, usa fechas como: 2024-09-15, 2024-09-20, 2024-09-25
3. **Botes > $1000:** Para caso 3, al personalizar el bote pon: 1200, 1500, 1800, 2000, 2500
4. **Colusión:** Para caso 10, asegúrate que usuarios 1 y 2 compartan 4 mesas
5. **PayPal:** Crea al menos 3 métodos de pago tipo "paypal" para caso 4

---

¡Listo! Con esta guía podrás cargar todos los datos manualmente desde la aplicación sin necesidad de ejecutar SQL directamente. 🚀
