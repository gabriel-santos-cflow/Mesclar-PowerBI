import os
import stat
import shutil
from pathlib import Path

print("Iniciando restauração do backup...")
# Remove restrições de escrita (somente leitura) de arquivos e pastas
def _make_writable(path: Path):
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
    except Exception:
        pass

# Limpa o conteúdo da pasta de destino
def clear_dir(dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    for entry in dest.iterdir():
        if entry.is_symlink() or entry.is_file():
            _make_writable(entry)
            entry.unlink()
        elif entry.is_dir():
            shutil.rmtree(entry, onerror=lambda f, p, e: (_make_writable(Path(p)), f(p)))

# Substitui o conteúdo da pasta de destino pelo da pasta de origem
def replace_dir_contents(src: Path, dest: Path):
    src = src.resolve()
    dest = dest.resolve()
    if dest == src or dest in src.parents:
        raise ValueError("dest não pode ser a própria src nem estar dentro dela.")
    clear_dir(dest)
    # Agora copiamos tudo de src → dest
    for item in src.iterdir():
        d = dest / item.name
        if item.is_dir():
            shutil.copytree(item, d, symlinks=True)
        else:
            shutil.copy2(item, d)

# Caminhos das pastas
path_output = Path(os.getcwd()) / 'output_BI'
path_backup = Path(os.getcwd()) / 'backup'

# Substitui o conteúdo da pasta output pelo da pasta backup
replace_dir_contents(path_backup, path_output)
print("✅ Backup restaurado com sucesso!")