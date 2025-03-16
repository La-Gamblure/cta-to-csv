from simple_app import app

# Point d'entrée pour Vercel
if __name__ == "__main__":
    app.run()

# This is needed for Vercel serverless deployment
application = app
