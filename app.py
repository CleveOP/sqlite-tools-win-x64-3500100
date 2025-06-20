from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify # Importe jsonify
import psycopg2
import os
import secrets
from datetime import datetime
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/')
def index():
    return redirect(url_for('lista_pessoas'))

@app.route('/lista_pessoas')
def lista_pessoas():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM pessoas ORDER BY lower(nome)')
        pessoas = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        pessoas = [dict(zip(colnames, row)) for row in pessoas]
    conn.close()
    return render_template('lista_pessoas.html', pessoas=pessoas)

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
        cursor.execute('SELECT id, nome, sobrenome FROM pessoas WHERE lower(tipo_cadastro) = %s ORDER BY lower(nome)', ('criança',))
        pessoas_criancas = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        pessoas_criancas = [dict(zip(colnames, row)) for row in pessoas_criancas]

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
        cursor.execute('SELECT id, nome, sobrenome FROM pessoas WHERE lower(tipo_cadastro) = %s ORDER BY lower(nome)', ('adolescente',))
        pessoas_adolescentes = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        pessoas_adolescentes = [dict(zip(colnames, row)) for row in pessoas_adolescentes]

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

# NOVA ROTA PARA AUTOCOMPLETE
@app.route('/buscar_pessoas_autocomplete')
def buscar_pessoas_autocomplete():
    termo = request.args.get('term', '').lower()
    tipo = request.args.get('tipo', '').lower()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            SELECT id, nome, sobrenome
            FROM pessoas
            WHERE lower(tipo_cadastro) = %s
              AND (lower(nome) LIKE %s OR lower(sobrenome) LIKE %s)
            ORDER BY lower(nome)
            LIMIT 10
            ''',
            (tipo, f'{termo}%', f'{termo}%')
        )
        resultados = cursor.fetchall()
    conn.close()
    sugestoes = [
        {"id": row[0], "label": f"{row[1]} {row[2]}" if row[2] else row[1]}
        for row in resultados
    ]
    return jsonify(sugestoes)


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
        return redirect(url_for('static', filename='images/placeholder-profile.png'))

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

@app.route('/balanco_chamadas')
def balanco_chamadas():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # Crianças
        cursor.execute("""
            SELECT p.id, p.nome, p.sobrenome,
                SUM(CASE WHEN c.status = 'Presente' THEN 1 ELSE 0 END) AS total_presencas,
                SUM(CASE WHEN c.status = 'Falta' THEN 1 ELSE 0 END) AS total_faltas,
                SUM(CASE WHEN c.status = 'Justificado' THEN 1 ELSE 0 END) AS total_justificados,
                COUNT(c.id) AS total_chamadas_registradas
            FROM pessoas p
            LEFT JOIN chamadas c ON p.id = c.pessoa_id
            WHERE lower(p.tipo_cadastro) = 'criança'
            GROUP BY p.id, p.nome, p.sobrenome
            ORDER BY lower(p.nome)
        """)
        balanco_criancas = [
            {
                "id": row[0],
                "nome": row[1],
                "sobrenome": row[2],
                "total_presencas": row[3] or 0,
                "total_faltas": row[4] or 0,
                "total_justificados": row[5] or 0,
                "total_chamadas_registradas": row[6] or 0,
            }
            for row in cursor.fetchall()
        ]

        # Adolescentes
        cursor.execute("""
            SELECT p.id, p.nome, p.sobrenome,
                SUM(CASE WHEN c.status = 'Presente' THEN 1 ELSE 0 END) AS total_presencas,
                SUM(CASE WHEN c.status = 'Falta' THEN 1 ELSE 0 END) AS total_faltas,
                SUM(CASE WHEN c.status = 'Justificado' THEN 1 ELSE 0 END) AS total_justificados,
                COUNT(c.id) AS total_chamadas_registradas
            FROM pessoas p
            LEFT JOIN chamadas c ON p.id = c.pessoa_id
            WHERE lower(p.tipo_cadastro) = 'adolescente'
            GROUP BY p.id, p.nome, p.sobrenome
            ORDER BY lower(p.nome)
        """)
        balanco_adolescentes = [
            {
                "id": row[0],
                "nome": row[1],
                "sobrenome": row[2],
                "total_presencas": row[3] or 0,
                "total_faltas": row[4] or 0,
                "total_justificados": row[5] or 0,
                "total_chamadas_registradas": row[6] or 0,
            }
            for row in cursor.fetchall()
        ]
    conn.close()
    return render_template(
        'balanco_chamadas.html',
        balanco_criancas=balanco_criancas,
        balanco_adolescentes=balanco_adolescentes
    )

@app.route('/atualizar_ou_criar_chamada', methods=['POST'])
def atualizar_ou_criar_chamada():
    pessoa_id = request.form.get('pessoa_id')
    data_chamada = request.form.get('data_chamada')
    status = request.form.get('status')
    if not pessoa_id or not data_chamada or not status:
        flash('Dados incompletos para atualizar chamada.', 'error')
        return redirect(request.referrer or url_for('lista_chamada_criancas'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id FROM chamadas WHERE pessoa_id = %s AND data = %s', (pessoa_id, data_chamada))
            chamada_existente = cursor.fetchone()
            if chamada_existente:
                cursor.execute('UPDATE chamadas SET status = %s WHERE id = %s', (status, chamada_existente[0]))
            else:
                cursor.execute('INSERT INTO chamadas (pessoa_id, data, status) VALUES (%s, %s, %s)', (pessoa_id, data_chamada, status))
        conn.commit()
        flash('Chamada atualizada!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao atualizar chamada: {e}', 'error')
    finally:
        conn.close()
    return redirect(request.referrer or url_for('lista_chamada_criancas'))

if __name__ == '__main__':
    app.run(debug=True)