"""Point d'entrée CLI pour le nettoyage et la normalisation.

Délègue à scripts.process_data_02.process_data().
"""

from scripts.process_data_02 import process_data

if __name__ == "__main__":
    process_data()
