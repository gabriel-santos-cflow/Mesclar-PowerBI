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
    create_group = "N"
new_group_block = ""
if create_group == "s":
    group_name = input("Informe o nome do grupo: ").strip()
    existing_groups = get_query_groups(output_content)
    N = len(existing_groups)
    new_group_block = f"\nqueryGroup '{group_name}'\n\n\tannotation PBI_QueryGroupOrder = {N}\n"

# Adiciona novo grupo após último queryGroup ou após 'model Model'
querygroup_matches = list(re.finditer(r"(queryGroup\s+'.*?'\n\n\tannotation PBI_QueryGroupOrder = \d+\n)", output_content, re.DOTALL))
if querygroup_matches:
    last_querygroup = querygroup_matches[-1]
    insert_pos = last_querygroup.end()
else:
    model_match = re.search(r"(model Model[^\n]*\n)", output_content)
    insert_pos = model_match.end() if model_match else 0
output_content = output_content[:insert_pos] + new_group_block + output_content[insert_pos:]

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
input_tables = get_ref_tables(input_content)
ref_culture_info = get_ref_culture_info(output_content)

# Parágrafos explicativos
before_tables = "\n\n"
after_tables = "\n\n"

# Remove todas as linhas ref table e ref cultureInfo do output
output_content = re.sub(r'(ref table .+\n)+', '', output_content)
output_content = re.sub(r'(ref cultureInfo .+)$', '', output_content, flags=re.MULTILINE)

# Junta as tabelas do output e input, mantendo a ordem
all_tables = output_tables + input_tables

# Adiciona os parágrafos e as referências
output_content = (
    output_content.rstrip() +
    before_tables +
    '\n'.join(all_tables) +
    after_tables +
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

if not input_semantic_dirs or not output_semantic_dirs:
    raise FileNotFoundError("Não foi encontrada uma pasta terminando com '.SemanticModel' em input_BI ou output_BI.")

input_path = os.path.join(input_semantic_dirs[0], "definition", "expressions.tmdl")
output_path = os.path.join(output_semantic_dirs[0], "definition", "expressions.tmdl")

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

# Adiciona o conteúdo do input ao output
combined_rel_content = output_rel_content.strip() + "\n\n" + input_rel_content.strip() + "\n"

# Salva o conteúdo combinado de volta no arquivo de output
with open(output_rel_path, "w", encoding="utf-8") as f:
    f.write(combined_rel_content)

print("✅ Relações criadas com sucesso!")

print("Criando tabelas...")

# Obtém caminhos dos arquivos de tabelas
input_tables_path = os.path.join(input_semantic_dirs[0], "definition", "tables")
output_tables_path = os.path.join(output_semantic_dirs[0], "definition", "tables")

# Copia todas as tabelas do input para o output
for input_file in os.listdir(input_tables_path):
    input_file_path = os.path.join(input_tables_path, input_file)
    output_file_path = os.path.join(output_tables_path, input_file)
    if os.path.isfile(input_file_path):
        with open(input_file_path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
# Adiciona 'queryGroup: group_name' entre mode e source nas tabelas do output que vieram do input
if create_group == "s":
    for input_file in os.listdir(input_tables_path):
        output_file_path = os.path.join(output_tables_path, input_file)
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

