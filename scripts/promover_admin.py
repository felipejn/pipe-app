# scripts/promover_admin.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from app.auth.models import User

app = create_app()
with app.app_context():
    username = input("Username a promover: ")
    u = User.query.filter_by(username=username).first()
    if not u:
        print("Utilizador não encontrado.")
    else:
        u.is_admin = True
        db.session.commit()
        print(f"{u.username} é agora admin.")