# run.py
# Este archivo es opcional si usas FLASK_APP=autointelli:create_app() y flask run

from autointelli import create_app

app = create_app()

if __name__ == '__main__':
    # Usa el servidor de desarrollo de Flask
    app.run(debug=True) # debug=True es solo para desarrollo