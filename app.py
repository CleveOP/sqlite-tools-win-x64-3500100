from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
import secrets
import datetime

app = Flask(__name__)
# Usamos uma chave secreta para segurança das sessões (flash messages)
# Para produção, você deve usar uma chave fixa e persistente (ex: de uma variável de ambiente)
# Por enquanto, mantivemos secrets.token_hex para facilitar o teste local
app.secret_key = secrets.token_hex(16) 

# Caminho para o banco de dados
# No PythonAnywhere, ele estará na mesma pasta do seu app.py (mysite)
DATABASE = 'cadastro_pessoas.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # Permite acessar colunas como dicionários
    return conn

# Função para criar as tabelas se elas não existirem
def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabela de Pessoas (AGORA COM A COLUNA 'email' INCLUÍDA)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pessoas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT NOT NULL,
            email TEXT,               -- Adicionada a coluna email
            endereco TEXT, 
            data_nascimento TEXT,
            foto_path TEXT,           -- Nome da coluna para o caminho da foto
            sobrenome TEXT,
            tipo_cadastro TEXT,
            rua TEXT,
            numero TEXT,
            bairro TEXT,
            cidade TEXT,
            estado TEXT,
            cep TEXT,
            nome_responsavel TEXT,
            telefone_responsavel TEXT
        )
    ''')

    # Tabela de Chamadas - ATUALIZADA para 'status' TEXT
    # O status pode ser 'Presente', 'Falta' ou 'Justificado'
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chamadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pessoa_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            status TEXT NOT NULL, -- Alterado de 'presente INTEGER' para 'status TEXT'
            FOREIGN KEY (pessoa_id) REFERENCES pessoas (id) ON DELETE CASCADE
            -- Adicionado ON DELETE CASCADE para remover chamadas associadas ao deletar pessoa
        )
    ''')
    conn.commit()
    conn.close()

# Garante que as tabelas sejam criadas ao iniciar o aplicativo
with app.app_context():
    create_table()

# Rota principal
@app.route('/')
def index():
    return redirect(url_for('cadastro'))

# Rota para a página de cadastro
@app.route('/cadastro', methods=('GET', 'POST'))
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form['telefone']
        
        # Usando .get() para campos que podem ser opcionais ou não estar no HTML
        email = request.form.get('email')
        endereco = request.form.get('endereco')
        data_nascimento = request.form.get('data_nascimento')
        sobrenome = request.form.get('sobrenome')
        tipo_cadastro = request.form.get('tipo_cadastro')
        rua = request.form.get('rua')
        numero = request.form.get('numero')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        cep = request.form.get('cep')
        nome_responsavel = request.form.get('nome_responsavel')
        telefone_responsavel = request.form.get('telefone_responsavel')

        foto_path_for_db = None # Variável para o caminho salvo no BD
        # Verifica se um arquivo de foto foi enviado
        if 'foto' in request.files and request.files['foto'].filename != '':
            foto = request.files['foto']
            # Define o caminho completo da pasta de upload no sistema de arquivos
            upload_dir_fs = os.path.join(app.root_path, 'static', 'fotos_pessoas')
            # Cria a pasta se não existir
            os.makedirs(upload_dir_fs, exist_ok=True)
            
            # Gera um nome de arquivo único para a foto
            filename_unique = secrets.token_hex(8) + os.path.splitext(foto.filename)[1]
            
            # Constrói o caminho completo para salvar o arquivo fisicamente no sistema de arquivos
            full_file_path_fs = os.path.join(upload_dir_fs, filename_unique)
            foto.save(full_file_path_fs)

            # Constrói o caminho RELATIVO ao diretório 'static' para salvar no banco de dados.
            # Este caminho DEVE usar forward slashes ('/') para ser compatível com URLs.
            # url_for('static', filename=...) espera um caminho relativo à pasta 'static'.
            foto_path_for_db = os.path.join('fotos_pessoas', filename_unique).replace('\\', '/')


        if not nome or not telefone:
            flash('Nome e Telefone são campos obrigatórios!', 'error')
        else:
            conn = get_db_connection()
            try:
                conn.execute('''
                    INSERT INTO pessoas (
                        nome, telefone, email, endereco, data_nascimento, foto_path,
                        sobrenome, tipo_cadastro, rua, numero, bairro, cidade, estado, cep,
                        nome_responsavel, telefone_responsavel
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    nome, telefone, email, endereco, data_nascimento, foto_path_for_db, # Usando o caminho corrigido
                    sobrenome, tipo_cadastro, rua, numero, bairro, cidade, estado, cep,
                    nome_responsavel, telefone_responsavel
                ))
                conn.commit()
                flash('Pessoa cadastrada com sucesso!', 'success')
                return redirect(url_for('lista_pessoas'))
            except sqlite3.Error as e:
                flash(f'Erro ao cadastrar pessoa: {e}', 'error')
                conn.rollback() # Desfaz a operação em caso de erro
            finally:
                conn.close()
    
    return render_template('cadastro.html', pessoa=None)

# Rota para listar todas as pessoas
@app.route('/lista_pessoas')
def lista_pessoas():
    conn = get_db_connection()
    pessoas = conn.execute('SELECT * FROM pessoas ORDER BY nome').fetchall()
    conn.close()
    return render_template('lista_pessoas.html', pessoas=pessoas)

# Rota para editar uma pessoa existente
@app.route('/editar_pessoa/<int:pessoa_id>', methods=('GET', 'POST'))
def editar_pessoa(pessoa_id):
    conn = get_db_connection()
    pessoa = conn.execute('SELECT * FROM pessoas WHERE id = ?', (pessoa_id,)).fetchone()
    
    if pessoa is None:
        flash('Pessoa não encontrada!', 'error')
        conn.close()
        return redirect(url_for('lista_pessoas'))

    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form['telefone']
        
        email = request.form.get('email')
        endereco = request.form.get('endereco')
        data_nascimento = request.form.get('data_nascimento')
        sobrenome = request.form.get('sobrenome')
        tipo_cadastro = request.form.get('tipo_cadastro')
        rua = request.form.get('rua')
        numero = request.form.get('numero')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        cep = request.form.get('cep')
        nome_responsavel = request.form.get('nome_responsavel')
        telefone_responsavel = request.form.get('telefone_responsavel')
        
        # Mantém o caminho da foto existente por padrão
        foto_path_for_db = pessoa['foto_path'] # Obtém o caminho da foto atual do banco de dados (já deve estar no formato correto)
        
        # Lógica para remover foto se o checkbox for marcado
        if request.form.get('remover_foto') == 'on':
            if foto_path_for_db: # Se houver um caminho salvo no BD
                # Constrói o caminho completo do arquivo no sistema de arquivos para remoção
                full_file_path_fs = os.path.join(app.root_path, 'static', foto_path_for_db)
                if os.path.exists(full_file_path_fs):
                    os.remove(full_file_path_fs)
            foto_path_for_db = None # Define como None após a remoção

        # Se uma nova foto for enviada, processa o upload e remove a antiga (se existir)
        if 'foto' in request.files and request.files['foto'].filename != '':
            nova_foto = request.files['foto']
            # Define o caminho completo da pasta de upload no sistema de arquivos
            upload_dir_fs = os.path.join(app.root_path, 'static', 'fotos_pessoas')
            os.makedirs(upload_dir_fs, exist_ok=True) 
            
            # Se já existe uma foto, exclui a antiga antes de salvar a nova
            if foto_path_for_db: # Se houver um caminho salvo no BD (e não foi removido pelo checkbox)
                full_file_path_fs_old = os.path.join(app.root_path, 'static', foto_path_for_db)
                if os.path.exists(full_file_path_fs_old):
                    os.remove(full_file_path_fs_old)
            
            filename_unique = secrets.token_hex(8) + os.path.splitext(nova_foto.filename)[1]
            # Constrói o caminho completo para salvar o arquivo fisicamente no sistema de arquivos
            full_file_path_fs = os.path.join(upload_dir_fs, filename_unique)
            nova_foto.save(full_file_path_fs)

            # Constrói o caminho RELATIVO ao diretório 'static' para salvar no banco de dados.
            foto_path_for_db = os.path.join('fotos_pessoas', filename_unique).replace('\\', '/')
            
        if not nome or not telefone:
            flash('Nome e Telefone são campos obrigatórios!', 'error')
        else:
            try:
                conn.execute('''
                    UPDATE pessoas SET 
                        nome = ?, telefone = ?, email = ?, endereco = ?, data_nascimento = ?, foto_path = ?,
                        sobrenome = ?, tipo_cadastro = ?, rua = ?, numero = ?, bairro = ?, cidade = ?, estado = ?, cep = ?,
                        nome_responsavel = ?, telefone_responsavel = ?
                    WHERE id = ?
                ''', (
                    nome, telefone, email, endereco, data_nascimento, foto_path_for_db, # Usando o caminho corrigido
                    sobrenome, tipo_cadastro, rua, numero, bairro, cidade, estado, cep,
                    nome_responsavel, telefone_responsavel,
                    pessoa_id 
                ))
                conn.commit()
                flash('Pessoa atualizada com sucesso!', 'success')
                return redirect(url_for('lista_pessoas'))
            except sqlite3.Error as e:
                flash(f'Erro ao atualizar pessoa: {e}', 'error')
                conn.rollback()
            finally:
                conn.close()
    
    # Se for uma requisição GET, busca os dados da pessoa para preencher o formulário
    # Já buscamos no início da função, então apenas passamos para o template
    conn.close()
    return render_template('cadastro.html', pessoa=pessoa)

# Rota para excluir uma pessoa
@app.route('/excluir_pessoa/<int:pessoa_id>', methods=('POST',))
def excluir_pessoa(pessoa_id):
    conn = get_db_connection()
    try:
        # Obter o caminho da foto antes de excluir o registro para remover o arquivo físico
        pessoa_para_excluir = conn.execute('SELECT foto_path FROM pessoas WHERE id = ?', (pessoa_id,)).fetchone()
        
        conn.execute('DELETE FROM pessoas WHERE id = ?', (pessoa_id,))
        conn.commit()
        
        # Excluir o arquivo da foto do sistema de arquivos
        if pessoa_para_excluir and pessoa_para_excluir['foto_path']:
            # Constrói o caminho completo do arquivo no sistema de arquivos a partir do caminho relativo
            caminho_completo_foto_fs = os.path.join(app.root_path, 'static', pessoa_para_excluir['foto_path'])
            if os.path.exists(caminho_completo_foto_fs):
                os.remove(caminho_completo_foto_fs)
        
        flash('Pessoa excluída com sucesso!', 'success')
    except sqlite3.Error as e:
        flash(f'Erro ao excluir pessoa: {e}', 'error')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('lista_pessoas'))

# Rota para a página de controle de chamadas
@app.route('/lista_chamada', methods=('GET',)) # Apenas GET para exibir a lista
def lista_chamada():
    conn = get_db_connection()
    pessoas = conn.execute('SELECT id, nome, sobrenome, tipo_cadastro FROM pessoas ORDER BY nome').fetchall()

    # Pega a data da requisição GET, ou a data de hoje se não for fornecida
    data_para_exibir = request.args.get('data', datetime.date.today().isoformat())

    # Busca o status de presença para a data selecionada
    chamadas_do_dia = conn.execute(
        'SELECT pessoa_id, status FROM chamadas WHERE data = ?',
        (data_para_exibir,)
    ).fetchall()

    # Cria um mapa para facilitar a verificação no template
    chamadas_map = {}
    for chamada in chamadas_do_dia:
        chamadas_map[chamada['pessoa_id']] = chamada['status'] # Armazena o status como texto

    conn.close()
    
    # Passa as pessoas, a data selecionada e o mapa de chamadas para o template
    return render_template('lista_chamada.html', pessoas=pessoas, data_para_exibir=data_para_exibir, chamadas_map=chamadas_map)

# Rota para registrar presença/ausência (POST) - Rota separada para o formulário POST
@app.route('/registrar_chamada', methods=('POST',))
def registrar_chamada():
    conn = get_db_connection()
    data_chamada = request.form['data_chamada']

    try:
        for key, value in request.form.items():
            if key.startswith('status_'): # Prefixo do nome do campo de rádio
                pessoa_id = key.split('_')[1]
                status = value # O valor já é 'Presente', 'Falta' ou 'Justificado'
                
                # Verifica se já existe um registro para esta pessoa nesta data
                registro_existente = conn.execute(
                    'SELECT id FROM chamadas WHERE pessoa_id = ? AND data = ?',
                    (pessoa_id, data_chamada)
                ).fetchone()
                
                if registro_existente:
                    # Atualiza o registro existente
                    conn.execute(
                        'UPDATE chamadas SET status = ? WHERE id = ?',
                        (status, registro_existente['id'])
                    )
                else:
                    # Insere um novo registro
                    conn.execute(
                        'INSERT INTO chamadas (pessoa_id, data, status) VALUES (?, ?, ?)',
                        (pessoa_id, data_chamada, status)
                    )
        conn.commit()
        flash('Chamada registrada com sucesso!', 'success')
    except sqlite3.Error as e:
        flash(f'Erro ao registrar chamada: {e}', 'error')
        conn.rollback()
    finally:
        conn.close()
    # Redireciona de volta para a lista de chamada, mantendo a data selecionada
    return redirect(url_for('lista_chamada', data=data_chamada))

# Rota para exibir balanço de chamadas por pessoa
@app.route('/balanco_chamadas')
def balanco_chamadas():
    conn = get_db_connection()
    
    # Consulta para obter o balanço de chamadas por pessoa
    # COMENTADO: Este é o código original que busca todos juntos
    # balanco = conn.execute('''
    #     SELECT
    #         p.id,
    #         p.nome,
    #         p.sobrenome,
    #         p.tipo_cadastro,
    #         COUNT(c.id) AS total_chamadas_registradas,
    #         SUM(CASE WHEN c.status = 'Presente' THEN 1 ELSE 0 END) AS total_presencas,
    #         SUM(CASE WHEN c.status = 'Falta' THEN 1 ELSE 0 END) AS total_faltas,
    #         SUM(CASE WHEN c.status = 'Justificado' THEN 1 ELSE 0 END) AS total_justificados
    #     FROM pessoas p
    #     LEFT JOIN chamadas c ON p.id = c.pessoa_id
    #     GROUP BY p.id, p.nome, p.sobrenome, p.tipo_cadastro
    #     ORDER BY p.nome
    # ''').fetchall()

    # NOVA CONSULTA: Balanço para Crianças
    balanco_criancas = conn.execute('''
        SELECT
            p.id,
            p.nome,
            p.sobrenome,
            p.tipo_cadastro,
            COUNT(c.id) AS total_chamadas_registradas,
            SUM(CASE WHEN c.status = 'Presente' THEN 1 ELSE 0 END) AS total_presencas,
            SUM(CASE WHEN c.status = 'Falta' THEN 1 ELSE 0 END) AS total_faltas,
            SUM(CASE WHEN c.status = 'Justificado' THEN 1 ELSE 0 END) AS total_justificados
        FROM pessoas p
        LEFT JOIN chamadas c ON p.id = c.pessoa_id
        WHERE p.tipo_cadastro = 'Criança'
        GROUP BY p.id, p.nome, p.sobrenome, p.tipo_cadastro
        ORDER BY p.nome
    ''').fetchall()

    # NOVA CONSULTA: Balanço para Adolescentes
    balanco_adolescentes = conn.execute('''
        SELECT
            p.id,
            p.nome,
            p.sobrenome,
            p.tipo_cadastro,
            COUNT(c.id) AS total_chamadas_registradas,
            SUM(CASE WHEN c.status = 'Presente' THEN 1 ELSE 0 END) AS total_presencas,
            SUM(CASE WHEN c.status = 'Falta' THEN 1 ELSE 0 END) AS total_faltas,
            SUM(CASE WHEN c.status = 'Justificado' THEN 1 ELSE 0 END) AS total_justificados
        FROM pessoas p
        LEFT JOIN chamadas c ON p.id = c.pessoa_id
        WHERE p.tipo_cadastro = 'Adolescente'
        GROUP BY p.id, p.nome, p.sobrenome, p.tipo_cadastro
        ORDER BY p.nome
    ''').fetchall()
    
    conn.close()
    return render_template('balanco_chamadas.html', 
        balanco_criancas=balanco_criancas, 
        balanco_adolescentes=balanco_adolescentes)

if __name__ == '__main__':
    # Para garantir que as mudanças na tabela de chamadas entrem em vigor,
    # você pode precisar apagar o arquivo 'cadastro_pessoas.db' localmente
    # e reiniciar o aplicativo, ou adicionar lógica de migração de banco de dados.
    # Em um ambiente de produção, migrações seriam gerenciadas com ferramentas como Alembic.
    app.run(debug=True)