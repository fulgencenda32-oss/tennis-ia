import os

def explorer_dossier_tennis(dossier="Tennis_IA"):
    """Affiche le contenu du dossier Tennis_IA"""
    
    if not os.path.exists(dossier):
        print(f"Le dossier {dossier} n'existe pas.")
        return
    
    print(f"
Exploration du dossier {dossier} :
")
    
    # Parcours de tous les éléments du dossier
    for racine, dossiers, fichiers in os.walk(dossier):
        niveau = racine.replace(dossier, '').count(os.sep)
        retrait = ' ' * 4 * niveau
        print(f"{retrait}📁 {os.path.basename(racine)}/")
        
        # Affichage des fichiers
        retrait_fichier = ' ' * 4 * (niveau + 1)
        for fichier in fichiers:
            chemin_fichier = os.path.join(racine, fichier)
            print(f"{retrait_fichier}📄 {fichier}")
            
            # Affichage du contenu pour les fichiers texte
            if fichier.endswith(('.txt', '.csv', '.py', '.pkl')):
                try:
                    with open(chemin_fichier, 'r', encoding='utf-8') as f:
                        lignes = f.readlines()
                        print(f"{retrait_fichier}   Contenu (premières lignes) :")
                        for ligne in lignes[:3]:
                            print(f"{retrait_fichier}   - {ligne.strip()}")
                        if len(lignes) > 3:
                            print(f"{retrait_fichier}   ... (et {len(lignes)-3} lignes supplémentaires)")
                except UnicodeDecodeError:
                    print(f"{retrait_fichier}   Fichier binaire (non affichable)")
                except Exception as e:
                    print(f"{retrait_fichier}   Erreur de lecture : {str(e)}")
                    
        # Séparateur entre dossiers
        if dossiers:
            print()

if __name__ == "__main__":
    explorer_dossier_tennis()