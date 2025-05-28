import streamlit as st
import sqlite3
from datetime import date

DB_NAME = "HotelDB.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            email TEXT UNIQUE,
            telephone TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chambres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            prix_nuit REAL NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            chambre_id INTEGER NOT NULL,
            date_arrivee DATE NOT NULL,
            date_depart DATE NOT NULL,
            statut TEXT DEFAULT 'Confirmée',
            FOREIGN KEY (client_id) REFERENCES clients(id),
            FOREIGN KEY (chambre_id) REFERENCES chambres(id)
        )
    ''')
    conn.commit()
    conn.close()

def get_all_clients():
    conn = get_db_connection()
    clients = conn.execute("SELECT * FROM clients ORDER BY nom").fetchall()
    conn.close()
    return clients

def get_all_reservations():
    conn = get_db_connection()
    reservations = conn.execute("""
        SELECT r.id, c.nom, c.prenom, ch.numero, ch.type, r.date_arrivee, r.date_depart, r.statut
        FROM reservations r
        JOIN clients c ON r.client_id = c.id
        JOIN chambres ch ON r.chambre_id = ch.id
        ORDER BY r.date_arrivee DESC
    """).fetchall()
    conn.close()
    return reservations

def get_chambres_disponibles(date_arrivee, date_depart):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT * FROM chambres
        WHERE id NOT IN (
            SELECT chambre_id FROM reservations
            WHERE NOT (date_depart <= ? OR date_arrivee >= ?)
        )
        ORDER BY numero
    """
    cursor.execute(query, (date_arrivee, date_depart))
    chambres = cursor.fetchall()
    conn.close()
    return chambres

def add_client(nom, prenom, email, telephone):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO clients (nom, prenom, email, telephone) VALUES (?, ?, ?, ?)",
                       (nom, prenom, email, telephone))
        conn.commit()
        return True, "Client ajouté avec succès."
    except sqlite3.IntegrityError:
        return False, "Erreur : email déjà utilisé."
    finally:
        conn.close()

def add_reservation(client_id, chambre_id, date_arrivee, date_depart):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT id FROM reservations
        WHERE chambre_id = ?
        AND NOT (date_depart <= ? OR date_arrivee >= ?)
    """
    cursor.execute(query, (chambre_id, date_arrivee, date_depart))
    conflit = cursor.fetchone()
    if conflit:
        conn.close()
        return False, "Erreur : la chambre est déjà réservée pendant cette période."

    cursor.execute("""
        INSERT INTO reservations (client_id, chambre_id, date_arrivee, date_depart)
        VALUES (?, ?, ?, ?)
    """, (client_id, chambre_id, date_arrivee, date_depart))
    conn.commit()
    conn.close()
    return True, "Réservation ajoutée avec succès."

# Initialiser base
init_db()

st.title("Gestion Hôtel - Interface")

# Menu en haut, aligné à gauche
menu = st.radio(
    "Sélectionnez une fonctionnalité :",
    ("Liste des réservations", "Liste des clients", "Chambres disponibles", "Ajouter un client", "Ajouter une réservation"),
    horizontal=True
)

# Pour un affichage contenu à gauche on peut aussi créer une colonne principale étroite, si tu veux
# Ici on reste simple, tout en page classique.

if menu == "Liste des réservations":
    st.header("Liste des réservations")
    reservations = get_all_reservations()
    if reservations:
        for r in reservations:
            st.write(f"Réservation #{r['id']}: Client {r['nom']} {r['prenom']}, Chambre {r['numero']} ({r['type']}), du {r['date_arrivee']} au {r['date_depart']} - Statut: {r['statut']}")
    else:
        st.info("Aucune réservation trouvée.")

elif menu == "Liste des clients":
    st.header("Liste des clients")
    clients = get_all_clients()
    if clients:
        for c in clients:
            st.write(f"{c['id']}: {c['nom']} {c['prenom']} - Email: {c['email']} - Téléphone: {c['telephone']}")
    else:
        st.info("Aucun client trouvé.")

elif menu == "Chambres disponibles":
    st.header("Rechercher chambres disponibles")

    date_arrivee = st.date_input("Date d'arrivée", date.today())
    date_depart = st.date_input("Date de départ", date.today())

    if st.button("Rechercher"):
        if date_depart <= date_arrivee:
            st.error("La date de départ doit être après la date d'arrivée.")
        else:
            chambres = get_chambres_disponibles(date_arrivee.isoformat(), date_depart.isoformat())
            if chambres:
                st.success(f"Chambres disponibles du {date_arrivee} au {date_depart} :")
                for ch in chambres:
                    st.write(f"Chambre {ch['numero']} ({ch['type']}) - Prix par nuit : {ch['prix_nuit']}€")
            else:
                st.warning("Aucune chambre disponible pour cette période.")

elif menu == "Ajouter un client":
    st.header("Ajouter un nouveau client")

    nom = st.text_input("Nom")
    prenom = st.text_input("Prénom")
    email = st.text_input("Email")
    telephone = st.text_input("Téléphone")

    if st.button("Ajouter client"):
        if not nom or not prenom:
            st.error("Nom et prénom obligatoires.")
        else:
            ok, msg = add_client(nom, prenom, email, telephone)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

elif menu == "Ajouter une réservation":
    st.header("Ajouter une nouvelle réservation")

    clients = get_all_clients()

    if not clients:
        st.warning("Veuillez d'abord ajouter des clients.")
    else:
        client_options = {f"{c['nom']} {c['prenom']}": c['id'] for c in clients}
        client_selection = st.selectbox("Client", list(client_options.keys()))

        date_arrivee = st.date_input("Date d'arrivée", date.today())
        date_depart = st.date_input("Date de départ", date.today())

        if date_depart <= date_arrivee:
            st.error("La date de départ doit être après la date d'arrivée.")
        else:
            chambres = get_chambres_disponibles(date_arrivee.isoformat(), date_depart.isoformat())
            if not chambres:
                st.warning("Aucune chambre disponible pour cette période.")
            else:
                chambre_options = {f"Chambre {ch['numero']} ({ch['type']})": ch['id'] for ch in chambres}
                chambre_selection = st.selectbox("Chambre", list(chambre_options.keys()))

                if st.button("Ajouter réservation"):
                    ok, msg = add_reservation(client_options[client_selection], chambre_options[chambre_selection], date_arrivee.isoformat(), date_depart.isoformat())
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
