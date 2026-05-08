"""
Pruebas de manejo de excepciones en el frontend IOT-Server.
Hace peticiones directamente al backend (puerto 8000) simulando
lo que el frontend enviaría en cada escenario de error.
"""
import urllib.request
import urllib.error
import json
import time

BASE = "http://localhost:8000"
RESULTS = []

def req(label, url, body=None, content_type="application/json", method=None, extra_headers=None):
    h = {"Content-Type": content_type}
    if extra_headers:
        h.update(extra_headers)
    data = body.encode("utf-8") if isinstance(body, str) else body
    m = method or ("POST" if data is not None else "GET")
    print(f"\n{'─'*65}")
    print(f"  {label}")
    print(f"{'─'*65}")
    try:
        rq = urllib.request.Request(url, data=data, headers=h, method=m)
        r = urllib.request.urlopen(rq)
        resp_body = r.read().decode()
        print(f"HTTP {r.status} ✓")
        print(resp_body[:400])
        RESULTS.append({"test": label, "status": r.status, "body": resp_body[:200]})
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode()
        print(f"HTTP {e.code} {e.reason}")
        print(resp_body[:400])
        RESULTS.append({"test": label, "status": e.code, "body": resp_body[:200]})
    except Exception as e:
        print(f"RED_FLAG — Sin respuesta HTTP: {e}")
        RESULTS.append({"test": label, "status": "NO_RESPONSE", "body": str(e)})

# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 1 — CUERPO Y CAMPOS MALFORMADOS (simula bugs en fetch() del frontend)
# ══════════════════════════════════════════════════════════════════════════════
print("\n\n██████████  BLOQUE 1: CUERPO MALFORMADO  ██████████")

req("T-01 Body completamente vacío", BASE + "/api/v1/auth/login", "")
req("T-02 Falta campo 'password'", BASE + "/api/v1/auth/login", '{"email":"admin@test.com"}')
req("T-03 Tipos incorrectos (int/bool)", BASE + "/api/v1/auth/login", '{"email":99999,"password":true}')
req("T-04 JSON malformado (sintaxis rota)", BASE + "/api/v1/auth/login", '{"email":"x@x.com","password":')
req("T-05 Content-Type text/plain", BASE + "/api/v1/auth/login",
    '{"email":"admin@iot.com","password":"Admin1234!"}', "text/plain")
req("T-06 Body es un array, no objeto", BASE + "/api/v1/auth/login", '[1, 2, 3]')
req("T-07 Payload null literal", BASE + "/api/v1/auth/login", "null")
req("T-08 Campos extra desconocidos", BASE + "/api/v1/auth/login",
    '{"email":"admin@iot.com","password":"Admin1234!","extra_field":"HACKED","role":"admin"}')

# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 2 — INYECCIÓN EN CAMPOS (XSS, SQLi, SSTI, Command)
# ══════════════════════════════════════════════════════════════════════════════
print("\n\n██████████  BLOQUE 2: INYECCIÓN EN CAMPOS  ██████████")

req("T-09 XSS en email", BASE + "/api/v1/auth/login",
    '{"email":"<script>alert(1)</script>@x.com","password":"Test1234!"}')
req("T-10 SQL injection clásico en email", BASE + "/api/v1/auth/login",
    '{"email":"admin@x.com\' OR \'1\'=\'1","password":"Test1234!"}')
req("T-11 SSTI Jinja2 en password", BASE + "/api/v1/auth/login",
    '{"email":"admin@iot.com","password":"{{7*7}}Admin1234!"}')
req("T-12 Command injection en email", BASE + "/api/v1/auth/login",
    '{"email":"admin@iot.com; rm -rf /","password":"Test1234!"}')
req("T-13 Null bytes en campos", BASE + "/api/v1/auth/login",
    '{"email":"admin\\u0000@iot.com","password":"Admin1234!"}')
req("T-14 Longitud extrema en email (5000 chars)", BASE + "/api/v1/auth/login",
    '{"email":"' + "a" * 5000 + '@iot.com","password":"Admin1234!"}')
req("T-15 Unicode/emoji en password", BASE + "/api/v1/auth/login",
    '{"email":"admin@iot.com","password":"😈💀🔓Admin1234!"}')

# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 3 — TOKENS JWT INVÁLIDOS (simula parseApiError en useGetQuery)
# ══════════════════════════════════════════════════════════════════════════════
print("\n\n██████████  BLOQUE 3: TOKENS JWT INVÁLIDOS  ██████████")

req("T-16 Sin header Authorization (GET protegido)", BASE + "/api/v1/users/", method="GET")

req("T-17 Token vacío string", BASE + "/api/v1/users/", method="GET",
    extra_headers={"Authorization": "Bearer "})

req("T-18 Token completamente inválido (basura)", BASE + "/api/v1/users/", method="GET",
    extra_headers={"Authorization": "Bearer ESTE_NO_ES_UN_JWT_VALIDO"})

req("T-19 JWT con firma incorrecta (algoritmo HS256 clave equivocada)", BASE + "/api/v1/users/", method="GET",
    extra_headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDEiLCJ0eXBlIjoiYWRtaW5pc3RyYXRvciIsImlzX21hc3RlciI6dHJ1ZX0.FIRMA_INVALIDA_AQUI"})

req("T-20 JWT expirado (exp en el pasado)", BASE + "/api/v1/users/", method="GET",
    extra_headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNjAwMDAwMDAwfQ.XXXXXXXXXXX"})

req("T-21 Esquema BASIC en vez de Bearer", BASE + "/api/v1/users/", method="GET",
    extra_headers={"Authorization": "Basic YWRtaW46cGFzc3dvcmQ="})

req("T-22 JWT con alg:none (algoritmo none attack)", BASE + "/api/v1/users/", method="GET",
    extra_headers={"Authorization": "Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhZG1pbiIsInR5cGUiOiJhZG1pbmlzdHJhdG9yIn0."})

# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 4 — RUTAS Y PARÁMETROS INVÁLIDOS
# ══════════════════════════════════════════════════════════════════════════════
print("\n\n██████████  BLOQUE 4: RUTAS Y PARÁMETROS INVÁLIDOS  ██████████")

req("T-23 Ruta completamente inexistente", BASE + "/api/v1/no-existe/ruta/falsa", method="GET")

req("T-24 Método HTTP incorrecto (GET en endpoint POST)", BASE + "/api/v1/auth/login", method="GET")

req("T-25 UUID inválido en path param (texto en lugar de UUID)",
    BASE + "/api/v1/users/ESTO_NO_ES_UUID", method="GET",
    extra_headers={"Authorization": "Bearer token_invalido"})

req("T-26 Path traversal en parámetro", BASE + "/api/v1/users/../../../../etc/passwd",
    method="GET", extra_headers={"Authorization": "Bearer token_invalido"})

req("T-27 Paginación negativa", BASE + "/api/v1/users/?offset=-999&limit=-1", method="GET",
    extra_headers={"Authorization": "Bearer token_invalido"})

req("T-28 Paginación con inyección", BASE + "/api/v1/users/?offset=0%3BDROP+TABLE+users&limit=10",
    method="GET", extra_headers={"Authorization": "Bearer token_invalido"})

# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 5 — HEADERS ANÓMALOS
# ══════════════════════════════════════════════════════════════════════════════
print("\n\n██████████  BLOQUE 5: HEADERS ANÓMALOS  ██████████")

req("T-29 Header X-Forwarded-For falsificado (bypass IP)", BASE + "/api/v1/auth/login",
    '{"email":"admin@iot.com","password":"Admin1234!"}',
    extra_headers={"X-Forwarded-For": "127.0.0.1"})

req("T-30 Header Host manipulado", BASE + "/api/v1/auth/login",
    '{"email":"admin@iot.com","password":"Admin1234!"}',
    extra_headers={"Host": "evil.com"})

# ══════════════════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ══════════════════════════════════════════════════════════════════════════════
print("\n\n██████████  RESUMEN  ██████████")
status_counts = {}
for r in RESULTS:
    s = str(r["status"])
    status_counts[s] = status_counts.get(s, 0) + 1
print(f"\nTotal de pruebas: {len(RESULTS)}")
for code, count in sorted(status_counts.items()):
    print(f"  HTTP {code}: {count} pruebas")
