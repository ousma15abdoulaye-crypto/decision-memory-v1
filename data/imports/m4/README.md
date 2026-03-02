# data/imports/m4/ — Fichiers d'import Wave 2

## Règle absolue

Les fichiers xlsx sont exclus de Git (`.gitignore`).
Ils sont déposés manuellement avant chaque import.
Un nom de fichier incorrect déclenche `STOP-PB-J` dans l'ETL.
Ce README est la source de vérité documentaire sur les noms attendus.

---

## Fichier wave 2

| Paramètre | Valeur |
|-----------|--------|
| Nom exact | `SUPPLIER DATA Mali FINAL.xlsx` |
| Espaces | **1 espace** entre chaque mot · pas de double espace |
| Format | `.xlsx` uniquement |
| Chemin complet | `data/imports/m4/SUPPLIER DATA Mali FINAL.xlsx` |

---

## Alignement obligatoire avec le script

Le nom exact documenté ici doit être **strictement identique**
au nom attendu dans `scripts/etl_vendors_wave2.py`
avant le premier dry-run.

Aucun écart toléré :
- pas de double espace
- pas de variante invisible
- pas de nom "presque identique"

README = vérité documentaire
Script = vérité exécutable
Les deux doivent correspondre exactement.

---

## Vérification avant import

```bash
# Vérifier présence du fichier exact
ls -la "data/imports/m4/SUPPLIER DATA Mali FINAL.xlsx"

# Rendre les espaces visibles si doute
python3 -c "
import os
for f in os.listdir('data/imports/m4/'):
    print(repr(f))
"
```

---

## Cause fréquente de STOP-PB-J

```text
Nom reçu avec double espace → copié tel quel → STOP
Exemple fautif :
  SUPPLIER DATA  Mali FINAL.xlsx

Nom correct attendu :
  SUPPLIER DATA Mali FINAL.xlsx
```

### Correction

```bash
mv "SUPPLIER DATA  Mali FINAL.xlsx" "SUPPLIER DATA Mali FINAL.xlsx"
```

---

## Procédure de dépôt

```text
1. Recevoir le fichier xlsx de l'équipe terrain
2. Vérifier son nom exact
3. Utiliser repr() si doute sur les espaces
4. Renommer si nécessaire
5. Déposer dans data/imports/m4/
6. Vérifier que le nom correspond exactement au README
7. Vérifier qu'il correspond exactement à la constante du script
8. Lancer ensuite seulement le probe PB0.3
```

---

## Note sécurité

```text
Ces fichiers contiennent des données fournisseurs réelles.
Ne jamais committer dans Git.
Ne jamais partager hors équipe autorisée.
Anonymiser avant tout partage externe (RÈGLE-15).
```
