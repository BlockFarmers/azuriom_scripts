# ============================================================
# Importation des librairies
# ============================================================

import os
import mysql.connector

from dotenv import load_dotenv

# ============================================================
# Chargement des variables d'environnement
# ============================================================

load_dotenv()

WEBSITE_DB_HOST=os.getenv('WEBSITE_DB_HOST')
WEBSITE_DB_PORT=os.getenv('WEBSITE_DB_PORT')
WEBSITE_DB_NAME=os.getenv('WEBSITE_DB_NAME')
WEBSITE_DB_USER=os.getenv('WEBSITE_DB_USER')
WEBSITE_DB_PASS=os.getenv('WEBSITE_DB_PASS')

MC_DB_HOST=os.getenv('MC_DB_HOST')
MC_DB_PORT=os.getenv('MC_DB_PORT')
MC_DB_NAME=os.getenv('MC_DB_NAME')
MC_DB_USER=os.getenv('MC_DB_USER')
MC_DB_PASS=os.getenv('MC_DB_PASS')

NO_SYNC=os.getenv('NO_SYNC').split(',')

# ============================================================
# Connexion aux bases de données
# ============================================================

mcConn = mysql.connector.connect(
    host=MC_DB_HOST,
    port=MC_DB_PORT,
    database=MC_DB_NAME,
    user=MC_DB_USER,
    password=MC_DB_PASS
)

mcCur = mcConn.cursor()

websiteConn = mysql.connector.connect(
    host=WEBSITE_DB_HOST,
    port=WEBSITE_DB_PORT,
    database=WEBSITE_DB_NAME,
    user=WEBSITE_DB_USER,
    password=WEBSITE_DB_PASS
)

websiteCur = websiteConn.cursor()

# ============================================================
# Fonctions utiles
# ============================================================

def getMcPlayers():
    try:
        mcCur.execute("SELECT uuid, primary_group FROM luckperms_players")
        players = mcCur.fetchall()
        mcConn.close()
        return players
    except Exception as e:
        return f"Erreur (getMcPlayers) : {e}"

def getWebsiteUsers():
    try:
        websiteCur.execute(
            """
            SELECT r.name AS role, u.game_id AS uuid
            FROM users u
            JOIN roles r ON u.role_id = r.id
            """
        )
        return websiteCur.fetchall()
    except Exception as e:
        return f"Erreur (getWebsiteUsers) : {e}"

def updateUser(uuid, role):
    try:
        websiteCur.execute(
            """
            UPDATE users SET role_id =
            (SELECT id FROM roles WHERE name = %s)
            WHERE game_id = %s
            """,
            (role, uuid)
        )
        websiteConn.commit()
    except Exception as e:
        return f"Erreur (updateUser) : {e}"

# ============================================================
# Boucle principale
# ============================================================

for player in getMcPlayers():
    player_uuid = player[0].replace('-', '') # UUID sans les -
    player_role = player[1] if player[1] != 'default' else 'joueur' # Si le grade est "default", mettre "joueur" pour le role Azuriom

    for user in getWebsiteUsers():
        user_role = user[0].lower() # Role Azuriom en minuscules
        user_uuid = user[1] # UUID sans les -

        # Si l'uuid est le meme en jeu que sur Azurium mais que les roles ne correspondent pas et que le role n'est pas dans la liste des roles à ne pas synchroniser
        if user_uuid == player_uuid and user_role != player_role and user_role not in NO_SYNC:
            # Mettre à jour le role sur Azuriom
            updateUser(user_uuid, player_role.upper())
