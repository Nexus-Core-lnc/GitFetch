# check_db.py
from application import application
from models import db
import sys

def check_connection():
    """Vérifie la connexion à Neon"""
    with application.app_context():
        print("=" * 60)
        print("🔍 VÉRIFICATION DE LA CONNEXION NEON")
        print("=" * 60)
        
        # 1. Vérifier l'URI
        db_uri = application.config['SQLALCHEMY_DATABASE_URI']
        masked_uri = db_uri.replace(db_uri.split(':')[2].split('@')[0], '*****')
        print(f"\n📌 URI: {masked_uri}")
        
        # 2. Vérifier la configuration SSL
        engine_options = application.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})
        connect_args = engine_options.get('connect_args', {})
        print(f"\n📌 SSL requis: {'Oui' if connect_args.get('sslmode') == 'require' else 'Non'}")
        
        # 3. Tester la connexion
        print("\n🔄 Test de connexion...")
        try:
            db.session.execute('SELECT version()')
            result = db.session.execute('SELECT current_database(), current_user')
            db_name, db_user = result.first()
            db.session.commit()
            
            print(f"✅ CONNEXION RÉUSSIE!")
            print(f"   Base de données: {db_name}")
            print(f"   Utilisateur: {db_user}")
            
            # 4. Vérifier les tables existantes
            print("\n📋 Tables existantes:")
            tables = db.session.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """).fetchall()
            
            if tables:
                for table in tables:
                    count = db.session.execute(f"SELECT COUNT(*) FROM {table[0]}").scalar()
                    print(f"   - {table[0]}: {count} lignes")
            else:
                print("   ⚠️ Aucune table trouvée (base de données vide)")
                print("   Exécutez 'python init_db.py' pour créer les tables")
            
            return True
            
        except Exception as e:
            print(f"❌ ERREUR DE CONNEXION: {e}")
            print("\n🔧 Causes possibles:")
            print("   1. URI incorrecte")
            print("   2. Problème de réseau (port 5432 bloqué)")
            print("   3. SSL non accepté par Neon")
            print("   4. Compte PythonAnywhere gratuit (blocage des ports externes)")
            return False

if __name__ == "__main__":
    success = check_connection()
    sys.exit(0 if success else 1)