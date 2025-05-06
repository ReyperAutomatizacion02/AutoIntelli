import os

# Carpeta base desde la cual generar el árbol
base_dir = r"C:\Users\User2\Documents\Scripts Python\sys_autointelli"

# Lista de carpetas o archivos que quieres excluir (por nombre)
excluir = ['.git', '__pycache__', '.env', ".venv", "migrations"]

# Archivo donde se guardará el resultado
output_file = os.path.join(base_dir, "arbol.txt")


def generar_arbol(directorio, prefijo=""):
    tree_str = ""
    items = [i for i in os.listdir(directorio) if i not in excluir]
    items.sort()
    for index, item in enumerate(items):
        ruta = os.path.join(directorio, item)
        is_last = index == len(items) - 1
        conector = "└── " if is_last else "├── "
        tree_str += f"{prefijo}{conector}{item}\n"
        if os.path.isdir(ruta) and item not in excluir:
            nuevo_prefijo = prefijo + ("    " if is_last else "│   ")
            tree_str += generar_arbol(ruta, nuevo_prefijo)
    return tree_str


if __name__ == "__main__":
    arbol = f"{os.path.basename(base_dir)}\n"
    arbol += generar_arbol(base_dir)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(arbol)

    print(f"Árbol generado y guardado en: {output_file}")
