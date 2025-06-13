from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
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
    # Exemplo simples, personalize conforme sua necessidade
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT data, status, COUNT(*) FROM chamadas GROUP BY data, status ORDER BY data DESC')
        balanco = cursor.fetchall()
    conn.close()
    return render_template('balanco_chamadas.html', balanco=balanco)

@app.route('/autocomplete_pessoas')
def autocomplete_pessoas():
    termo = request.args.get('q', '').strip()
    if not termo:
        return jsonify([])
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT nome, sobrenome FROM pessoas WHERE nome ILIKE %s OR sobrenome ILIKE %s ORDER BY nome LIMIT 10",
            (f"{termo}%", f"{termo}%")
        )
        nomes = [f"{row[0]} {row[1]}" if row[1] else row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(nomes)

@app.route('/autocomplete_chamada')
def autocomplete_chamada():
    termo = request.args.get('q', '').strip()
    tipo = request.args.get('tipo', '').strip()  # 'Criança' ou 'Adolescente'
    if not termo or not tipo:
        return jsonify([])
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT nome, sobrenome FROM pessoas
            WHERE tipo_cadastro = %s
              AND (
                nome ILIKE %s OR sobrenome ILIKE %s
              )
            ORDER BY nome
            LIMIT 10
            """,
            (tipo, f"{termo}%", f"{termo}%")
        )
        nomes = [f"{row[0]} {row[1]}" if row[1] else row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(nomes)

if __name__ == '__main__':
    app.run(debug=True)