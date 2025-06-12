  from flask import Flask, render_template, request, redirect, url_for, flash
    import sqlite3
    import os
    import secrets
    from datetime import datetime

    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

    DATABASE = 'cadastro_pessoas.db'

    UPLOAD_FOLDER = 'static/fotos_pessoas'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def get_db_connection():
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn

    def create_table():
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pessoas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT NOT NULL,
                email TEXT,
                endereco TEXT,
                data_nascimento TEXT,
                foto_path TEXT,
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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chamadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pessoa_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (pessoa_id) REFERENCES pessoas (id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        conn.close()

    with app.app_context():
        create_table()

    @app.route('/')
    def index():
        return redirect(url_for('cadastro'))

    @app.route('/cadastro', methods=('GET', 'POST'))
    def cadastro():
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

            foto_path_for_db = None
            if 'foto' in request.files and request.files['foto'].filename != '':
                foto = request.files['foto']
                if foto and allowed_file(foto.filename):
                    upload_dir_fs = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
                    os.makedirs(upload_dir_fs, exist_ok=True)

                    filename_unique = secrets.token_hex(8) + os.path.splitext(foto.filename)[1]
                    full_file_path_fs = os.path.join(upload_dir_fs, filename_unique)
                    foto.save(full_file_path_fs)

                    foto_path_for_db = os.path.join(app.config['UPLOAD_FOLDER'], filename_unique).replace('\\', '/')
                else:
                    flash('Tipo de arquivo de foto não permitido!', 'error')

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
                        nome, telefone, email, endereco, data_nascimento, foto_path_for_db,
                        sobrenome, tipo_cadastro, rua, numero, bairro, cidade, estado, cep,
                        nome_responsavel, telefone_responsavel
                    ))
                    conn.commit()
                    flash('Pessoa cadastrada com sucesso!', 'success')
                    return redirect(url_for('lista_pessoas'))
                except sqlite3.Error as e:
                    flash(f'Erro ao cadastrar pessoa: {e}', 'error')
                    conn.rollback()
                finally:
                    conn.close()

        return render_template('cadastro.html', pessoa=None)

    @app.route('/lista_pessoas')
    def lista_pessoas():
        conn = get_db_connection()
        pessoas = conn.execute('SELECT * FROM pessoas ORDER BY nome').fetchall()
        conn.close()
        return render_template('lista_pessoas.html', pessoas=pessoas)

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

            foto_path_for_db = pessoa['foto_path']

            # Lógica para remover foto existente
            if request.form.get('remover_foto') == 'true' and foto_path_for_db:
                full_file_path_fs = os.path.join(app.root_path, 'static', foto_path_for_db)
                if os.path.exists(full_file_path_fs):
                    os.remove(full_file_path_fs)
                foto_path_for_db = None

            # Lógica para fazer upload de nova foto
            if 'foto' in request.files and request.files['foto'].filename != '':
                nova_foto = request.files['foto']
                if nova_foto and allowed_file(nova_foto.filename):
                    upload_dir_fs = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
                    os.makedirs(upload_dir_fs, exist_ok=True)

                    if foto_path_for_db and request.form.get('remover_foto') != 'true':
                        full_file_path_fs_old = os.path.join(app.root_path, 'static', foto_path_for_db)
                        if os.path.exists(full_file_path_fs_old):
                            os.remove(full_file_path_fs_old)

                    filename_unique = secrets.token_hex(8) + os.path.splitext(nova_foto.filename)[1]
                    full_file_path_fs = os.path.join(upload_dir_fs, filename_unique)
                    nova_foto.save(full_file_path_fs)

                    foto_path_for_db = os.path.join(app.config['UPLOAD_FOLDER'], filename_unique).replace('\\', '/')
                else:
                    flash('Tipo de arquivo de foto não permitido!', 'error')

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
                        nome, telefone, email, endereco, data_nascimento, foto_path_for_db,
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

        conn.close()
        return render_template('cadastro.html', pessoa=pessoa)

    @app.route('/excluir_pessoa/<int:pessoa_id>', methods=('POST',))
    def excluir_pessoa(pessoa_id):
        conn = get_db_connection()
        try:
            pessoa_para_excluir = conn.execute('SELECT foto_path FROM pessoas WHERE id = ?', (pessoa_id,)).fetchone()

            conn.execute('DELETE FROM pessoas WHERE id = ?', (pessoa_id,))
            conn.commit()

            if pessoa_para_excluir and pessoa_para_excluir['foto_path']:
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

    @app.route('/lista_chamada', methods=['GET'])
    def lista_chamada():
        conn = get_db_connection()

        data_selecionada_str = request.args.get('data')
        if data_selecionada_str:
            try:
                data_para_exibir = datetime.strptime(data_selecionada_str, '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                flash('Data inválida.', 'error')
                data_para_exibir = datetime.now().strftime('%Y-%m-%d')
        else:
            data_para_exibir = datetime.now().strftime('%Y-%m-%d')

        # Buscar todas as pessoas cadastradas
        pessoas_db = conn.execute('SELECT * FROM pessoas ORDER BY nome').fetchall()

        pessoas_criancas = []
        pessoas_adolescentes = []

        print(f"--- Debug: Total de pessoas do DB: {len(pessoas_db)} ---")
        for pessoa in pessoas_db:
            pessoa_dict = dict(pessoa)
            print(f"  Debug: Pessoa ID: {pessoa_dict['id']}, Nome: {pessoa_dict['nome']}, Tipo: '{pessoa_dict['tipo_cadastro']}'") # Imprime o tipo_cadastro
            if pessoa_dict['tipo_cadastro'] == 'Criança':
                pessoas_criancas.append(pessoa_dict)
            elif pessoa_dict['tipo_cadastro'] == 'Adolescente':
                pessoas_adolescentes.append(pessoa_dict)

        print(f"--- Debug: Crianças encontradas: {len(pessoas_criancas)} ---")
        print(f"--- Debug: Adolescentes encontrados: {len(pessoas_adolescentes)} ---")

        # Buscar os registros de chamada para a data selecionada
        chamadas = conn.execute('SELECT pessoa_id, status FROM chamadas WHERE data = ?', (data_para_exibir,)).fetchall()
        chamadas_map = {c['pessoa_id']: c['status'] for c in chamadas}

        conn.close()

        return render_template(
            'lista_chamada.html',
            pessoas_criancas=pessoas_criancas,
            pessoas_adolescentes=pessoas_adolescentes,
            data_para_exibir=data_para_exibir,
            chamadas_map=chamadas_map
        )

    @app.route('/registrar_chamada', methods=('POST',))
    def registrar_chamada():
        conn = get_db_connection()
        data_chamada = request.form['data_chamada']

        try:
            conn.execute('DELETE FROM chamadas WHERE data = ?', (data_chamada,))

            for key, value in request.form.items():
                if key.startswith('status_'):
                    pessoa_id = key.split('_')[1]
                    status = value
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
        return redirect(url_for('lista_chamada', data=data_chamada))

    @app.route('/balanco_chamadas')
    def balanco_chamadas():
        conn = get_db_connection()

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
    