from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello World! This is a simple test for Vercel deployment."

# Point d'entrée pour Vercel
if __name__ == "__main__":
    app.run()
