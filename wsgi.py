# wsgi.py

from autointelli import create_app

# Crea la aplicación llamando a la fábrica
app = create_app()

# Gunicorn buscará la variable 'app' en este archivo
# Puedes añadir logging básico si necesitas diagnosticar errores *antes* de que la app esté completamente configurada
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("WSGI: Application factory called.")