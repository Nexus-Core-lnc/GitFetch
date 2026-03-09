# init_db.py
from application import application
from models import db
import sys

def init_database():
    """Initialise la base de données Neon"""
    with application.app_context():
        print("=" * 50)
        print("🚀 Initialisation de la base de données Neon")
        print("=" * 50)
        
        # Afficher l'URI (masqué)
        db_uri = application.config['SQLALCHEMY_DATABASE_URI']
        masked_uri = db_uri.replace(db_uri.split(':')[2].split('@')[0], '*****')
        print(f"📦 Connexion à: {masked_uri}")
        
        try:
            # Test de connexion
            print("\n🔍 Test de connexion...")
            db.session.execute('SELECT 1')
            db.session.commit()
            print("✅ Connexion réussie!")
            
            # Création des tables
            print("\n🏗️  Création des tables...")
            db.create_all()
            print("✅ Tables créées avec succès!")
            
            # Vérification
            from models import Utilisateur, Projet, PortfolioConfig, AboutPage
            
            tables = [
                ('utilisateurs', Utilisateur),
                ('projets', Projet),
                ('portfolio_config', PortfolioConfig),
                ('about_pages', AboutPage)
            ]
            
            print("\n📋 Tables créées:")
            for table_name, model in tables:
                try:
                    count = db.session.query(model).count()
                    print(f"   - {table_name}: {count} enregistrements")
                except Exception as e:
                    print(f"   - {table_name}: ⚠️ Erreur de vérification")
            
            print("\n✅ Base de données initialisée avec succès!")
            return True
            
        except Exception as e:
            print(f"\n❌ Erreur lors de l'initialisation: {e}")
            print("\n🔧 Vérifications:")
            print("   1. Votre URI Neon est correcte")
            print("   2. Le SSL est bien configuré (sslmode=require)")
            print("   3. Votre IP n'est pas bloquée par Neon")
            print("   4. La base de données 'neondb' existe")
            return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)