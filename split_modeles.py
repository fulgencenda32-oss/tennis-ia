import pickle, os

def simplifier_round(r): return 3

with open('data/modeles_tennis_v2.pkl', 'rb') as f:
    m = pickle.load(f)

# Extraire les modèles surface dans un fichier séparé
surf = {
    'modeles_surf': m.pop('modeles_surf', {}),
    'acc_surf': m.pop('acc_surf', {})
}

with open('data/modeles_surface.pkl', 'wb') as f:
    pickle.dump(surf, f)

with open('data/modeles_tennis_v2.pkl', 'wb') as f:
    pickle.dump(m, f)

print(f'pkl principal : {os.path.getsize("data/modeles_tennis_v2.pkl")/1024/1024:.1f} MB')
print(f'pkl surface   : {os.path.getsize("data/modeles_surface.pkl")/1024/1024:.1f} MB')
print('Clés principales:', list(m.keys()))