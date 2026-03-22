content = open("entrainement_hebdo.py", encoding="utf-8").read()

ancien = '''print("\n📦 Chargement modèle existant...")
with open(FICHIER_MODELE, 'rb') as f:
    modeles = pickle.load(f)'''

nouveau = '''print("\n📦 Chargement modèle existant...")
if not os.path.exists(FICHIER_MODELE):
    print("   📥 Téléchargement modèle depuis HuggingFace...")
    try:
        from huggingface_hub import hf_hub_download
        chemin = hf_hub_download(
            repo_id="fulgence10/tennis-ia",
            filename="data/modeles_tennis_v2.pkl",
            repo_type="space",
            local_dir=os.path.dirname(FICHIER_MODELE)
        )
        import shutil
        shutil.copy(chemin, FICHIER_MODELE)
        print("   ✅ Modèle téléchargé")
    except Exception as e:
        print(f"   ❌ Erreur téléchargement : {e}")
        print("   💡 Conseil : copiez manuellement modeles_tennis_v2.pkl dans data/")
        exit(1)
with open(FICHIER_MODELE, 'rb') as f:
    modeles = pickle.load(f)'''

content = content.replace(ancien, nouveau)
open("entrainement_hebdo.py", "w", encoding="utf-8").write(content)
print("OK" if "hf_hub_download" in open("entrainement_hebdo.py", encoding="utf-8").read() else "ECHEC")
