from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from ..password_hash import check_password_hash, generate_password_hash
from ..models import User, SystemLog, UserLogin
from .. import db

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('usuarios.perfil'))
    if request.method == 'POST':
        action = request.form.get('action', 'login')
        
        # Cadastro de novo usuário
        if action == 'register':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            name = request.form.get('name', '').strip()
            
            # Validações
            if not username or len(username) < 3:
                flash('O nome de usuário deve ter pelo menos 3 caracteres.', 'danger')
                return render_template('login.html', show_register=True)
            
            if not password or len(password) < 4:
                flash('A senha deve ter pelo menos 4 caracteres.', 'danger')
                return render_template('login.html', show_register=True)
            
            if password != confirm_password:
                flash('As senhas não coincidem.', 'danger')
                return render_template('login.html', show_register=True)
            
            if not name:
                name = username
            
            # Verificar se usuário já existe
            if User.query.filter_by(username=username).first():
                flash('Este nome de usuário já está em uso.', 'danger')
                return render_template('login.html', show_register=True)
            
            # Criar novo usuário com nível visualizador
            try:
                new_user = User()
                new_user.username = username
                new_user.name = name[:100]  # Limitar tamanho
                new_user.password_hash = generate_password_hash(password)
                new_user.nivel = 'visualizador'  # Sempre visualizador para novos cadastros
                
                db.session.add(new_user)
                db.session.commit()
                
                flash('Cadastro realizado com sucesso! Faça login para continuar.', 'success')
                return render_template('login.html', show_register=False)
            except Exception as e:
                db.session.rollback()
                import logging
                logging.getLogger(__name__).error(f"Erro ao cadastrar usuário: {e}", exc_info=True)
                flash('Erro ao realizar cadastro. Tente novamente.', 'danger')
                return render_template('login.html', show_register=True)
        
        # Login normal
        else:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                try:
                    log = SystemLog()
                    log.origem = 'Acesso'
                    log.evento = 'login'
                    log.detalhes = 'Acesso ao sistema'
                    log.usuario = user.name
                    db.session.add(log)
                    # registrar histórico de login (todos os usuários)
                    try:
                        ip = request.remote_addr or request.environ.get('HTTP_X_FORWARDED_FOR') or ''
                    except (AttributeError, KeyError):
                        ip = ''
                    try:
                        ua = request.headers.get('User-Agent', '')
                    except (AttributeError, KeyError):
                        ua = ''
                    try:
                        ul = UserLogin()
                        ul.user_id = user.id
                        ul.username = user.username
                        ul.ip_address = ip[:255] if ip else ''  # Limitar tamanho
                        ul.user_agent = ua[:500] if ua else ''  # Limitar tamanho
                        db.session.add(ul)
                    except Exception as e:
                        # Log mas não falha o login
                        import logging
                        logging.getLogger(__name__).warning(f"Erro ao registrar login: {e}")
                    try:
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        import logging
                        logging.getLogger(__name__).error(f"Erro ao salvar log de login: {e}")
                except Exception as e:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                    import logging
                    logging.getLogger(__name__).error(f"Erro ao registrar login: {e}")
                flash('Login realizado com sucesso!', 'success')
                return redirect(url_for('usuarios.perfil'))
            else:
                flash('Nome de usuário ou senha inválidos.', 'danger')
    
    show_register = request.args.get('register', '').lower() == 'true'
    return render_template('login.html', show_register=show_register)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('usuarios.perfil'))
    return redirect(url_for('auth.login', register='true'))

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('auth.login'))
