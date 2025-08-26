Este repositório tem como objetivo mesclar relatórios do Power BI utilizando a linguagem TMDL.

# Requisitos

Crie pastas com os seguintes nomes: 'input_BI', 'output_BI' e 'backup'.

É necessário que ambos os relatórios sejam salvos no formato .pbip, que desmembra o relatório e extrai os arquivos TMDL necessários para o script.

Os relatórios devem estar na mesma versão.

Antes de executar o script, salve uma cópia do arquivo de destino na pasta backup.

Obs.: Ainda não foram investigados os impactos da diferença no nível de compatibilidade. Por isso, caso exista alguma divergência, o script irá ignorar e apenas informar durante a execução.

# Como funciona?

O script copia todas as tabelas, medidas e relações de um relatório para outro, utilizando os arquivos TMDL.
Ele extrai seções essenciais desses arquivos do relatório de origem e as insere nos arquivos TMDL de destino, alterando o modelo.

Arquivos TMDL alterados:

expressions.tmdl → funções e expressões;

model.tmdl → criação de grupos, ordem das consultas e tabelas de referência;

relationships.tmdl → definição das relações entre tabelas.

O arquivo database.tmdl é utilizado apenas para verificação do nível de compatibilidade.

Já os arquivos TMDL das tabelas são copiados para a pasta de destino e só têm o conteúdo alterado caso o usuário escolha incluí-los em um grupo.
Se a opção de criar um grupo for escolhida, todas as consultas e expressões do arquivo de origem serão armazenadas dentro desse grupo.

# Notas

Ao finalizar o script, abra o arquivo .pbip de destino para carregar as alterações.

No Power BI, clique no aviso de atualização no canto superior para atualizar os dados das tabelas migradas.

Em seguida, salve o arquivo como .pbix para que ele funcione de forma independente (o .pbip só funciona dentro da pasta, pois depende dos arquivos TMDL).

Caso seja necessário restaurar o estado original, utilize o script restore-backup.py, que substitui todo o conteúdo da pasta output_BI pelo conteúdo da pasta backup.

Em casos de tabelas com mesmo nome, aquela de origem do input, será renomeada com adição de ' (1)' (Ex.: 'Calendário' -> 'Calendário (1)')