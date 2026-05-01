from argparse import ArgumentParser
from pathlib import Path

from docx import Document

def limpar_headers(origem, destino=None):
    origem_path = Path(origem)
    destino_path = Path(destino) if destino else origem_path.with_name(f"{origem_path.stem}_limpo{origem_path.suffix}")

    doc = Document(origem_path)

    for section in doc.sections:
        header = section.header
        for paragraph in header.paragraphs:
            paragraph.text = ""

    doc.save(destino_path)
    return destino_path

def main():
    parser = ArgumentParser(description="Remove os headers de um ficheiro Word.")
    parser.add_argument("origem", help="Caminho para o ficheiro DOCX de origem.")
    parser.add_argument("destino", nargs="?", help="Caminho para o ficheiro DOCX limpo.")
    args = parser.parse_args()

    destino = limpar_headers(args.origem, args.destino)
    print(destino)

if __name__ == "__main__":
    main()