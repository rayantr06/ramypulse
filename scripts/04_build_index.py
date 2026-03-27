"""Point d'entrée CLI pour la construction de l'index FAISS et BM25.

Délègue à scripts.build_index_04.build_index().
"""

from scripts.build_index_04 import build_index

if __name__ == "__main__":
    build_index()
