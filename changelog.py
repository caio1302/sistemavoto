CHANGELOG_TEXT = """
# Versão 5.0 (Atual - Refinamento Completo e Usabilidade)

## Módulo de Usuários e Login
- **Sistema de Login/Logoff Completo:**
    - Tela de login dedicada (`LoginWindow`) no início da aplicação.
    - Autenticação de usuário e senha usando hash SHA256.
    - Opção "Lembrar-me" para login automático por token de sessão (validade de 24h), armazenado de forma segura no banco de dados e em arquivo local.
    - Opção "Efetuar Logoff" no menu para encerrar a sessão e limpar o token local/DB, retornando à tela de login.
    - `LoginWindow` refeita para ser a janela `tk.Tk` inicial, gerenciando o fluxo de inicialização da `MainApplication` de forma estável.
- **Gerenciamento de Usuários (`UserManagementWindow`):**
    - Interface dedicada para cadastrar, editar e apagar usuários.
    - Visualização de usuários em lista categorizada por nível de acesso (Administradores, Coordenadores, Assessores, Outros).
    - Campos detalhados para usuário: Nome Completo, Data de Nascimento, Telefone, E-mail, Nome de Usuário, Nível de Acesso (admin, coordenador, assessor).
    - Lógica de alteração de senha segura (campos "Nova Senha" e "Confirmar Nova Senha").
    - Campo para foto do usuário, salva na pasta `fotos_atualizadas` com nome baseado no ID do usuário (ex: `user_1.png`).
    - Preenchimento automático de dados do usuário ao selecionar na lista.
    - Proibição de apagar o usuário "admin".
- **Controle de Acesso por Permissões:**
    - Opções sensíveis no menu "Configurações" (`Gerenciar Usuários`, `Reconstruir Banco de Dados`, `Restaurar Sistema de um Backup`, `Editar Textos da Interface`) agora são visíveis e acessíveis **apenas** para usuários com nível de acesso `admin`.
    - Isso aumenta significativamente a segurança e o controle do sistema.

## Melhorias de Usabilidade e Qualidade de Dados
- **DatePicker Integrado:**
    - Campos de data agora são "somente leitura" e, ao serem clicados, abrem um seletor de calendário (`tkcalendar.Calendar`) para seleção fácil e formatação `DD/MM/YYYY`.
    - Implementado em: Data de Nascimento (cadastro de candidatos e usuários), Prazo de Tarefa.
- **Máscaras de Entrada (Validação e Formatação):**
    - Campos de Telefone e Celular agora aceitam **apenas dígitos** ao serem digitados.
    - Formatação automática no padrão `(XX) XXXX-XXXX` ou `(XX) X XXXX-XXXX` quando o campo perde o foco (`<FocusOut>`).
    - Remoção da formatação ao entrar no campo (`<FocusIn>`) para facilitar a edição.
    - Validação de formato de e-mail ao perder o foco (texto fica vermelho se inválido).
    - Funções de validação de CPF e E-mail adicionadas em `functions/formatters.py`.
- **Cálculo Dinâmico da Densidade Demográfica:**
    - A densidade demográfica (hab/km²) agora é calculada em tempo real (`População / Área`) ao gerar relatórios, tanto na UI quanto no HTML. Isso garante a precisão do dado, independentemente do valor no banco de dados.
- **Gerenciamento de Logo do Sistema:**
    - Opção "Alterar Logo do Sistema..." adicionada no menu "Configurações" (acessível por admins).
    - Novo logo é salvo em `fotos_atualizadas/logo_app.png`.
    - Todo o sistema (tela de login, relatórios UI, relatórios HTML) agora usa este logo personalizado se ele existir; caso contrário, usa o logo padrão (`saulo_logo.png`).
- **Correção de Vazamento de Scroll:**
    - Implementada lógica de `bind`/`unbind` para garantir que o scroll do mouse afete **apenas a área sob o cursor**, resolvendo o problema de rolagem em segundo plano em Listboxes, Canvas e Treeviews.

## Refatoração e Robustez Interna
- **Renomeação de Classe Principal:** `AppConsultaCandidatos` renomeada para `MainApplication` para melhor clareza e separação de responsabilidades no fluxo de inicialização.
- **Refatoração do Fluxo de Inicialização:** O `main.py` agora gerencia o ciclo de vida da aplicação de forma mais robusta, iniciando o `DataLoader` uma única vez e passando-o para as janelas (Login, MainApplication). Isso evita a duplicação de inicialização e problemas de contexto.
- **Lógica de Múltiplos Mainloops Simplificada:** Abordagem consolidada e testada para garantir que janelas modais (`Toplevel`) funcionem corretamente.
- **Melhoria da Detecção de Erros e Logging:**
    - Adição de `import logging` em todos os módulos que utilizam o logger, corrigindo `NameError`.
    - Captura e log de exceções em mais pontos críticos (e.g., carregamento de logo, operações de foto de usuário), fornecendo mais informações para depuração em `app.log`.
- **Refinamento na Estrutura do Banco de Dados:**
    - Tabela `usuarios` migrada com segurança (sem apagar `dados.db`) para incluir campos adicionais (data de nascimento, telefone, email, caminho da foto, token de login, validade do token).

# Versão 4.0 (Atual - Implementação CRM e Melhorias)
- Implementação de Funcionalidades de CRM:
    - Histórico de Interações:
        - Nova tabela `interacoes` no banco de dados.
        - Aba "Histórico de Interações e Notas" na janela `EditCandidateWindow` para visualizar, adicionar e apagar interações.
        - DTO `Interaction` criado para gerenciar dados de interação.
    - Sistema de Tarefas e Agendamentos:
        - Nova tabela `tarefas` no banco de dados.
        - Nova janela `TaskManagementWindow` acessível pelo menu principal e pela janela de edição de contato para criar, visualizar, editar, filtrar, ordenar e apagar tarefas.
        - DTO `Task` criado para gerenciar dados de tarefa.
    - Segmentação Avançada de Contatos (Tags de CRM):
        - Novas tabelas `tags` e `contato_tags` (relação muitos-para-muitos) no banco de dados.
        - Na janela `EditCandidateWindow` (aba "Informações Políticas e Tags"):
            - Exibição de tags de CRM disponíveis como checkboxes.
            - Capacidade de associar/desassociar múltiplas tags a um contato.
            - Botão para abrir o `GlobalTagManagerWindow`.
        - Nova janela `GlobalTagManagerWindow` para adicionar e apagar tags de CRM globalmente.
        - Atualização do `DataLoader` para buscar e salvar tags de CRM.
- Melhorias na Arquitetura de Dados e DTOs:
    - Schema do Banco de Dados (`database_setup.py`):
        - Refinamento das tabelas `candidatos` e `contatos` para melhor separação de dados eleitorais e de CRM.
        - Adição das tabelas `interacoes`, `tarefas`, `tags`, `contato_tags` e `usuarios` (com admin padrão).
        - Melhorias na população inicial de dados a partir dos CSVs, incluindo tratamento de tags do CSV de contatos.
    - DTOs (`dto/`):
        - `Candidate.py`: Atualizado para refletir o novo schema e incluir listas para `interacoes` e `tags`. Lógica de `from_dict` e `to_dict` aprimorada.
        - Criados `Interaction.py` e `Task.py`. `User.py` revisado.
    - `DataLoader.py`:
        - Refatorado para usar `JOINs` e carregar dados para os DTOs de forma mais completa.
        - Adicionados métodos para gerenciar interações, tarefas e tags de CRM.
        - Melhorada a lógica de busca de candidatos, aniversários e dados para dashboard.
- Melhorias na Interface do Usuário (UI) e Experiência do Usuário (UX):
    - Janela de Edição de Contato (`popups.EditCandidateWindow`):
        - Layout da aba "Histórico de Interações e Notas" significativamente melhorado com o uso de `PanedWindow` para melhor organização e visibilidade.
        - Painel esquerdo com foto e ações rápidas (Nível de Relacionamento, Criar Tarefa) mais claro.
        - Melhorias gerais no preenchimento e salvamento de dados.
    - Relatório Principal (`canvas_report.py` e `report_generator.py`):
        - Exibição correta de fotos de candidatos (customizadas, Saulo, padrão, placeholder) tanto na UI quanto no HTML.
        - Correção na formatação de dados como população e área nas tabelas de informações municipais.
        - Correção na obtenção do ano de eleição para o título do relatório HTML.
    - Popups Diversos (`popups.py`):
        - Melhorias na formatação de datas em popups de aniversário.
        - Correção de bugs e refinamentos em popups de progresso (Backup/Restore), busca global, dashboard.
        - Lógica de placeholder visual para combobox de "Nível de Relacionamento".
    - `app_ui.py`:
        - Melhorada a lógica de recarregamento de dados e reconstrução do banco.
        - Refinada a atualização da UI após edições (ex: tags da UI, dados de candidatos).
        - Correção de bugs relacionados a referências de variáveis e imports.
- Correções de Bugs Gerais:
    - Resolvidos diversos `AttributeError` e `SyntaxError` reportados.
    - Melhorado o tratamento de caminhos de arquivos e imagens.
    - Aumentada a robustez geral do sistema contra dados faltantes ou inesperados.

# Versão 3.1 (Atual)
- Correções Críticas:
    - Reestruturação do Banco de Dados (Schema):
        - Tabela 'candidatos': Adicionada coluna 'ano_eleicao' (INTEGER). Chave primária alterada para composta ('sq_candidato', 'ano_eleicao', 'cidade') para suportar múltiplas eleições e a votação do Saulo por cidade/ano. Coluna 'data_nascimento' removida.
        - Tabela 'contatos': Coluna 'data_nascimento' movida para esta tabela. Colunas de dados eleitorais ('nome_completo', 'nome_urna', 'partido', 'cargo', 'votos') removidas, garantindo que 'contatos' armazene APENAS dados de CRM.
        - Tabela 'prefeituras': Sem alterações.
    - População do Banco de Dados ('database_setup.py'):
        - Ajustado para inserir 'ano_eleicao' (2024 para eleições municipais, 2022 para Saulo) na tabela 'candidatos'.
        - Corrigida a inserção de 'data_nascimento' para ser feita na tabela 'contatos' via função auxiliar 'popular_contato_basico'.
        - Corrigida a lógica de importação de 'contato_candidatos.csv' para atualizar corretamente os campos de CRM na tabela 'contatos', lidando com nomes de coluna e garantindo que apenas campos válidos sejam atualizados.
        - Corrigido o número do Saulo para '5515' em 'saulo2022.csv' (implicitamente, pois o CSV deve ser corrigido manualmente; o código agora lê o número do CSV para o Saulo).
        - Tratamento de erro robusto com remoção do 'dados.db' em caso de falha na criação.
    - Carregamento de Dados ('data_loader.py'):
        - Todas as consultas que retornam 'Candidate' agora utilizam 'LEFT JOIN' entre 'candidatos' e 'contatos' para unir dados eleitorais e de contato.
        - Seleção explícita de colunas ('cand.coluna', 'cont.coluna') em 'SELECT' para evitar ambiguidades e garantir que todos os dados necessários para o DTO (incluindo 'uf', 'numero', 'foto_customizada' etc.) sejam carregados corretamente.
        - 'get_city_data': Agora aceita 'ano_eleicao' (padrão 2024).
        - 'get_saulo_data': Busca o Saulo pelo número '5515', 'cidade' e 'ano_eleicao_saulo' (padrão 2022), permitindo exibir a votação correta por cidade.
        - 'get_candidate_by_sq': Aceita 'ano_eleicao' e 'cidade_contexto' para buscar o registro de eleição específico.
        - 'save_candidate_data': Refatorado para salvar/atualizar APENAS os campos pertinentes à tabela 'contatos' (dados de CRM).
        - 'get_upcoming_birthdays': Busca 'data_nascimento' da tabela 'contatos', junta com 'candidatos' (filtrando por ano_eleicao e cargo) e retorna objetos 'Candidate'. Ordenação aprimorada por data e depois por nome.
        - 'get_upcoming_city_birthdays': Corrigida a lógica de cálculo de data para evitar 'ValueError' (usando 'timedelta' e validação) e aprimorada a leitura de formatos de data de aniversário de cidade (dd/mm, dd/MêsAbreviado). Ordenação aprimorada por data e depois por cidade.
        - 'search_candidates' e 'get_dashboard_data': Ajustados para utilizar o 'JOIN' e o filtro 'ano_eleicao'.

- Melhorias na Interface e Funcionalidades:
    - Exibição do Saulo: O card do Saulo agora é exibido corretamente no relatório principal e HTML com a votação específica para a cidade selecionada (buscando por ano 2022).
    - Fotos de Candidatos: Corrigida a exibição de fotos em todos os cards (Canvas e HTML) e na janela de edição, garantindo que 'ImageTk.PhotoImage' mantenha a referência e que 'get_candidate_photo_path' resolva corretamente os caminhos (customizadas, Saulo, padrão).
    - Datas de Nascimento e Idades: Exibição correta em todos os cards, baseada no campo 'data_nascimento' agora armazenado em 'contatos'.
    - Popups de Aniversário:
        - Aniversários de candidatos e cidades agora carregam e exibem corretamente, com ordenação aprimorada.
        - Cidades no popup de aniversários são clicáveis, selecionando a cidade na tela principal.
        - Resolvido erro "Não foi possível carregar dados completos de (0)" ao clicar em aniversariantes.
    - Edição de Tags ('EditTagsWindow'):
        - Correção que garante que as mudanças de tags (menu superior, labels da lista de cidades, títulos de seções) sejam atualizadas dinamicamente na 'AppConsultaCandidatos' sem a necessidade de reiniciar o aplicativo.
        - Título da janela principal ('main_window_title') e labels do menu agora são personalizáveis via tags.
    - Janela de Edição de Contatos ('EditCandidateWindow'):
        - Restaurado e funcional o botão "Habilitar Edição Avançada" para proteger/desproteger campos eleitorais (que agora são somente leitura).
        - Campos eleitorais (Nome na Urna, Cargo, Votos, Ano, etc.) agora são exibidos como somente leitura.
        - Campo "Nível de Relacionamento" movido para o painel esquerdo (abaixo de "Atualizar Foto") e seu 'ttk.Combobox' implementa uma lógica de placeholder visual ("Relacionamento ...") quando vazio.
        - Título da janela de edição agora inclui o ano da eleição do candidato.
    - Busca Global ('GlobalSearchWindow'): Aprimorada para usar o 'ano_eleicao_ref' na busca e o IID da Treeview agora é composto ('sq_candidato_ano_eleicao_cidade_normalizada') para garantir unicidade e permitir carregamento preciso na edição.
    - Foco em Popups: Todas as janelas popup agora tentam definir o foco para si mesmas automaticamente ao serem abertas, melhorando a usabilidade e a interação com o teclado (ex: tecla Esc para fechar).
    - Debugs: Todos os prints de debug de desenvolvimento foram removidos/comentados para uma experiência de console limpa.

# Versão 2.1 (Anterior)
- Correções de Bugs:
    - Restaurada a funcionalidade de 'Importar Contatos', que havia sido desativada acidentalmente em uma atualização anterior.
    - Corrigido um bug que impedia a exibição correta dos dados de 'Aniversário' e 'Idade' nos cards de candidatos após a reformulação da tela de edição.
    - Garantida a consistência na exibição de dados para todos os candidatos, incluindo o card de votação especial.

# Versão 2.0 (Anterior)
- Super Tela de Contatos: A janela de edição de contatos foi completamente reformulada. Agora utiliza um sistema de abas para organizar dezenas de novos campos, transformando o sistema em uma ferramenta de CRM político.
    - Aba Geral: Dados fundamentais do candidato.
    - Aba Inf. Políticas: Campos estratégicos como 'Nível de Relacionamento', 'Tags', 'Áreas de Interesse' e 'Perfil Político'.
    - Aba Contato: Múltiplos e-mails, telefones e contatos de assessoria.
    - Aba Social e Notas: Links para redes sociais e um campo de observações para registrar o histórico de interações.
- Layout Fixo: Na nova tela de contatos, a foto do candidato permanece sempre visível no painel esquerdo, independentemente da aba selecionada.

# Versão 1.9 (Anterior)
- Personalização Total: Adicionado o menu 'Editar Textos (tags)' em Configurações.
- Ajuda Aprimorada: A janela de 'Ajuda' foi reformulada, incluindo um botão para este 'Histórico de Atualizações'.
- Correções de Layout: Ajustes finos no alinhamento dos cards.

# Versão 1.8 (Anterior)
- Upload de Fotos: Implementada a funcionalidade para atualizar a foto de qualquer candidato.
- Armazenamento de Fotos: Fotos personalizadas são salvas em uma nova pasta 'fotos_atualizadas'.

# Versão 1.7 (Anterior)
- Padronização Visual:
    - Atualização de títulos de seção e cards de candidatos.
- Cards Interativos: Toda a área do card de um candidato tornou-se clicável.

# Versão 1.6 (Anterior)
- Menu Aniversários Aprimorado: Submenus para 'Candidatos' e 'Cidades'.
- Popup Inicial Removido: A janela de aniversariantes agora é acessada via menu.

# Versão 1.5 (Anterior)
- Navegação em Aniversários: Nomes na lista de aniversariantes tornaram-se clicáveis.
- Scroll Melhorado: Corrigido o problema de rolagem nos popups.

# Versão 1.0 (Anterior)
- Estrutura Modular e Funcionalidades Base: Lançamento com relatórios, edição de contatos, backup/restauração e importação de dados.
"""
# --- END OF FILE changelog.py ---