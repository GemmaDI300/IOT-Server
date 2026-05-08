"""
Docker entrypoint: crea tablas, seed del admin y arranca el servidor.
"""
# Importar modelos ANTES de crear tablas (SQLModel necesita conocerlos)
import app.database.model  # noqa: F401
from app.database import create_db_and_tables

if __name__ == "__main__":
    print("Creando tablas de la base de datos...")
    create_db_and_tables()
    print("Tablas creadas.")

    print("Ejecutando seed del administrador...")
    from seed_admin import create_initial_admin
    create_initial_admin()

    print("Iniciando servidor uvicorn...")
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
