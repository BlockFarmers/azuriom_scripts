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
# Fonctions utiles - Lecture LuckPerms
# ============================================================

def getMcPlayers():
    """Liste des joueurs connus de LuckPerms avec leur groupe primaire (uuid avec tirets)."""
    try:
        mcCur.execute("SELECT uuid, primary_group FROM luckperms_players")
        return mcCur.fetchall()
    except Exception as e:
        print(f"Erreur (getMcPlayers) : {e}")
        return []

def getMcAddedGroups():
    """
    Groupes ajoutés via '/lp user ... parent add <grade>' (nœuds 'group.<nom>'
    dans luckperms_user_permissions), en ne gardant que les attributions actives
    (value = 1) et non expirées. Retourne un dict {uuid: {grade1, grade2, ...}}.
    """
    try:
        mcCur.execute(
            """
            SELECT uuid, SUBSTRING(permission, 7) AS grade
            FROM luckperms_user_permissions
            WHERE permission LIKE 'group.%%'
              AND value = 1
              AND (expiry = 0 OR expiry > UNIX_TIMESTAMP())
            """
        )
        added_groups = {}
        for uuid, grade in mcCur.fetchall():
            added_groups.setdefault(uuid, set()).add(grade)
        return added_groups
    except Exception as e:
        print(f"Erreur (getMcAddedGroups) : {e}")
        return {}

def getMcGroupWeights():
    """
    Poids de chaque groupe LuckPerms, tels que définis avec
    '/lp group <grade> setweight <n>' (nœuds 'weight.<n>' dans
    luckperms_group_permissions). Retourne un dict {grade: poids}.
    Un groupe sans poids défini vaut 0 par défaut : pense à faire
    un setweight sur chacun de tes grades pour un tri fiable.
    """
    try:
        mcCur.execute(
            """
            SELECT name, permission
            FROM luckperms_group_permissions
            WHERE permission LIKE 'weight.%%'
              AND value = 1
            """
        )
        weights = {}
        for name, permission in mcCur.fetchall():
            try:
                weights[name] = int(permission.split('.', 1)[1])
            except (IndexError, ValueError):
                pass
        return weights
    except Exception as e:
        print(f"Erreur (getMcGroupWeights) : {e}")
        return {}

def getHighestGrade(primary_group, added_groups, weights):
    """
    Détermine, parmi le groupe primaire ('parent set') et les groupes
    ajoutés ('parent add'), celui qui a le poids le plus élevé.
    En cas d'égalité de poids, le choix est fait par ordre alphabétique
    (comportement déterministe, à ajuster si besoin).
    """
    candidates = sorted(added_groups | {primary_group})
    return max(candidates, key=lambda grade: weights.get(grade, 0))

# ============================================================
# Fonctions utiles - Site web (Azuriom)
# ============================================================

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
        print(f"Erreur (getWebsiteUsers) : {e}")
        return []

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
        print(f"Erreur (updateUser) : {e}")

# ============================================================
# Boucle principale
# ============================================================

# Toutes les lectures LuckPerms sont faites avant de fermer la connexion MC
mc_players = getMcPlayers()
mc_added_groups = getMcAddedGroups()
mc_group_weights = getMcGroupWeights()

mcCur.close()
mcConn.close()

# Dictionnaire {uuid sans tirets: role Azuriom en minuscules} pour un lookup en O(1)
website_users = {user_uuid: role.lower() for role, user_uuid in getWebsiteUsers()}

for player_uuid_raw, primary_group in mc_players:
    player_uuid = player_uuid_raw.replace('-', '') # UUID sans les -

    # Grade le plus haut (poids max) parmi le groupe primaire et les groupes ajoutés
    added_groups = mc_added_groups.get(player_uuid_raw, set())
    highest_grade = getHighestGrade(primary_group, added_groups, mc_group_weights)

    player_role = highest_grade if highest_grade != 'default' else 'joueur' # Si le grade est "default", mettre "joueur" pour le role Azuriom

    user_role = website_users.get(player_uuid)

    # Si le joueur a un compte Azuriom, que les roles ne correspondent pas et que
    # le role n'est pas dans la liste des roles à ne pas synchroniser
    if user_role is not None and user_role != player_role and user_role not in NO_SYNC:
        # Mettre à jour le role sur Azuriom
        updateUser(player_uuid, player_role.upper())

websiteCur.close()
websiteConn.close()
