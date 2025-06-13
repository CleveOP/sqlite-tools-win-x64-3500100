from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import psycopg2
import os
import secrets
from datetime import datetime
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

DATABASE_URL = os.environ.get('DATABASE_URL')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pessoas (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            telefone TEXT NOT NULL,
            email TEXT,
            endereco TEXT,
            data_nascimento TEXT,
            foto BYTEA,  -- campo para imagem binária
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
            id SERIAL PRIMARY KEY,
            pessoa_id INTEGER NOT NULL REFERENCES pessoas(id) ON DELETE CASCADE,
            data DATE NOT NULL,
            status TEXT NOT NULL
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

        foto_bytes = None
        if 'foto' in request.files and request.files['foto'].filename != '':
            foto = request.files['foto']
            if foto and allowed_file(foto.filename):
                foto_bytes = foto.read()
            else:
                flash('Tipo de arquivo de foto não permitido!', 'error')

        if not nome or not telefone:
            flash('Nome e Telefone são campos obrigatórios!', 'error')
        else:
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO pessoas (
                            nome, telefone, email, endereco, data_nascimento, foto,
                            sobrenome, tipo_cadastro, rua, numero, bairro, cidade, estado, cep,
                            nome_responsavel, telefone_responsavel
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        nome, telefone, email, endereco, data_nascimento, foto_bytes,
                        sobrenome, tipo_cadastro, rua, numero, bairro, cidade, estado, cep,
                        nome_responsavel, telefone_responsavel
                    ))
                conn.commit()
                flash('Pessoa cadastrada com sucesso!', 'success')
                return redirect(url_for('lista_pessoas'))
            except Exception as e:
                flash(f'Erro ao cadastrar pessoa: {e}', 'error')
                conn.rollback()
            finally:
                conn.close()

    return render_template('cadastro.html', pessoa=None)

@app.route('/lista_pessoas')
def lista_pessoas():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM pessoas ORDER BY nome')
        pessoas = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        pessoas = [dict(zip(colnames, row)) for row in pessoas]
    conn.close()
    return render_template('lista_pessoas.html', pessoas=pessoas)

@app.route('/imagem_pessoa/<int:pessoa_id>')
def imagem_pessoa(pessoa_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT foto FROM pessoas WHERE id = %s', (pessoa_id,))
        row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return send_file(BytesIO(row[0]), mimetype='image/png')
    else:
        return redirect(url_for('static', filename='img/sem_foto.png'))

@app.route('/editar_pessoa/<int:pessoa_id>', methods=('GET', 'POST'))
def editar_pessoa(pessoa_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM pessoas WHERE id = %s', (pessoa_id,))
        pessoa_row = cursor.fetchone()
        colnames = [desc[0] for desc in cursor.description]
        pessoa = dict(zip(colnames, pessoa_row)) if pessoa_row else None

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

        foto_bytes = pessoa['foto']

        if request.form.get('remover_foto') == 'true':
            foto_bytes = None

        if 'foto' in request.files and request.files['foto'].filename != '':
            nova_foto = request.files['foto']
            if nova_foto and allowed_file(nova_foto.filename):
                foto_bytes = nova_foto.read()
            else:
                flash('Tipo de arquivo de foto não permitido!', 'error')

        if not nome or not telefone:
            flash('Nome e Telefone são campos obrigatórios!', 'error')
        else:
            try:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE pessoas SET
                            nome = %s, telefone = %s, email = %s, endereco = %s, data_nascimento = %s, foto = %s,
                            sobrenome = %s, tipo_cadastro = %s, rua = %s, numero = %s, bairro = %s, cidade = %s, estado = %s, cep = %s,
                            nome_responsavel = %s, telefone_responsavel = %s
                        WHERE id = %s
                    ''', (
                        nome, telefone, email, endereco, data_nascimento, foto_bytes,
                        sobrenome, tipo_cadastro, rua, numero, bairro, cidade, estado, cep,
                        nome_responsavel, telefone_responsavel,
                        pessoa_id
                    ))
                conn.commit()
                flash('Pessoa atualizada com sucesso!', 'success')
                return redirect(url_for('lista_pessoas'))
            except Exception as e:
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
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM pessoas WHERE id = %s', (pessoa_id,))
            conn.commit()
        flash('Pessoa excluída com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir pessoa: {e}', 'error')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('lista_pessoas'))

@app.route('/lista_chamada_criancas', methods=['GET'])
def lista_chamada_criancas():
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

    with conn.cursor() as cursor:
        cursor.execute("SELECT id, nome, sobrenome FROM pessoas WHERE tipo_cadastro = 'Criança' ORDER BY nome")
        pessoas_criancas = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        pessoas_criancas = [dict(zip(colnames, row)) for row in pessoas_criancas]

        # ALTERAÇÃO: buscar também o id da chamada
        cursor.execute('SELECT id, pessoa_id, status FROM chamadas WHERE data = %s', (data_para_exibir,))
        chamadas = cursor.fetchall()
        chamadas_map = {c[1]: {'id': c[0], 'status': c[2]} for c in chamadas}

    conn.close()

    return render_template(
        'lista_chamada_criancas.html',
        pessoas_criancas=pessoas_criancas,
        data_para_exibir=data_para_exibir,
        chamadas_map=chamadas_map
    )

@app.route('/lista_chamada_adolescentes', methods=['GET'])
def lista_chamada_adolescentes():
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

    with conn.cursor() as cursor:
        cursor.execute("SELECT id, nome, sobrenome FROM pessoas WHERE tipo_cadastro = 'Adolescente' ORDER BY nome")
        pessoas_adolescentes = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        pessoas_adolescentes = [dict(zip(colnames, row)) for row in pessoas_adolescentes]

        # ALTERAÇÃO: buscar também o id da chamada
        cursor.execute('SELECT id, pessoa_id, status FROM chamadas WHERE data = %s', (data_para_exibir,))
        chamadas = cursor.fetchall()
        chamadas_map = {c[1]: {'id': c[0], 'status': c[2]} for c in chamadas}

    conn.close()

    return render_template(
        'lista_chamada_adolescentes.html',
        pessoas_adolescentes=pessoas_adolescentes,
        data_para_exibir=data_para_exibir,
        chamadas_map=chamadas_map
    )

@app.route('/lista_chamada_dupla', methods=['GET'])
def lista_chamada_dupla():
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

    with conn.cursor() as cursor:
        cursor.execute("SELECT id, nome, sobrenome FROM pessoas WHERE tipo_cadastro = 'Criança' ORDER BY nome")
        pessoas_criancas = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        pessoas_criancas = [dict(zip(colnames, row)) for row in pessoas_criancas]

        cursor.execute("SELECT id, nome, sobrenome FROM pessoas WHERE tipo_cadastro = 'Adolescente' ORDER BY nome")
        pessoas_adolescentes = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        pessoas_adolescentes = [dict(zip(colnames, row)) for row in pessoas_adolescentes]

        cursor.execute('SELECT pessoa_id, status FROM chamadas WHERE data = %s', (data_para_exibir,))
        chamadas = cursor.fetchall()
        chamadas_map = {c[0]: c[1] for c in chamadas}

    conn.close()

    return render_template(
        'lista_chamada_dupla.html',
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
        with conn.cursor() as cursor:
            for key, value in request.form.items():
                if key.startswith('status_'):
                    pessoa_id = key.split('_')[1]
                    status = value
                    cursor.execute(
                        'SELECT 1 FROM chamadas WHERE pessoa_id = %s AND data = %s',
                        (pessoa_id, data_chamada)
                    )
                    existe = cursor.fetchone()
                    if not existe:
                        cursor.execute(
                            'INSERT INTO chamadas (pessoa_id, data, status) VALUES (%s, %s, %s)',
                            (pessoa_id, data_chamada, status)
                        )
            conn.commit()
        flash('Chamada registrada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao registrar chamada: {e}', 'error')
        conn.rollback()
    finally:
        conn.close()

    return redirect(url_for('cadastro'))

@app.route('/balanco_chamadas')
def balanco_chamadas():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('''
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
        ''')
        balanco_criancas = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        balanco_criancas = [dict(zip(colnames, row)) for row in balanco_criancas]

        cursor.execute('''
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
        ''')
        balanco_adolescentes = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        balanco_adolescentes = [dict(zip(colnames, row)) for row in balanco_adolescentes]

    conn.close()
    return render_template('balanco_chamadas.html',
                           balanco_criancas=balanco_criancas,
                           balanco_adolescentes=balanco_adolescentes)

@app.route('/editar_chamada/<int:chamada_id>', methods=['GET', 'POST'])
def editar_chamada(chamada_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM chamadas WHERE id = %s', (chamada_id,))
        chamada = cursor.fetchone()
        colnames = [desc[0] for desc in cursor.description]
        chamada = dict(zip(colnames, chamada)) if chamada else None

        # Descobre o tipo da pessoa para redirecionar corretamente
        tipo_cadastro = None
        if chamada:
            cursor.execute('SELECT tipo_cadastro FROM pessoas WHERE id = %s', (chamada['pessoa_id'],))
            tipo_cadastro_row = cursor.fetchone()
            if tipo_cadastro_row:
                tipo_cadastro = tipo_cadastro_row[0]

    if not chamada:
        flash('Chamada não encontrada!', 'error')
        conn.close()
        return redirect(url_for('lista_chamada_criancas'))

    if request.method == 'POST':
        novo_status = request.form.get('status')
        try:
            with conn.cursor() as cursor:
                cursor.execute('UPDATE chamadas SET status = %s WHERE id = %s', (novo_status, chamada_id))
            conn.commit()
            flash('Chamada atualizada com sucesso!', 'success')
            # Redireciona para a lista correta
            if tipo_cadastro == 'Criança':
                return redirect(url_for('lista_chamada_criancas'))
            elif tipo_cadastro == 'Adolescente':
                return redirect(url_for('lista_chamada_adolescentes'))
            else:
                return redirect(url_for('lista_chamada_criancas'))
        except Exception as e:
            flash(f'Erro ao atualizar chamada: {e}', 'error')
            conn.rollback()
        finally:
            conn.close()

    conn.close()
    return render_template('editar_chamada.html', chamada=chamada)

@app.route('/atualizar_chamada', methods=['POST'])
def atualizar_chamada():
    chamada_id = request.form.get('chamada_id')
    novo_status = request.form.get('status')
    if not chamada_id or not novo_status:
        return jsonify({'success': False, 'message': 'Dados incompletos.'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('UPDATE chamadas SET status = %s WHERE id = %s', (novo_status, chamada_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/atualizar_ou_criar_chamada', methods=['POST'])
def atualizar_ou_criar_chamada():
    pessoa_id = request.form.get('pessoa_id')
    data_chamada = request.form.get('data_chamada')
    status = request.form.get('status')
    chamada_id = request.form.get('chamada_id')

    if not pessoa_id or not data_chamada or not status:
        return jsonify({'success': False, 'message': 'Dados incompletos.'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if chamada_id:
                # Atualiza chamada existente
                cursor.execute('UPDATE chamadas SET status = %s WHERE id = %s', (status, chamada_id))
            else:
                # Verifica se já existe chamada para pessoa/data (evita duplicidade)
                cursor.execute('SELECT id FROM chamadas WHERE pessoa_id = %s AND data = %s', (pessoa_id, data_chamada))
                chamada_existente = cursor.fetchone()
                if chamada_existente:
                    cursor.execute('UPDATE chamadas SET status = %s WHERE id = %s', (status, chamada_existente[0]))
                else:
                    cursor.execute('INSERT INTO chamadas (pessoa_id, data, status) VALUES (%s, %s, %s) RETURNING id', (pessoa_id, data_chamada, status))
                    chamada_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'success': True, 'chamada_id': chamada_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()