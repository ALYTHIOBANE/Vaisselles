import sys
import sqlite3
import os
from datetime import datetime, date
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
                             QPushButton, QLineEdit, QLabel, QComboBox, QSpinBox,
                             QDoubleSpinBox, QDateEdit, QTextEdit, QMessageBox,
                             QDialog, QFormLayout, QDialogButtonBox, QHeaderView,
                             QGroupBox, QGridLayout, QFrame, QSplitter, QListWidget,
                             QProgressBar, QStatusBar, QMenuBar, QAction, QFileDialog,
                             QCheckBox)  # Assure-toi que QCheckBox est bien importé
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import pandas as pd

class DatabaseManager:
    def __init__(self, db_path="stock_vaisselle.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données avec les tables nécessaires"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table des articles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                designation TEXT NOT NULL,
                categorie TEXT NOT NULL,
                quantite INTEGER DEFAULT 0,
                unite TEXT DEFAULT 'pièce',
                prix_unitaire REAL DEFAULT 0.0,
                seuil_minimum INTEGER DEFAULT 10,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table des entrées
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entrees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                quantite INTEGER NOT NULL,
                date_entree DATE NOT NULL,
                fournisseur TEXT,
                prix_total REAL DEFAULT 0.0,
                commentaire TEXT,
                FOREIGN KEY (article_id) REFERENCES articles (id)
            )
        ''')
        
        # Table des sorties
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sorties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                quantite INTEGER NOT NULL,
                date_sortie DATE NOT NULL,
                motif TEXT NOT NULL,
                utilisateur TEXT,
                commentaire TEXT,
                FOREIGN KEY (article_id) REFERENCES articles (id)
            )
        ''')
        
        # Table des utilisateurs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS utilisateurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom_utilisateur TEXT UNIQUE NOT NULL,
                mot_de_passe TEXT NOT NULL,
                role TEXT DEFAULT 'utilisateur',
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insérer un utilisateur admin par défaut
        cursor.execute('''
            INSERT OR IGNORE INTO utilisateurs (nom_utilisateur, mot_de_passe, role)
            VALUES ('admin', 'admin123', 'admin')
        ''')
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query, params=None):
        """Exécute une requête et retourne les résultats"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
        else:
            conn.commit()
            results = cursor.rowcount
        
        conn.close()
        return results

    def get_total_ventes_du_jour(self):
        """Calcule la somme totale des produits vendus aujourd'hui"""
        today = date.today().isoformat()
        query = """
            SELECT SUM(s.quantite * a.prix_unitaire)
            FROM sorties s
            JOIN articles a ON s.article_id = a.id
            WHERE s.date_sortie = ?
        """
        total = self.db_manager.execute_query(query, (today,))[0][0]
        return total or 0

class LoginDialog(QDialog):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.user_role = None
        self.username = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Connexion - Gestion de Stocks")
        self.setFixedSize(340, 260)
        self.setStyleSheet("""
            QDialog {
                background: #f7f7fa;
                border-radius: 12px;
            }
            QLabel#titleLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2d3a4b;
            }
            QLineEdit, QComboBox {
                border: 1.5px solid #b0b8c1;
                border-radius: 8px;
                padding: 6px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #4a90e2;
                background: #eaf4ff;
            }
            QPushButton {
                background: #4a90e2;
                color: white;
                border-radius: 8px;
                padding: 8px 0;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #357ab8;
            }
            QCheckBox {
                font-size: 12px;
                color: #2d3a4b;
            }
        """)

        layout = QVBoxLayout()

        # Titre
        title = QLabel("Gestion de Stocks de Vaisselle")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Formulaire de connexion
        form_layout = QFormLayout()
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Nom d'utilisateur")
        form_layout.addRow("Utilisateur:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Mot de passe")
        form_layout.addRow("Mot de passe:", self.password_edit)

        # Option afficher le mot de passe
        self.show_password_cb = QCheckBox("Afficher le mot de passe")
        self.show_password_cb.toggled.connect(
            lambda checked: self.password_edit.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        )
        form_layout.addRow("", self.show_password_cb)

        layout.addLayout(form_layout)

        # Boutons
        button_layout = QHBoxLayout()
        login_btn = QPushButton("Se connecter")
        login_btn.clicked.connect(self.login)
        login_btn.setDefault(True)
        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(login_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        # Info par défaut
        # info_label = QLabel("Défaut: admin / admin123")
        # info_label.setStyleSheet("color: gray; font-size: 10px;")
        # info_label.setAlignment(Qt.AlignCenter)
        # layout.addWidget(info_label)

        # Footer élégant
        footer = QLabel("© 2025 Gestion de Stocks de Vaisselle - Tous droits réservés")
        footer.setStyleSheet("color: #8a8a8a; font-size: 11px; margin-top: 18px;")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

        self.setLayout(layout)
        self.password_edit.returnPressed.connect(self.login)

    def login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "Erreur", "Veuillez saisir le nom d'utilisateur et le mot de passe.")
            return
        query = "SELECT role FROM utilisateurs WHERE nom_utilisateur = ? AND mot_de_passe = ?"
        result = self.db_manager.execute_query(query, (username, password))
        if result:
            self.user_role = result[0][0]
            self.username = username
            self.accept()
        else:
            QMessageBox.warning(self, "Erreur", "Nom d'utilisateur ou mot de passe incorrect.")

class ArticleDialog(QDialog):
    def __init__(self, db_manager, article_data=None):
        super().__init__()
        self.db_manager = db_manager
        self.article_data = article_data
        self.init_ui()
        
        if article_data:
            self.load_article_data()
    
    def init_ui(self):
        self.setWindowTitle("Ajouter un article" if not self.article_data else "Modifier l'article")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Formulaire
        form_layout = QFormLayout()
        
        self.designation_edit = QLineEdit()
        form_layout.addRow("Désignation:", self.designation_edit)
        
        self.categorie_combo = QComboBox()
        self.categorie_combo.setEditable(True)
        categories = ["Assiettes", "Verres", "Couverts", "Plats", "Bols", "Tasses", "Autre"]
        self.categorie_combo.addItems(categories)
        form_layout.addRow("Catégorie:", self.categorie_combo)
        
        self.quantite_spin = QSpinBox()
        self.quantite_spin.setRange(0, 999999)
        form_layout.addRow("Quantité initiale:", self.quantite_spin)
        
        self.unite_combo = QComboBox()
        self.unite_combo.setEditable(True)
        unites = ["pièce", "lot", "ensemble", "kg", "g"]
        self.unite_combo.addItems(unites)
        form_layout.addRow("Unité:", self.unite_combo)
        
        self.prix_spin = QDoubleSpinBox()
        self.prix_spin.setRange(0, 999999.99)
        self.prix_spin.setDecimals(2)
        self.prix_spin.setSuffix(" FCFA")
        form_layout.addRow("Prix unitaire:", self.prix_spin)
        
        self.seuil_spin = QSpinBox()
        self.seuil_spin.setRange(0, 999999)
        self.seuil_spin.setValue(10)
        form_layout.addRow("Seuil minimum:", self.seuil_spin)
        
        layout.addLayout(form_layout)
        
        # Boutons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def load_article_data(self):
        """Charge les données de l'article pour modification"""
        self.designation_edit.setText(self.article_data[1])
        self.categorie_combo.setCurrentText(self.article_data[2])
        self.quantite_spin.setValue(self.article_data[3])
        self.unite_combo.setCurrentText(self.article_data[4])
        self.prix_spin.setValue(self.article_data[5])
        self.seuil_spin.setValue(self.article_data[6])
    
    def get_data(self):
        """Retourne les données du formulaire"""
        return {
            'designation': self.designation_edit.text().strip(),
            'categorie': self.categorie_combo.currentText().strip(),
            'quantite': self.quantite_spin.value(),
            'unite': self.unite_combo.currentText().strip(),
            'prix_unitaire': self.prix_spin.value(),
            'seuil_minimum': self.seuil_spin.value()
        }

class MouvementDialog(QDialog):
    def __init__(self, db_manager, movement_type, articles):
        super().__init__()
        self.db_manager = db_manager
        self.movement_type = movement_type  # 'entree' ou 'sortie'
        self.articles = articles
        self.init_ui()
    
    def init_ui(self):
        title = "Nouvelle entrée" if self.movement_type == 'entree' else "Nouvelle sortie"
        self.setWindowTitle(title)
        self.setFixedSize(400, 350)
        
        layout = QVBoxLayout()
        
        # Formulaire
        form_layout = QFormLayout()
        
        # Article
        self.article_combo = QComboBox()
        for article in self.articles:
            self.article_combo.addItem(f"{article[1]} ({article[3]} {article[4]})", article[0])
        form_layout.addRow("Article:", self.article_combo)
        
        # Quantité
        self.quantite_spin = QSpinBox()
        self.quantite_spin.setRange(1, 999999)
        form_layout.addRow("Quantité:", self.quantite_spin)
        
        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form_layout.addRow("Date:", self.date_edit)
        
        if self.movement_type == 'entree':
            # Fournisseur
            self.fournisseur_edit = QLineEdit()
            form_layout.addRow("Fournisseur:", self.fournisseur_edit)
            
            # Prix total
            self.prix_spin = QDoubleSpinBox()
            self.prix_spin.setRange(0, 999999.99)
            self.prix_spin.setDecimals(2)
            self.prix_spin.setSuffix(" FCFA")
            form_layout.addRow("Prix total:", self.prix_spin)
        
        else:  # sortie
            # Motif
            self.motif_combo = QComboBox()
            self.motif_combo.setEditable(True)
            motifs = ["Utilisation", "Prêt", "Casse", "Perte", "Don", "Autre"]
            self.motif_combo.addItems(motifs)
            form_layout.addRow("Motif:", self.motif_combo)
            
            # Utilisateur
            self.utilisateur_edit = QLineEdit()
            form_layout.addRow("Utilisateur:", self.utilisateur_edit)
        
        # Commentaire
        self.commentaire_edit = QTextEdit()
        self.commentaire_edit.setMaximumHeight(80)
        form_layout.addRow("Commentaire:", self.commentaire_edit)
        
        layout.addLayout(form_layout)
        
        # Boutons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_data(self):
        """Retourne les données du formulaire"""
        data = {
            'article_id': self.article_combo.currentData(),
            'quantite': self.quantite_spin.value(),
            'date': self.date_edit.date().toPyDate(),
            'commentaire': self.commentaire_edit.toPlainText().strip()
        }
        
        if self.movement_type == 'entree':
            data.update({
                'fournisseur': self.fournisseur_edit.text().strip(),
                'prix_total': self.prix_spin.value()
            })
        else:
            data.update({
                'motif': self.motif_combo.currentText().strip(),
                'utilisateur': self.utilisateur_edit.text().strip()
            })
        
        return data

class StockManagementApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.current_user = None
        self.user_role = None
        
        # Connexion
        if not self.authenticate():
            sys.exit()
        
        self.init_ui()
        self.load_data()
        
        # Timer pour vérifier les stocks bas
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_low_stock)
        self.timer.start(60000)  # Vérification toutes les minutes
    
    def authenticate(self):
        """Gère l'authentification"""
        login_dialog = LoginDialog(self.db_manager)
        if login_dialog.exec_() == QDialog.Accepted:
            self.current_user = login_dialog.username
            self.user_role = login_dialog.user_role
            return True
        return False
    
    def init_ui(self):
        self.setWindowTitle(f"Gestion de Stocks de Vaisselle - {self.current_user} ({self.user_role})")
        self.setGeometry(100, 100, 1200, 800)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Barre d'outils
        self.create_toolbar()
        
        # Onglets
        self.tab_widget = QTabWidget()
        
        # Onglet Articles
        self.articles_tab = self.create_articles_tab()
        self.tab_widget.addTab(self.articles_tab, "Articles")
        
        # Onglet Entrées
        self.entrees_tab = self.create_entrees_tab()
        self.tab_widget.addTab(self.entrees_tab, "Entrées")
        
        # Onglet Sorties
        self.sorties_tab = self.create_sorties_tab()
        self.tab_widget.addTab(self.sorties_tab, "Sorties")
        
        # Onglet Tableau de bord
        self.dashboard_tab = self.create_dashboard_tab()
        self.tab_widget.addTab(self.dashboard_tab, "Tableau de bord")
        
        main_layout.addWidget(self.tab_widget)
        
        # Barre de statut
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Prêt")
    
    def create_toolbar(self):
        """Crée la barre d'outils"""
        toolbar = self.addToolBar("Actions")
        
        # Nouveau article
        new_article_action = QAction("Nouvel Article", self)
        new_article_action.triggered.connect(self.add_article)
        toolbar.addAction(new_article_action)
        
        toolbar.addSeparator()
        
        # Nouvelle entrée
        new_entry_action = QAction("Nouvelle Entrée", self)
        new_entry_action.triggered.connect(self.add_entree)
        toolbar.addAction(new_entry_action)
        
        # Nouvelle sortie
        new_exit_action = QAction("Nouvelle Sortie", self)
        new_exit_action.triggered.connect(self.add_sortie)
        toolbar.addAction(new_exit_action)
        
        toolbar.addSeparator()
        
        # Rapports
        report_action = QAction("Générer Rapport", self)
        report_action.triggered.connect(self.generate_report)
        toolbar.addAction(report_action)
        
        toolbar.addSeparator()
        
        # Actualiser
        refresh_action = QAction("Actualiser", self)
        refresh_action.triggered.connect(self.load_data)
        toolbar.addAction(refresh_action)
    
    def create_articles_tab(self):
        """Crée l'onglet de gestion des articles"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Barre de recherche et filtres
        search_layout = QHBoxLayout()
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Rechercher un article...")
        self.search_edit.textChanged.connect(self.filter_articles)
        search_layout.addWidget(QLabel("Recherche:"))
        search_layout.addWidget(self.search_edit)
        
        self.category_filter = QComboBox()
        self.category_filter.addItem("Toutes les catégories")
        self.category_filter.currentTextChanged.connect(self.filter_articles)
        search_layout.addWidget(QLabel("Catégorie:"))
        search_layout.addWidget(self.category_filter)
        
        self.stock_filter = QComboBox()
        self.stock_filter.addItems(["Tous les stocks", "Stock normal", "Stock bas", "Stock épuisé"])
        self.stock_filter.currentTextChanged.connect(self.filter_articles)
        search_layout.addWidget(QLabel("Stock:"))
        search_layout.addWidget(self.stock_filter)
        
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        # Tableau des articles
        self.articles_table = QTableWidget()
        self.articles_table.setColumnCount(8)
        self.articles_table.setHorizontalHeaderLabels([
            "ID", "Désignation", "Catégorie", "Quantité", "Unité", 
            "Prix unitaire", "Seuil minimum", "Statut"
        ])
        
        # Redimensionnement automatique des colonnes
        header = self.articles_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.articles_table)
        
        # Boutons d'action
        buttons_layout = QHBoxLayout()
        
        add_btn = QPushButton("Ajouter")
        add_btn.clicked.connect(self.add_article)
        buttons_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Modifier")
        edit_btn.clicked.connect(self.edit_article)
        buttons_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Supprimer")
        delete_btn.clicked.connect(self.delete_article)
        buttons_layout.addWidget(delete_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        return widget
    
    def create_entrees_tab(self):
        """Crée l'onglet des entrées"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Filtres de date
        date_layout = QHBoxLayout()
        
        self.date_from_entry = QDateEdit()
        self.date_from_entry.setDate(QDate.currentDate().addDays(-30))
        self.date_from_entry.setCalendarPopup(True)
        date_layout.addWidget(QLabel("Du:"))
        date_layout.addWidget(self.date_from_entry)
        
        self.date_to_entry = QDateEdit()
        self.date_to_entry.setDate(QDate.currentDate())
        self.date_to_entry.setCalendarPopup(True)
        date_layout.addWidget(QLabel("Au:"))
        date_layout.addWidget(self.date_to_entry)
        
        filter_entries_btn = QPushButton("Filtrer")
        filter_entries_btn.clicked.connect(self.load_entrees)
        date_layout.addWidget(filter_entries_btn)
        
        date_layout.addStretch()
        layout.addLayout(date_layout)
        
        # Tableau des entrées
        self.entrees_table = QTableWidget()
        self.entrees_table.setColumnCount(7)
        self.entrees_table.setHorizontalHeaderLabels([
            "ID", "Article", "Quantité", "Date", "Fournisseur", "Prix total", "Commentaire"
        ])
        
        header = self.entrees_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout.addWidget(self.entrees_table)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        add_entry_btn = QPushButton("Nouvelle Entrée")
        add_entry_btn.clicked.connect(self.add_entree)
        buttons_layout.addWidget(add_entry_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        return widget
    
    def create_sorties_tab(self):
        """Crée l'onglet des sorties"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Filtres de date
        date_layout = QHBoxLayout()
        
        self.date_from_sortie = QDateEdit()
        self.date_from_sortie.setDate(QDate.currentDate().addDays(-30))
        self.date_from_sortie.setCalendarPopup(True)
        date_layout.addWidget(QLabel("Du:"))
        date_layout.addWidget(self.date_from_sortie)
        
        self.date_to_sortie = QDateEdit()
        self.date_to_sortie.setDate(QDate.currentDate())
        self.date_to_sortie.setCalendarPopup(True)
        date_layout.addWidget(QLabel("Au:"))
        date_layout.addWidget(self.date_to_sortie)
        
        filter_sorties_btn = QPushButton("Filtrer")
        filter_sorties_btn.clicked.connect(self.load_sorties)
        date_layout.addWidget(filter_sorties_btn)
        
        date_layout.addStretch()
        layout.addLayout(date_layout)
        
        # Tableau des sorties
        self.sorties_table = QTableWidget()
        self.sorties_table.setColumnCount(7)
        self.sorties_table.setHorizontalHeaderLabels([
            "ID", "Article", "Quantité", "Date", "Motif", "Utilisateur", "Commentaire"
        ])
        
        header = self.sorties_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout.addWidget(self.sorties_table)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        add_sortie_btn = QPushButton("Nouvelle Sortie")
        add_sortie_btn.clicked.connect(self.add_sortie)
        buttons_layout.addWidget(add_sortie_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        return widget
    
    def create_dashboard_tab(self):
        """Crée le tableau de bord"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Statistiques générales
        stats_group = QGroupBox("Statistiques générales")
        stats_layout = QGridLayout(stats_group)
        
        self.total_articles_label = QLabel("0")
        self.total_articles_label.setStyleSheet("font-size: 24px; font-weight: bold; color: blue;")
        stats_layout.addWidget(QLabel("Total articles:"), 0, 0)
        stats_layout.addWidget(self.total_articles_label, 0, 1)
        
        self.low_stock_label = QLabel("0")
        self.low_stock_label.setStyleSheet("font-size: 24px; font-weight: bold; color: red;")
        stats_layout.addWidget(QLabel("Stocks bas:"), 0, 2)
        stats_layout.addWidget(self.low_stock_label, 0, 3)
        
        self.total_value_label = QLabel("0.00 FCFA")
        self.total_value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: green;")
        stats_layout.addWidget(QLabel("Valeur totale:"), 1, 0)
        stats_layout.addWidget(self.total_value_label, 1, 1)
        
        self.total_ventes_label = QLabel("0.00 FCFA")
        self.total_ventes_label.setStyleSheet("font-size: 24px; font-weight: bold; color: orange;")
        stats_layout.addWidget(QLabel("Ventes du jour:"), 2, 0)
        stats_layout.addWidget(self.total_ventes_label, 2, 1)
        
        # Total des ventes du jour
        total_ventes = self.get_total_ventes_du_jour()
        self.total_ventes_label.setText(f"{total_ventes:.2f} FCFA")
        
        self.total_ventes_label = QLabel("0.00 FCFA")
        self.total_ventes_label.setStyleSheet("font-size: 24px; font-weight: bold; color: orange;")
        stats_layout.addWidget(QLabel("Ventes du jour:"), 2, 0)
        stats_layout.addWidget(self.total_ventes_label, 2, 1)
        
        layout.addWidget(stats_group)
        
        # Alertes stocks bas
        alerts_group = QGroupBox("Alertes - Stocks bas")
        alerts_layout = QVBoxLayout(alerts_group)
        
        self.alerts_list = QListWidget()
        self.alerts_list.setMaximumHeight(150)
        alerts_layout.addWidget(self.alerts_list)
        
        layout.addWidget(alerts_group)
        
        # Mouvements récents
        recent_group = QGroupBox("Mouvements récents")
        recent_layout = QVBoxLayout(recent_group)
        
        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(4)
        self.recent_table.setHorizontalHeaderLabels(["Date", "Article", "Type", "Quantité"])
        self.recent_table.setMaximumHeight(200)
        
        header = self.recent_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        recent_layout.addWidget(self.recent_table)
        layout.addWidget(recent_group)
        
        layout.addStretch()
        
        return widget
    
    def load_data(self):
        """Charge toutes les données"""
        self.load_articles()
        self.load_entrees()
        self.load_sorties()
        self.load_dashboard()
        self.load_categories()
    
    def load_categories(self):
        """Charge les catégories pour les filtres"""
        query = "SELECT DISTINCT categorie FROM articles ORDER BY categorie"
        categories = self.db_manager.execute_query(query)
        
        self.category_filter.clear()
        self.category_filter.addItem("Toutes les catégories")
        
        for category in categories:
            self.category_filter.addItem(category[0])
    
    def load_articles(self):
        """Charge les articles dans le tableau"""
        query = """
            SELECT id, designation, categorie, quantite, unite, prix_unitaire, seuil_minimum
            FROM articles
            ORDER BY designation
        """
        articles = self.db_manager.execute_query(query)
        
        self.articles_table.setRowCount(len(articles))
        
        for row, article in enumerate(articles):
            for col, value in enumerate(article):
                if col == 5:  # Prix unitaire
                    item = QTableWidgetItem(f"{value:.2f} FCFA")
                else:
                    item = QTableWidgetItem(str(value))
                
                self.articles_table.setItem(row, col, item)
            
            # Statut du stock
            quantite = article[3]
            seuil = article[6]
            
            if quantite == 0:
                status = "Épuisé"
                color = QColor(255, 0, 0)  # Rouge
            elif quantite <= seuil:
                status = "Stock bas"
                color = QColor(255, 165, 0)  # Orange
            else:
                status = "Normal"
                color = QColor(0, 128, 0)  # Vert
            
            status_item = QTableWidgetItem(status)
            status_item.setBackground(color)
            status_item.setForeground(QColor(255, 255, 255))  # Texte blanc
            self.articles_table.setItem(row, 7, status_item)
    
    def filter_articles(self):
        """Filtre les articles selon les critères"""
        search_text = self.search_edit.text().lower()
        category_filter = self.category_filter.currentText()
        stock_filter = self.stock_filter.currentText()
        
        for row in range(self.articles_table.rowCount()):
            show_row = True
            
            # Filtre par texte de recherche
            if search_text:
                designation = self.articles_table.item(row, 1).text().lower()
                if search_text not in designation:
                    show_row = False
            
            # Filtre par catégorie
            if category_filter != "Toutes les catégories":
                category = self.articles_table.item(row, 2).text()
                if category != category_filter:
                    show_row = False
            
            # Filtre par stock
            if stock_filter != "Tous les stocks":
                status = self.articles_table.item(row, 7).text()
                if stock_filter == "Stock normal" and status != "Normal":
                    show_row = False
                elif stock_filter == "Stock bas" and status != "Stock bas":
                    show_row = False
                elif stock_filter == "Stock épuisé" and status != "Épuisé":
                    show_row = False
            
            self.articles_table.setRowHidden(row, not show_row)
    
    def load_entrees(self):
        """Charge les entrées dans le tableau"""
        date_from = self.date_from_entry.date().toPyDate()
        date_to = self.date_to_entry.date().toPyDate()
        
        query = """
            SELECT e.id, a.designation, e.quantite, e.date_entree, 
                   e.fournisseur, e.prix_total, e.commentaire
            FROM entrees e
            JOIN articles a ON e.article_id = a.id
            WHERE e.date_entree BETWEEN ? AND ?
            ORDER BY e.date_entree DESC
        """
        entrees = self.db_manager.execute_query(query, (date_from, date_to))
        
        self.entrees_table.setRowCount(len(entrees))
        
        for row, entree in enumerate(entrees):
            for col, value in enumerate(entree):
                if col == 5 and value:  # Prix total
                    item = QTableWidgetItem(f"{value:.2f} FCFA")
                else:
                    item = QTableWidgetItem(str(value) if value else "")
                self.entrees_table.setItem(row, col, item)
    
    def load_sorties(self):
        """Charge les sorties dans le tableau"""
        date_from = self.date_from_sortie.date().toPyDate()
        date_to = self.date_to_sortie.date().toPyDate()
        
        query = """
            SELECT s.id, a.designation, s.quantite, s.date_sortie, 
                   s.motif, s.utilisateur, s.commentaire
            FROM sorties s
            JOIN articles a ON s.article_id = a.id
            WHERE s.date_sortie BETWEEN ? AND ?
            ORDER BY s.date_sortie DESC
        """
        sorties = self.db_manager.execute_query(query, (date_from, date_to))
        
        self.sorties_table.setRowCount(len(sorties))
        
        for row, sortie in enumerate(sorties):
            for col, value in enumerate(sortie):
                item = QTableWidgetItem(str(value) if value else "")
                self.sorties_table.setItem(row, col, item)
    
    def get_total_ventes_du_jour(self):
        """Calcule la somme totale des produits vendus aujourd'hui"""
        today = date.today().isoformat()
        query = """
            SELECT SUM(s.quantite * a.prix_unitaire)
            FROM sorties s
            JOIN articles a ON s.article_id = a.id
            WHERE s.date_sortie = ?
        """
        total = self.db_manager.execute_query(query, (today,))[0][0]
        return total or 0
    
    def load_dashboard(self):
        """Charge les données du tableau de bord"""
        # Statistiques générales
        total_articles = self.db_manager.execute_query("SELECT COUNT(*) FROM articles")[0][0]
        self.total_articles_label.setText(str(total_articles))
        
        # Articles en stock bas
        low_stock_query = "SELECT COUNT(*) FROM articles WHERE quantite <= seuil_minimum AND quantite > 0"
        low_stock = self.db_manager.execute_query(low_stock_query)[0][0]
        self.low_stock_label.setText(str(low_stock))
        
        # Valeur totale du stock
        value_query = "SELECT SUM(quantite * prix_unitaire) FROM articles"
        total_value = self.db_manager.execute_query(value_query)[0][0] or 0
        self.total_value_label.setText(f"{total_value:.2f} FCFA")
        
        # Total des ventes du jour
        total_ventes = self.get_total_ventes_du_jour()
        self.total_ventes_label.setText(f"{total_ventes:.2f} FCFA")
        
        # Alertes stocks bas
        self.load_alerts()
        
        # Mouvements récents
        self.load_recent_movements()
    
    def load_alerts(self):
        """Charge les alertes de stocks bas"""
        query = """
            SELECT designation, quantite, seuil_minimum, unite
            FROM articles 
            WHERE quantite <= seuil_minimum 
            ORDER BY quantite ASC
        """
        alerts = self.db_manager.execute_query(query)
        
        self.alerts_list.clear()
        
        for alert in alerts:
            designation, quantite, seuil, unite = alert
            if quantite == 0:
                message = f"⚠️ {designation} - STOCK ÉPUISÉ"
            else:
                message = f"⚠️ {designation} - {quantite} {unite} (seuil: {seuil})"
            self.alerts_list.addItem(message)
        
        if not alerts:
            self.alerts_list.addItem("✅ Aucune alerte - Tous les stocks sont corrects")
    
    def load_recent_movements(self):
        """Charge les mouvements récents"""
        query = """
            SELECT date_entree as date, 'Entrée' as type, a.designation, e.quantite
            FROM entrees e
            JOIN articles a ON e.article_id = a.id
            UNION ALL
            SELECT date_sortie as date, 'Sortie' as type, a.designation, s.quantite
            FROM sorties s
            JOIN articles a ON s.article_id = a.id
            ORDER BY date DESC
            LIMIT 10
        """
        movements = self.db_manager.execute_query(query)
        
        self.recent_table.setRowCount(len(movements))
        
        for row, movement in enumerate(movements):
            date, type_mvt, designation, quantite = movement
            
            self.recent_table.setItem(row, 0, QTableWidgetItem(str(date)))
            self.recent_table.setItem(row, 1, QTableWidgetItem(designation))
            
            type_item = QTableWidgetItem(type_mvt)
            if type_mvt == "Entrée":
                type_item.setBackground(QColor(0, 255, 0, 50))  # Vert clair
            else:
                type_item.setBackground(QColor(255, 0, 0, 50))  # Rouge clair
            self.recent_table.setItem(row, 2, type_item)
            
            quantity_text = f"+{quantite}" if type_mvt == "Entrée" else f"-{quantite}"
            self.recent_table.setItem(row, 3, QTableWidgetItem(quantity_text))
    
    def check_low_stock(self):
        """Vérifie les stocks bas périodiquement"""
        query = "SELECT COUNT(*) FROM articles WHERE quantite <= seuil_minimum AND quantite > 0"
        low_stock_count = self.db_manager.execute_query(query)[0][0]
        
        if low_stock_count > 0:
            self.status_bar.showMessage(f"⚠️ {low_stock_count} article(s) en stock bas")
        else:
            self.status_bar.showMessage("✅ Tous les stocks sont corrects")
    
    def add_article(self):
        """Ajoute un nouvel article"""
        dialog = ArticleDialog(self.db_manager)
        
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            
            if not data['designation']:
                QMessageBox.warning(self, "Erreur", "La désignation est obligatoire.")
                return
            
            query = """
                INSERT INTO articles (designation, categorie, quantite, unite, prix_unitaire, seuil_minimum)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (data['designation'], data['categorie'], data['quantite'],
                     data['unite'], data['prix_unitaire'], data['seuil_minimum'])
            
            try:
                self.db_manager.execute_query(query, params)
                QMessageBox.information(self, "Succès", "Article ajouté avec succès.")
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'ajout: {str(e)}")
    
    def edit_article(self):
        """Modifie l'article sélectionné"""
        current_row = self.articles_table.currentRow()
        
        if current_row < 0:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un article à modifier.")
            return
        
        # Récupérer les données de l'article
        article_id = int(self.articles_table.item(current_row, 0).text())
        query = "SELECT * FROM articles WHERE id = ?"
        article_data = self.db_manager.execute_query(query, (article_id,))[0]
        
        dialog = ArticleDialog(self.db_manager, article_data)
        
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            
            if not data['designation']:
                QMessageBox.warning(self, "Erreur", "La désignation est obligatoire.")
                return
            
            query = """
                UPDATE articles 
                SET designation=?, categorie=?, quantite=?, unite=?, prix_unitaire=?, seuil_minimum=?
                WHERE id=?
            """
            params = (data['designation'], data['categorie'], data['quantite'],
                     data['unite'], data['prix_unitaire'], data['seuil_minimum'], article_id)
            
            try:
                self.db_manager.execute_query(query, params)
                QMessageBox.information(self, "Succès", "Article modifié avec succès.")
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de la modification: {str(e)}")
    
    def delete_article(self):
        """Supprime l'article sélectionné"""
        current_row = self.articles_table.currentRow()
        
        if current_row < 0:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un article à supprimer.")
            return
        
        article_id = int(self.articles_table.item(current_row, 0).text())
        designation = self.articles_table.item(current_row, 1).text()
        
        # Confirmation
        reply = QMessageBox.question(
            self, "Confirmation",
            f"Êtes-vous sûr de vouloir supprimer l'article '{designation}' ?\n"
            "Cette action supprimera aussi tous les mouvements associés.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Supprimer les mouvements associés
                self.db_manager.execute_query("DELETE FROM entrees WHERE article_id = ?", (article_id,))
                self.db_manager.execute_query("DELETE FROM sorties WHERE article_id = ?", (article_id,))
                
                # Supprimer l'article
                self.db_manager.execute_query("DELETE FROM articles WHERE id = ?", (article_id,))
                
                QMessageBox.information(self, "Succès", "Article supprimé avec succès.")
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de la suppression: {str(e)}")
    
    def add_entree(self):
        """Ajoute une nouvelle entrée"""
        # Récupérer la liste des articles
        articles = self.db_manager.execute_query("SELECT * FROM articles ORDER BY designation")
        
        if not articles:
            QMessageBox.warning(self, "Erreur", "Aucun article disponible. Créez d'abord des articles.")
            return
        
        dialog = MouvementDialog(self.db_manager, 'entree', articles)
        
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            
            query = """
                INSERT INTO entrees (article_id, quantite, date_entree, fournisseur, prix_total, commentaire)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (data['article_id'], data['quantite'], data['date'],
                     data['fournisseur'], data['prix_total'], data['commentaire'])
            
            try:
                # Insérer l'entrée
                self.db_manager.execute_query(query, params)
                
                # Mettre à jour le stock
                update_query = "UPDATE articles SET quantite = quantite + ? WHERE id = ?"
                self.db_manager.execute_query(update_query, (data['quantite'], data['article_id']))
                
                QMessageBox.information(self, "Succès", "Entrée ajoutée avec succès.")
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'ajout: {str(e)}")
    
    def add_sortie(self):
        """Ajoute une nouvelle sortie"""
        # Récupérer la liste des articles avec stock > 0
        articles = self.db_manager.execute_query(
            "SELECT * FROM articles WHERE quantite > 0 ORDER BY designation"
        )
        
        if not articles:
            QMessageBox.warning(self, "Erreur", "Aucun article en stock disponible.")
            return
        
        dialog = MouvementDialog(self.db_manager, 'sortie', articles)
        
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            
            # Vérifier le stock disponible
            stock_query = "SELECT quantite FROM articles WHERE id = ?"
            stock_actuel = self.db_manager.execute_query(stock_query, (data['article_id'],))[0][0]
            
            if data['quantite'] > stock_actuel:
                QMessageBox.warning(
                    self, "Erreur", 
                    f"Stock insuffisant. Stock disponible: {stock_actuel}"
                )
                return
            
            query = """
                INSERT INTO sorties (article_id, quantite, date_sortie, motif, utilisateur, commentaire)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (data['article_id'], data['quantite'], data['date'],
                     data['motif'], data['utilisateur'], data['commentaire'])
            
            try:
                # Insérer la sortie
                self.db_manager.execute_query(query, params)
                
                # Mettre à jour le stock
                update_query = "UPDATE articles SET quantite = quantite - ? WHERE id = ?"
                self.db_manager.execute_query(update_query, (data['quantite'], data['article_id']))
                
                QMessageBox.information(self, "Succès", "Sortie ajoutée avec succès.")
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'ajout: {str(e)}")
    
    def generate_report(self):
        """Génère un rapport PDF"""
        try:
            # Demander le type de rapport
            from PyQt5.QtWidgets import QInputDialog
            
            items = ["Inventaire complet", "Mouvements (Entrées/Sorties)", "Stocks bas"]
            item, ok = QInputDialog.getItem(
                self, "Générer un rapport", "Type de rapport:", items, 0, False
            )
            
            if not ok:
                return
            
            # Demander où sauvegarder
            filename, _ = QFileDialog.getSaveFileName(
                self, "Sauvegarder le rapport", f"rapport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "Fichiers PDF (*.pdf)"
            )
            
            if not filename:
                return
            
            # Générer le rapport selon le type
            if item == "Inventaire complet":
                self.generate_inventory_report(filename)
            elif item == "Mouvements (Entrées/Sorties)":
                self.generate_movements_report(filename)
            elif item == "Stocks bas":
                self.generate_low_stock_report(filename)
            
            QMessageBox.information(self, "Succès", f"Rapport généré: {filename}")
            
        except ImportError:
            QMessageBox.warning(
                self, "Erreur", 
                "La génération de rapports PDF nécessite la bibliothèque 'reportlab'.\n"
                "Installez-la avec: pip install reportlab"
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la génération: {str(e)}")
    
    def generate_inventory_report(self, filename):
        """Génère un rapport d'inventaire PDF"""
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Titre
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=1,  # Centré
            spaceAfter=30
        )
        story.append(Paragraph("Rapport d'Inventaire - Gestion de Stocks", title_style))
        story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Données
        query = """
            SELECT designation, categorie, quantite, unite, prix_unitaire, 
                   (quantite * prix_unitaire) as valeur_totale
            FROM articles 
            ORDER BY categorie, designation
        """
        articles = self.db_manager.execute_query(query)
        
        # Tableau
        data = [['Désignation', 'Catégorie', 'Quantité', 'Unité', 'Prix unit.', 'Valeur totale']]
        total_value = 0
        
        for article in articles:
            designation, categorie, quantite, unite, prix_unit, valeur = article
            total_value += valeur or 0
            data.append([
                designation, categorie, str(quantite), unite,
                f"{prix_unit:.2f} FCFA", f"{valeur:.2f} FCFA"
            ])
        
        # Ligne de total
        data.append(['', '', '', '', 'TOTAL:', f"{total_value:.2f} FCFA"])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        doc.build(story)
    
    def generate_movements_report(self, filename):
        """Génère un rapport des mouvements PDF"""
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Titre
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=1,
            spaceAfter=30
        )
        story.append(Paragraph("Rapport des Mouvements - Gestion de Stocks", title_style))
        story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Entrées
        story.append(Paragraph("ENTRÉES", styles['Heading2']))
        
        query_entrees = """
            SELECT e.date_entree, a.designation, e.quantite, e.fournisseur, e.prix_total
            FROM entrees e
            JOIN articles a ON e.article_id = a.id
            ORDER BY e.date_entree DESC
            LIMIT 50
        """
        entrees = self.db_manager.execute_query(query_entrees)
        
        if entrees:
            data_entrees = [['Date', 'Article', 'Quantité', 'Fournisseur', 'Prix']]
            for entree in entrees:
                date, designation, quantite, fournisseur, prix = entree
                data_entrees.append([
                    str(date), designation, str(quantite),
                    fournisseur or '-', f"{prix:.2f} FCFA" if prix else '-'
                ])
            
            table_entrees = Table(data_entrees)
            table_entrees.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.green),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table_entrees)
        else:
            story.append(Paragraph("Aucune entrée enregistrée.", styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Sorties
        story.append(Paragraph("SORTIES", styles['Heading2']))
        
        query_sorties = """
            SELECT s.date_sortie, a.designation, s.quantite, s.motif, s.utilisateur
            FROM sorties s
            JOIN articles a ON s.article_id = a.id
            ORDER BY s.date_sortie DESC
            LIMIT 50
        """
        sorties = self.db_manager.execute_query(query_sorties)
        
        if sorties:
            data_sorties = [['Date', 'Article', 'Quantité', 'Motif', 'Utilisateur']]
            for sortie in sorties:
                date, designation, quantite, motif, utilisateur = sortie
                data_sorties.append([
                    str(date), designation, str(quantite),
                    motif or '-', utilisateur or '-'
                ])
            
            table_sorties = Table(data_sorties)
            table_sorties.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.mistyrose),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table_sorties)
        else:
            story.append(Paragraph("Aucune sortie enregistrée.", styles['Normal']))
        
        doc.build(story)
    
    def generate_low_stock_report(self, filename):
        """Génère un rapport des stocks bas PDF"""
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Titre
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=1,
            spaceAfter=30
        )
        story.append(Paragraph("Rapport des Stocks Bas - Gestion de Stocks", title_style))
        story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Données
        query = """
            SELECT designation, categorie, quantite, unite, seuil_minimum
            FROM articles 
            WHERE quantite <= seuil_minimum
            ORDER BY quantite ASC, designation
        """
        articles = self.db_manager.execute_query(query)
        
        if articles:
            data = [['Désignation', 'Catégorie', 'Stock actuel', 'Unité', 'Seuil minimum', 'Statut']]
            
            for article in articles:
                designation, categorie, quantite, unite, seuil = article
                status = "ÉPUISÉ" if quantite == 0 else "STOCK BAS"
                data.append([
                    designation, categorie, str(quantite), unite, str(seuil), status
                ])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.mistyrose),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
        else:
            story.append(Paragraph("✅ Aucun stock bas détecté !", styles['Normal']))
        
        doc.build(story)

def main():
    app = QApplication(sys.argv)
    
    # Style de l'application
    app.setStyle('Fusion')
    
    # Palette de couleurs
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
    palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    try:
        window = StockManagementApp()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Erreur lors du lancement de l'application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()