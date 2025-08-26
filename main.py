import os
import glob
import re
import ast

# Encontra a pasta dentro de input_BI que termina com '.SemanticModel'
input_semantic_dirs = glob.glob("input_BI/*.SemanticModel")
if not input_semantic_dirs:
    raise FileNotFoundError(f"Não foi encontrada uma pasta terminando com '.SemanticModel' em input.")
output_semantic_dirs = glob.glob("output_BI/*.SemanticModel")
if not output_semantic_dirs:
    raise FileNotFoundError(f"Não foi encontrada uma pasta terminando com '.SemanticModel' em output.")

print("Criando modelo...")

# Verificando a versão do Power BI
def get_default_powerbi_version(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"defaultPowerBIDataSourceVersion:\s*(\S+)", content)
    return match.group(1) if match else None

# Extrai grupos de consulta
def get_query_groups(content):
    return re.findall(r"queryGroup\s+'([^']+)'", content)

# Calcula a ordem do grupo de consultas criado
def get_query_order(content):
    match = re.search(r'annotation PBI_QueryOrder = (\[.*?\])', content, re.DOTALL)
    return ast.literal_eval(match.group(1)) if match else []

# Extrai referências de tabelas
def get_ref_tables(content):
    return re.findall(r"^(ref table .+)$", content, re.MULTILINE)

# Extrai referência de cultura
def get_ref_culture_info(content):
    match = re.search(r"^(ref cultureInfo .+)$", content, re.MULTILINE)
    return match.group(1) if match else None

# Caminhos dos arquivos
input_model_path = input_semantic_dirs[0] + "/definition/model.tmdl"
output_model_path = output_semantic_dirs[0] + "/definition/model.tmdl"

# Verifica versão do Power BI
input_version = get_default_powerbi_version(input_model_path)
output_version = get_default_powerbi_version(output_model_path)
if input_version != output_version:
    raise ValueError(f"Versões diferentes: input_BI={input_version}, output_BI={output_version}")

# Lê conteúdos
with open(input_model_path, "r", encoding="utf-8") as f:
    input_content = f.read()
with open(output_model_path, "r", encoding="utf-8") as f:
    output_content = f.read()

# Pergunta se quer criar grupo
create_group = input("Deseja criar um novo queryGroup? (s/N): ").strip().lower()
if create_group not in ("s", "n"):
    create_group = "n"
new_group_block = ""
if create_group == "s":
    group_name = input("Informe o nome do grupo: ").strip()
    existing_groups = get_query_groups(output_content)
    N = len(existing_groups)
    new_group_block = f"\nqueryGroup '{group_name}'\n\n\tannotation PBI_QueryGroupOrder = {N}\n"

    # Encontra o final do bloco model Model
    model_block_match = re.search(
        r"(model Model[\s\S]*?returnErrorValuesAsNull\s*\n)", output_content
    )
    if model_block_match:
        insert_pos = model_block_match.end()
        output_content = (
            output_content[:insert_pos] +
            new_group_block +
            output_content[insert_pos:]
        )
    else:
        # Se não encontrar, insere no início
        output_content = new_group_block + output_content

# Atualiza annotation PBI_QueryOrder
input_query_order = get_query_order(input_content)
output_query_order = get_query_order(output_content)
# Junta as listas, mantendo a ordem e sem duplicatas
combined_query_order = output_query_order + [item for item in input_query_order if item not in output_query_order]
output_content = re.sub(
    r'(annotation PBI_QueryOrder = )\[.*?\]',
    f'\\1{str(combined_query_order)}',
    output_content,
    flags=re.DOTALL
)

# Anexa todas as linhas 'ref table' do input ao output (antes do ref cultureInfo)
output_tables = get_ref_tables(output_content)
output_table_names = set(re.findall(r"ref table '?([^\n']+)'?", "\n".join(output_tables)))
input_tables = get_ref_tables(input_content)
renamed_input_tables = []
for ref in input_tables:
    match = re.match(r"ref table '?([^\n']+)'?", ref)
    if match:
        name = match.group(1)
        if name in output_table_names:
            renamed_input_tables.append(f"ref table '{name} (1)'")
        else:
            renamed_input_tables.append(ref)
    else:
        renamed_input_tables.append(ref)
all_tables = output_tables + renamed_input_tables

# Adiciona os parágrafos e as referências
ref_culture_info = get_ref_culture_info(output_content)

# Remove todas as linhas ref table e ref cultureInfo do output
output_content = re.sub(r'(ref table .+\n)+', '', output_content)
output_content = re.sub(r'(ref cultureInfo .+)$', '', output_content, flags=re.MULTILINE)

# Adiciona os parágrafos e as referências
output_content = (
    output_content.rstrip() +
    "\n\n" +
    '\n'.join(all_tables) +
    "\n\n" +
    (ref_culture_info if ref_culture_info else '') +
    '\n'
)

# Salva alterações
with open(output_model_path, "w", encoding="utf-8") as f:
    f.write(output_content)

print("✅ Modelos criados com sucesso!")

print("Verificando database...")

input_db_path = os.path.join(input_semantic_dirs[0], "definition", "database.tmdl")
output_db_path = os.path.join(output_semantic_dirs[0], "definition", "database.tmdl")

def get_compatibility_level(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"compatibilityLevel:\s*(\d+)", content)
    return int(match.group(1)) if match else None

input_level = get_compatibility_level(input_db_path)
output_level = get_compatibility_level(output_db_path)

if input_level != output_level:
    print(f"Os valores de compatibilityLevel são diferentes: input_BI={input_level}, output_BI={output_level}")

print("✅ Database verificada com sucesso!")

print("Criando expressões...")

input_path = os.path.join(input_semantic_dirs[0], "definition", "expressions.tmdl")
output_path = os.path.join(output_semantic_dirs[0], "definition", "expressions.tmdl")

if not (os.path.exists(input_path) and os.path.exists(output_path)):
    print("Arquivo expressions.tmdl não encontrado. Pulando para relações...")
    # Pula para a criação das relações
    goto_relations = True
else:
    goto_relations = False

if not goto_relations:
    # Lê os arquivos
    with open(input_path, "r", encoding="utf-8") as f:
        input_content = f.read()
        # Adiciona a linha após cada lineageTag
    if create_group == "s":
        def insert_querygroup_expr(match):
            return f"{match.group(0)}\n\tqueryGroup: {group_name}"
        input_content = re.sub(
            r"(lineageTag:[^\n]*)",
            insert_querygroup_expr,
            input_content
        )
    with open(output_path, "r", encoding="utf-8") as f:
        output_content = f.read()

    # Une os conteúdos
    merged_content = input_content + "\n" + output_content

    # Substitui o arquivo da pasta output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(merged_content)

print("✅ Expressões criadas com sucesso!")

print("Criando relações... ")

# Obtém caminhos dos arquivos de relações
input_rel_path = os.path.join(input_semantic_dirs[0], "definition", "relationships.tmdl")
output_rel_path = os.path.join(output_semantic_dirs[0], "definition", "relationships.tmdl")

# Lê as relações de input
with open(input_rel_path, "r", encoding="utf-8") as f:
    input_rel_content = f.read()

# Lê as relações de output
with open(output_rel_path, "r", encoding="utf-8") as f:
    output_rel_content = f.read()

def rename_table_in_relations(rel_content, duplicated_names):
    def replacer(match):
        table = match.group(1).strip("' ").strip()  # Remove aspas e espaços extras
        column = match.group(2).strip("' ").strip()
        # Renomeia se for duplicada
        if table in duplicated_names:
            new_table = f"{table} (1)"
        else:
            new_table = table
        # Aspas se houver espaço ou se já tinha aspas
        if " " in new_table or match.group(1).startswith("'"):
            new_table = f"'{new_table}'"
        return f"{new_table}.{column}"
    # Substitui todas as ocorrências
    return re.sub(r"([']?[A-Za-z0-9 _]+[']?)\.([A-Za-z0-9 _']+)", replacer, rel_content)

# Antes de combinar, renomeie as relações do input
duplicated_names = output_table_names.intersection(
    set(re.findall(r"ref table '?([^\n']+)'?", "\n".join(input_tables)))
)
input_rel_content = rename_table_in_relations(input_rel_content, duplicated_names)

combined_rel_content = output_rel_content.strip() + "\n\n" + input_rel_content.strip() + "\n"

# Salva o conteúdo combinado de volta no arquivo de output
with open(output_rel_path, "w", encoding="utf-8") as f:
    f.write(combined_rel_content)

print("✅ Relações criadas com sucesso!")

print("Copiando tabelas...")

# Obtém caminhos dos arquivos de tabelas
input_tables_path = os.path.join(input_semantic_dirs[0], "definition", "tables")
output_tables_path = os.path.join(output_semantic_dirs[0], "definition", "tables")

def rename_table_in_tmdl(content, old_name, new_name):
    # Renomeia no bloco table
    content = re.sub(
        rf"(table\s+)('{re.escape(old_name)}'|{re.escape(old_name)})",
        lambda m: f"{m.group(1)}'{new_name}'" if (" " in new_name or m.group(2).startswith("'")) else f"{m.group(1)}{new_name}",
        content
    )
    # Renomeia no bloco partition (com espaços/tabs antes e depois)
    content = re.sub(
        rf"(^[ \t]*partition[ \t]+)('{re.escape(old_name)}'|{re.escape(old_name)})",
        lambda m: f"{m.group(1)}'{new_name}'" if (" " in new_name or m.group(2).startswith("'")) else f"{m.group(1)}{new_name}",
        content,
        flags=re.MULTILINE
    )
    return content

# Copia todas as tabelas do input para o output
output_table_files = set(os.listdir(output_tables_path))
for input_file in os.listdir(input_tables_path):
    table_name = input_file.replace(".tmdl", "")
    new_table_name = table_name
    if input_file in output_table_files:
        new_table_name = f"{table_name} (1)"
        new_input_file = f"{new_table_name}.tmdl"
    else:
        new_input_file = input_file
    input_file_path = os.path.join(input_tables_path, input_file)
    output_file_path = os.path.join(output_tables_path, new_input_file)
    if os.path.isfile(input_file_path):
        with open(input_file_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Renomeia o nome da tabela dentro do arquivo (table e partition)
        if new_table_name != table_name:
            content = rename_table_in_tmdl(content, table_name, new_table_name)
        else:
            content = rename_table_in_tmdl(content, table_name, table_name)
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(content)
    # Adiciona 'queryGroup: group_name' entre mode e source nas tabelas do output que vieram do input
    if create_group == "s":
        if os.path.isfile(output_file_path):
            with open(output_file_path, "r", encoding="utf-8") as f:
                table_content = f.read()
            # Adiciona a linha entre 'mode:' e 'source =' em todas as partições, sem linha extra
            def insert_querygroup(match):
                return f"{match.group(1)}\t\tqueryGroup: {group_name}\n{match.group(2)}"
            table_content = re.sub(
                r"(mode:[^\n]*\n)(\s*source\s*=)",
                insert_querygroup,
                table_content
            )
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(table_content)

print("✅ Tabelas criadas com sucesso!")

