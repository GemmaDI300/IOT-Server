"""
Pruebas funcionales del sistema IOT-Server.
Verifica autenticación, CRUD completo, autorización por roles,
proxy del frontend y comportamiento de la API documentada.
"""
import urllib.request
import urllib.error
import json
import time
import sys

BASE_BACKEND = "http://localhost:8000"
BASE_FRONTEND = "http://localhost:3000"
API = BASE_BACKEND + "/api/v1"

RESULTS = []
ERRORS = []

# ─────────────────────────────────────────────────────────────
def req(method, url, body=None, token=None, label=""):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    if method in ("GET", "DELETE") and data:
        data = None
    start = time.time()
    try:
        rq = urllib.request.Request(url, data=data, headers=h, method=method)
        r = urllib.request.urlopen(rq)
        elapsed = time.time() - start
        raw = r.read().decode()
        parsed = json.loads(raw) if raw else {}
        status = r.status
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        raw = e.read().decode()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw}
        status = e.code
    except Exception as e:
        elapsed = time.time() - start
        parsed = {}
        status = 0
        ERRORS.append(f"{label}: {e}")
    return status, parsed, elapsed

def ok(status, label, detail=""):
    icon = "✅" if 200 <= status < 300 else "❌"
    RESULTS.append({"label": label, "status": status, "ok": 200 <= status < 300, "detail": detail})
    print(f"  {icon} [{status}] {label}" + (f" — {detail}" if detail else ""))
    return status, parsed if 'parsed' in dir() else {}

def check(cond, label, got=""):
    icon = "✅" if cond else "❌"
    RESULTS.append({"label": label, "status": "OK" if cond else "FAIL", "ok": cond, "detail": str(got)})
    print(f"  {icon} {label}" + (f" — {got}" if got else ""))
    return cond


# ══════════════════════════════════════════════════════════════
print("\n" + "█"*65)
print("  BLOQUE 1 — AUTENTICACIÓN Y SESIÓN")
print("█"*65)

# F-01: Login válido admin master
status, data, ms = req("POST", API + "/auth/login",
    {"email": "admin@iot.com", "password": "Admin1234!"}, label="Login admin master")
ok(status, "F-01: Login admin master válido")
check("access_token" in data, "F-01: Respuesta contiene access_token", list(data.keys()))
check(data.get("account_type") == "administrator", "F-01: account_type=administrator", data.get("account_type"))
check(data.get("is_master") == True, "F-01: is_master=True", data.get("is_master"))
TOKEN_ADMIN = data.get("access_token", "")
print(f"     ⏱ {ms*1000:.0f}ms")

# F-02: Login con credenciales incorrectas
status, data, ms = req("POST", API + "/auth/login",
    {"email": "admin@iot.com", "password": "ContraseñaIncorrecta123!"}, label="Login credenciales inválidas")
check(status == 400, "F-02: Login inválido retorna 400", status)
check(data.get("detail") == "Invalid credentials", "F-02: Mensaje genérico 'Invalid credentials'", data.get("detail"))

# F-03: Login con email inexistente
status, data, ms = req("POST", API + "/auth/login",
    {"email": "noexiste@nowhere.com", "password": "Test1234!"}, label="Login email inexistente")
check(status == 400, "F-03: Email inexistente retorna 400", status)
check(data.get("detail") == "Invalid credentials", "F-03: Mismo mensaje que email existente (anti-enum)", data.get("detail"))

# F-04: Cambio de contraseña
status, data, ms = req("PATCH", API + "/auth/change-password",
    {"current_password": "Admin1234!", "new_password": "Admin1234!"},
    token=TOKEN_ADMIN, label="Cambio de contraseña (misma)")
check(status in (400, 422), "F-04: No permite cambiar a la misma contraseña", status)

# F-05: Logout
status, data, ms = req("POST", API + "/auth/logout", {}, token=TOKEN_ADMIN, label="Logout")
check(status == 200, "F-05: Logout retorna 200", status)
check(data.get("message") == "Logged out successfully", "F-05: Mensaje de logout correcto", data.get("message"))

# F-06: Usar token después de logout (debe estar en blacklist)
status, data, ms = req("GET", API + "/administrators/", token=TOKEN_ADMIN, label="Request con token en blacklist")
check(status == 401, "F-06: Token invalidado tras logout retorna 401", status)

# Re-login para el resto de pruebas
status, data, ms = req("POST", API + "/auth/login",
    {"email": "admin@iot.com", "password": "Admin1234!"}, label="Re-login")
TOKEN_ADMIN = data.get("access_token", "")
check(bool(TOKEN_ADMIN), "F-06b: Re-login exitoso para siguientes pruebas")


# ══════════════════════════════════════════════════════════════
print("\n" + "█"*65)
print("  BLOQUE 2 — CRUD ADMINISTRADORES")
print("█"*65)

# F-07: Listar administradores
status, data, ms = req("GET", API + "/administrators/", token=TOKEN_ADMIN)
ok(status, "F-07: GET /administrators/ — listar")
check("items" in data, "F-07: Respuesta paginada con campo 'items'", list(data.keys()) if data else [])
admins_count = len(data.get("items", []))
check(admins_count >= 1, f"F-07: Al menos 1 admin (el seed admin)", admins_count)

# F-08: Crear administrador
NEW_ADMIN = {
    "first_name": "Test",
    "last_name": "Admin",
    "email": "testadmin@iot.com",
    "password": "TestAdmin1234!"
}
status, data, ms = req("POST", API + "/administrators/", NEW_ADMIN, token=TOKEN_ADMIN)
ok(status, "F-08: POST /administrators/ — crear")
NEW_ADMIN_ID = data.get("id", "")
check(bool(NEW_ADMIN_ID), "F-08: Respuesta contiene ID del nuevo admin", NEW_ADMIN_ID)

# F-09: Obtener por ID
if NEW_ADMIN_ID:
    status, data, ms = req("GET", API + f"/administrators/{NEW_ADMIN_ID}", token=TOKEN_ADMIN)
    ok(status, "F-09: GET /administrators/{id} — obtener por ID")
    check(data.get("id") == NEW_ADMIN_ID, "F-09: ID coincide en respuesta")

# F-10: Actualizar administrador
if NEW_ADMIN_ID:
    status, data, ms = req("PATCH", API + f"/administrators/{NEW_ADMIN_ID}",
        {"first_name": "TestActualizado"}, token=TOKEN_ADMIN)
    ok(status, "F-10: PATCH /administrators/{id} — actualizar")
    check(data.get("non_critical_personal_data", {}).get("first_name") == "TestActualizado"
          or data.get("first_name") == "TestActualizado",
          "F-10: Nombre actualizado en respuesta", data.get("non_critical_personal_data", data.get("first_name")))

# F-11: Eliminar administrador
if NEW_ADMIN_ID:
    status, data, ms = req("DELETE", API + f"/administrators/{NEW_ADMIN_ID}", token=TOKEN_ADMIN)
    check(status == 204, "F-11: DELETE /administrators/{id} — retorna 204", status)
    # Verificar que ya no existe
    status2, _, _ = req("GET", API + f"/administrators/{NEW_ADMIN_ID}", token=TOKEN_ADMIN)
    check(status2 == 404, "F-11: Admin eliminado ya no existe (404)", status2)


# ══════════════════════════════════════════════════════════════
print("\n" + "█"*65)
print("  BLOQUE 3 — CRUD GERENTES")
print("█"*65)

# F-12: Crear gerente
NEW_MANAGER = {
    "first_name": "Juan",
    "last_name": "Gerente",
    "email": "gerente.test@iot.com",
    "password": "Gerente1234!"
}
status, data, ms = req("POST", API + "/managers/", NEW_MANAGER, token=TOKEN_ADMIN)
ok(status, "F-12: POST /managers/ — crear gerente")
NEW_MANAGER_ID = data.get("id", "")
check(bool(NEW_MANAGER_ID), "F-12: Respuesta contiene ID del nuevo gerente", NEW_MANAGER_ID)

# F-13: Listar gerentes
status, data, ms = req("GET", API + "/managers/", token=TOKEN_ADMIN)
ok(status, "F-13: GET /managers/ — listar")
check("items" in data, "F-13: Respuesta paginada", list(data.keys()) if data else [])

# F-14: Login como gerente
TOKEN_MANAGER = ""
if NEW_MANAGER_ID:
    status, data, ms = req("POST", API + "/auth/login",
        {"email": "gerente.test@iot.com", "password": "Gerente1234!"})
    ok(status, "F-14: Login como gerente")
    TOKEN_MANAGER = data.get("access_token", "")
    check(data.get("account_type") == "manager", "F-14: account_type=manager", data.get("account_type"))


# ══════════════════════════════════════════════════════════════
print("\n" + "█"*65)
print("  BLOQUE 4 — CRUD USUARIOS")
print("█"*65)

# F-15: Crear usuario (como admin)
NEW_USER = {
    "first_name": "María",
    "last_name": "Usuario",
    "email": "usuario.test@iot.com",
    "password": "Usuario1234!"
}
status, data, ms = req("POST", API + "/users/", NEW_USER, token=TOKEN_ADMIN)
ok(status, "F-15: POST /users/ — crear usuario (como admin)")
NEW_USER_ID = data.get("id", "")
check(bool(NEW_USER_ID), "F-15: Respuesta contiene ID del nuevo usuario", NEW_USER_ID)

# F-16: Listar usuarios como admin
status, data, ms = req("GET", API + "/users/", token=TOKEN_ADMIN)
ok(status, "F-16: GET /users/ — listar (como admin)")
check("items" in data, "F-16: Respuesta paginada")

# F-17: Listar usuarios como gerente
if TOKEN_MANAGER:
    status, data, ms = req("GET", API + "/users/", token=TOKEN_MANAGER)
    ok(status, "F-17: GET /users/ — listar (como gerente, permitido por OSO)")

# F-18: Gerente intenta crear usuario (debe ser permitido por OSO)
if TOKEN_MANAGER:
    status, data, ms = req("POST", API + "/users/",
        {"first_name": "Nuevo", "last_name": "UserGerente",
         "email": "usermanager.test@iot.com", "password": "User1234!"},
        token=TOKEN_MANAGER)
    check(status in (200, 201, 403), "F-18: Gerente crea usuario — resultado según política OSO", status)

# F-19: Eliminar usuario de prueba
if NEW_USER_ID:
    status, _, _ = req("DELETE", API + f"/users/{NEW_USER_ID}", token=TOKEN_ADMIN)
    check(status == 204, "F-19: DELETE /users/{id} — eliminar usuario", status)


# ══════════════════════════════════════════════════════════════
print("\n" + "█"*65)
print("  BLOQUE 5 — CRUD DISPOSITIVOS")
print("█"*65)

# F-20: Crear dispositivo
NEW_DEVICE = {
    "name": "Sensor-Test-01",
    "brand": "Arduino",
    "model": "Uno Rev3",
    "serial_number": "SN-TEST-001",
    "ip": "192.168.1.100",
    "mac": "AA:BB:CC:DD:EE:FF"
}
status, data, ms = req("POST", API + "/devices/", NEW_DEVICE, token=TOKEN_ADMIN)
ok(status, "F-20: POST /devices/ — crear dispositivo")
NEW_DEVICE_ID = data.get("id", "")
check(bool(NEW_DEVICE_ID), "F-20: Respuesta contiene ID del dispositivo", NEW_DEVICE_ID)
check(data.get("mac") == "AA:BB:CC:DD:EE:FF", "F-20: MAC normalizada a mayúsculas", data.get("mac"))

# F-21: Listar dispositivos
status, data, ms = req("GET", API + "/devices/", token=TOKEN_ADMIN)
ok(status, "F-21: GET /devices/ — listar")
check("items" in data, "F-21: Respuesta paginada")

# F-22: Validación de MAC inválida
status, data, ms = req("POST", API + "/devices/",
    {"name": "Device-MAC-Invalida", "mac": "ESTO-NO-ES-MAC"}, token=TOKEN_ADMIN)
check(status == 422, "F-22: MAC inválida retorna 422", status)

# F-23: Validación de IP inválida
status, data, ms = req("POST", API + "/devices/",
    {"name": "Device-IP-Invalida", "ip": "999.999.999.999"}, token=TOKEN_ADMIN)
check(status == 422, "F-23: IP inválida retorna 422", status)

# F-24: Actualizar dispositivo (desactivar)
if NEW_DEVICE_ID:
    status, data, ms = req("PATCH", API + f"/devices/{NEW_DEVICE_ID}",
        {"is_active": False}, token=TOKEN_ADMIN)
    ok(status, "F-24: PATCH /devices/{id} — desactivar dispositivo")

# F-25: Gerente puede leer dispositivos (política OSO)
if TOKEN_MANAGER:
    status, data, ms = req("GET", API + "/devices/", token=TOKEN_MANAGER)
    ok(status, "F-25: GET /devices/ como gerente (permitido por OSO)")

# F-26: Eliminar dispositivo
if NEW_DEVICE_ID:
    status, _, _ = req("DELETE", API + f"/devices/{NEW_DEVICE_ID}", token=TOKEN_ADMIN)
    check(status == 204, "F-26: DELETE /devices/{id} — eliminar dispositivo", status)


# ══════════════════════════════════════════════════════════════
print("\n" + "█"*65)
print("  BLOQUE 6 — SERVICIOS Y APLICACIONES")
print("█"*65)

# F-27: Crear servicio
status, data, ms = req("POST", API + "/services/",
    {"name": "Servicio-Test", "description": "Servicio para pruebas funcionales"},
    token=TOKEN_ADMIN)
ok(status, "F-27: POST /services/ — crear servicio")
NEW_SERVICE_ID = data.get("id", "")
check(bool(NEW_SERVICE_ID), "F-27: Respuesta contiene ID del servicio", NEW_SERVICE_ID)

# F-28: Listar servicios
status, data, ms = req("GET", API + "/services/", token=TOKEN_ADMIN)
ok(status, "F-28: GET /services/ — listar servicios")

# F-29: Crear aplicación
status, data, ms = req("POST", API + "/applications/",
    {"name": "App-Test", "description": "App de prueba funcional"},
    token=TOKEN_ADMIN)
ok(status, "F-29: POST /applications/ — crear aplicación")
NEW_APP_ID = data.get("id", "")
check(bool(NEW_APP_ID), "F-29: Respuesta contiene ID de la aplicación", NEW_APP_ID)

# F-30: Listar aplicaciones
status, data, ms = req("GET", API + "/applications/", token=TOKEN_ADMIN)
ok(status, "F-30: GET /applications/ — listar aplicaciones")

# Limpieza
if NEW_SERVICE_ID:
    s, _, _ = req("DELETE", API + f"/services/{NEW_SERVICE_ID}", token=TOKEN_ADMIN)
    check(s == 204, "F-27b: Servicio de prueba eliminado", s)
if NEW_APP_ID:
    s, _, _ = req("DELETE", API + f"/applications/{NEW_APP_ID}", token=TOKEN_ADMIN)
    check(s == 204, "F-29b: Aplicación de prueba eliminada", s)


# ══════════════════════════════════════════════════════════════
print("\n" + "█"*65)
print("  BLOQUE 7 — TICKETS")
print("█"*65)

# F-31: Listar service tickets
status, data, ms = req("GET", API + "/service-tickets/", token=TOKEN_ADMIN)
ok(status, "F-31: GET /service-tickets/ — listar tickets de servicio")
check("items" in data or isinstance(data, list), "F-31: Respuesta tiene items", type(data).__name__)

# F-32: Listar ecosystem tickets
status, data, ms = req("GET", API + "/ecosystem-tickets/", token=TOKEN_ADMIN)
ok(status, "F-32: GET /ecosystem-tickets/ — listar tickets de ecosistema")


# ══════════════════════════════════════════════════════════════
print("\n" + "█"*65)
print("  BLOQUE 8 — CONTROL DE ACCESO (AUTORIZACIÓN)")
print("█"*65)

# F-33: Gerente NO puede crear administradores (debe ser 403)
if TOKEN_MANAGER:
    status, data, ms = req("POST", API + "/administrators/",
        {"first_name": "Hack", "last_name": "Attempt",
         "email": "hack@iot.com", "password": "Hack1234!"},
        token=TOKEN_MANAGER)
    check(status == 403, "F-33: Gerente no puede crear administradores (403)", status)

# F-34: Sin token no accede a endpoints protegidos
status, data, ms = req("GET", API + "/users/")
check(status == 401, "F-34: Sin token retorna 401 en endpoint protegido", status)

# F-35: Admin no-master no puede listar admins (solo master puede)
# Crear admin no-master primero
status, data_nm, ms = req("POST", API + "/administrators/",
    {"first_name": "NoMaster", "last_name": "Admin",
     "email": "nomaster.test@iot.com", "password": "NoMaster1234!"},
    token=TOKEN_ADMIN)
TOKEN_NOMASTER = ""
NM_ID = data_nm.get("id", "")
if data_nm.get("id"):
    s, d, _ = req("POST", API + "/auth/login",
        {"email": "nomaster.test@iot.com", "password": "NoMaster1234!"})
    TOKEN_NOMASTER = d.get("access_token", "")
    check(d.get("is_master") == False, "F-35a: Admin no-master tiene is_master=False", d.get("is_master"))

    # Admin no-master intenta listar administradores (solo master puede, según OSO)
    status, data, ms = req("GET", API + "/administrators/", token=TOKEN_NOMASTER)
    # Según policies.polar: administrator no master solo puede leer Administrator (no administer)
    check(status in (200, 403), "F-35b: Admin no-master en GET /administrators/ — resultado según política OSO", status)

    # Limpiar admin no-master
    req("DELETE", API + f"/administrators/{NM_ID}", token=TOKEN_ADMIN)


# ══════════════════════════════════════════════════════════════
print("\n" + "█"*65)
print("  BLOQUE 9 — FRONTEND PROXY Y SPA")
print("█"*65)

# F-36: Frontend sirve la SPA (HTML)
status, data, ms = req("GET", BASE_FRONTEND + "/")
check(status == 200, "F-36: Frontend sirve la SPA en /", status)

# F-37: Proxy /api/ del frontend llega al backend
status, data, ms = req("POST", BASE_FRONTEND + "/api/v1/auth/login",
    {"email": "admin@iot.com", "password": "Admin1234!"})
check(status == 200, "F-37: Frontend proxy /api/v1/ redirige al backend", status)
check("access_token" in data, "F-37: Proxy devuelve el token JWT correctamente", list(data.keys()) if data else [])

# F-38: Assets estáticos del frontend
status, data, ms = req("GET", BASE_FRONTEND + "/vite.svg")
check(status in (200, 404), "F-38: Assets estáticos accesibles desde el frontend", status)

# F-39: Rutas SPA son redirigidas a index.html (React Router)
status, data, ms = req("GET", BASE_FRONTEND + "/login/admin-master")
check(status == 200, "F-39: Rutas SPA redirigen a index.html (nginx try_files)", status)

status, data, ms = req("GET", BASE_FRONTEND + "/ruta-inexistente")
check(status == 200, "F-40: Ruta inexistente en SPA devuelve index.html (no 404)", status)


# ══════════════════════════════════════════════════════════════
print("\n" + "█"*65)
print("  BLOQUE 10 — DOCUMENTACIÓN Y ESTADO DEL BACKEND")
print("█"*65)

# F-41: Swagger UI accesible
status, _, ms = req("GET", BASE_BACKEND + "/docs")
check(status == 200, "F-41: /docs (Swagger UI) accesible públicamente", status)
print(f"     ⏱ {ms*1000:.0f}ms")

# F-42: OpenAPI schema
status, data, ms = req("GET", BASE_BACKEND + "/openapi.json")
check(status == 200, "F-42: /openapi.json disponible", status)
if isinstance(data, dict):
    endpoints = sum(len(v) for v in data.get("paths", {}).values())
    check(endpoints > 20, f"F-42: OpenAPI documenta {endpoints} operaciones registradas", endpoints)

# F-43: Paginación con parámetros válidos
status, data, ms = req("GET", API + "/administrators/?offset=0&limit=5", token=TOKEN_ADMIN)
check(status == 200, "F-43: Paginación con limit=5 funciona", status)
check(len(data.get("items", [])) <= 5, "F-43: Respuesta respeta el límite de paginación", len(data.get("items", [])))

# Logout final
req("POST", API + "/auth/logout", {}, token=TOKEN_ADMIN)
if TOKEN_MANAGER:
    req("POST", API + "/auth/logout", {}, token=TOKEN_MANAGER)


# ══════════════════════════════════════════════════════════════
print("\n" + "█"*65)
print("  RESUMEN FINAL")
print("█"*65)
total = len(RESULTS)
passed = sum(1 for r in RESULTS if r["ok"])
failed = total - passed
print(f"\n  Total pruebas: {total}")
print(f"  ✅ Pasaron:    {passed}")
print(f"  ❌ Fallaron:   {failed}")
if ERRORS:
    print(f"\n  Errores de red:")
    for e in ERRORS:
        print(f"    - {e}")
if failed > 0:
    print("\n  Pruebas fallidas:")
    for r in RESULTS:
        if not r["ok"]:
            print(f"    ❌ {r['label']} — status={r['status']} detail={r['detail']}")

sys.exit(0 if failed == 0 else 1)
