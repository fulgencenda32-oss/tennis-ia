lines = open("entrainement_hebdo.py", encoding="utf-8").readlines()

# Trouver la ligne "with open(FICHIER_MODELE"
for i, line in enumerate(lines):
    if "with open(FICHIER_MODELE" in line and "pickle" in lines[i+1]:
        insert_at = i
        break

nouveau = """if not os.path.exists(FICHIER_MODELE):
    print("   Telechargement modele depuis HuggingFace...")
    try:
        from huggingface_hub import hf_hub_download
        import shutil
        chemin = hf_hub_download(
            repo_id="fulgence10/tennis-ia",
            filename="data/modeles_tennis_v2.pkl",
            repo_type="space",
            local_dir=os.path.join(os.path.dirname(FICHIER_MODELE), "tmp_hf")
        )
        shutil.copy(chemin, FICHIER_MODELE)
        print("   OK modele telecharge")
    except Exception as e:
        print(f"   ERREUR telechargement : {e}")
        print("   Copiez manuellement modeles_tennis_v2.pkl dans data/")
        exit(1)
"""

lines.insert(insert_at, nouveau)
open("entrainement_hebdo.py", "w", encoding="utf-8").writelines(lines)
print("OK" if "hf_hub_download" in open("entrainement_hebdo.py", encoding="utf-8").read() else "ECHEC")
