#!/usr/bin/env python3
"""
Script para popular banco de dados com Setores e Ciclos
Executa as migrações necessárias e insere dados iniciais
"""

import os
import sys
from datetime import datetime, timedelta

# Forçar uso de SQLite local se não houver DATABASE_URL
if not os.getenv('DATABASE_URL') and not os.getenv('SQLALCHEMY_DATABASE_URI'):
    # Usar SQLite local como padrão
    db_path = os.path.join(os.path.dirname(__file__), 'multimax.db')
    os.environ['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    print(f"📊 Usando banco de dados local: {db_path}")

from multimax import create_app, db
from multimax.models import (
    User, Setor, CicloSemanal, CicloMensal, Colaborador, 
    HistoricoColaborador, AppSetting
)


def populate_database():
    """Popula o banco com dados iniciais de Setores e Ciclos"""
    app = create_app()
    
    with app.app_context():
        print("\n🔧 Iniciando população do banco de dados...\n")
        
        # 1. Criar tabelas se não existirem
        print("📋 Criando tabelas...")
        try:
            db.create_all()
            print("✅ Tabelas criadas/verificadas com sucesso\n")
        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}\n")
            return False
        
        # 2. Verificar se já existem dados
        existing_setores = Setor.query.count()
        existing_ciclos = CicloSemanal.query.count()
        
        if existing_setores > 0 or existing_ciclos > 0:
            print(f"✅ Banco já contém dados:")
            print(f"   - Setores: {existing_setores}")
            print(f"   - Ciclos: {existing_ciclos}\n")
            return True
        
        # 3. Criar Setores
        print("📍 Criando Setores...")
        setores_data = [
            {"nome": "Produção", "descricao": "Setor de produção e fabricação"},
            {"nome": "Expedição", "descricao": "Setor de expedição e logística"},
            {"nome": "Qualidade", "descricao": "Setor de controle de qualidade"},
            {"nome": "Manutenção", "descricao": "Setor de manutenção e reparo"},
            {"nome": "Administrativo", "descricao": "Setor administrativo"},
            {"nome": "Financeiro", "descricao": "Setor financeiro e contabilidade"},
            {"nome": "RH", "descricao": "Setor de recursos humanos"},
        ]
        
        setores = []
        for setor_data in setores_data:
            setor = Setor(
                nome=setor_data["nome"],
                descricao=setor_data.get("descricao"),
                ativo=True
            )
            db.session.add(setor)
            setores.append(setor)
            print(f"  ✓ {setor_data['nome']}")
        
        db.session.flush()  # Flush para gerar IDs
        print(f"✅ {len(setores)} setores criados\n")
        
        # 4. Criar Ciclos Semanais
        print("📅 Criando Ciclos Semanais...")
        today = datetime.now().date()
        ciclo_num = 1
        ciclos_semanais = []
        
        # Criar 26 semanas de ciclos (aproximadamente 6 meses)
        for week in range(26):
            data_inicio = today - timedelta(days=today.weekday()) + timedelta(weeks=week)
            data_fim = data_inicio + timedelta(days=6)
            
            ciclo = CicloSemanal(
                numero_ciclo=ciclo_num + week,
                data_inicio=data_inicio,
                data_fim=data_fim,
                ativo=(week < 4),  # Apenas os primeiros 4 ativos
                observacoes=None
            )
            db.session.add(ciclo)
            ciclos_semanais.append(ciclo)
            
            if week < 5:  # Mostrar apenas os 5 primeiros
                print(f"  ✓ Ciclo {ciclo_num + week}: {data_inicio} a {data_fim}")
        
        if len(ciclos_semanais) > 5:
            print(f"  ... e mais {len(ciclos_semanais) - 5} ciclos")
        
        print(f"✅ {len(ciclos_semanais)} ciclos semanais criados\n")
        
        # 5. Criar Ciclos Mensais
        print("📅 Criando Ciclos Mensais...")
        ciclos_mensais = []
        
        for month_offset in range(-2, 12):  # 2 meses anteriores + 12 meses futuros
            data = datetime.now() + timedelta(days=30*month_offset)
            
            ciclo = CicloMensal(
                mes=data.month,
                ano=data.year,
                data_inicio=data.replace(day=1),
                data_fim=(data.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
                fechado=(month_offset < -1)  # Meses anteriores fechados
            )
            db.session.add(ciclo)
            ciclos_mensais.append(ciclo)
        
        print(f"✅ {len(ciclos_mensais)} ciclos mensais criados\n")
        
        # 6. Criar Colaboradores de exemplo
        print("👥 Criando Colaboradores de exemplo...")
        colaboradores_data = [
            {"nome": "João Silva", "cpf": "11122233344", "funcao": "Operário", "setor_id": 1},
            {"nome": "Maria Santos", "cpf": "22233344455", "funcao": "Supervisora", "setor_id": 1},
            {"nome": "Pedro Costa", "cpf": "33344455566", "funcao": "Encarregado", "setor_id": 2},
            {"nome": "Ana Oliveira", "cpf": "44455566677", "funcao": "Analista QA", "setor_id": 3},
            {"nome": "Carlos Martins", "cpf": "55566677788", "funcao": "Técnico", "setor_id": 4},
        ]
        
        colaboradores = []
        for colab_data in colaboradores_data:
            colab = Colaborador(
                nome=colab_data["nome"],
                cpf=colab_data["cpf"],
                funcao=colab_data.get("funcao"),
                departamento="Operacional",
                ativo=True,
                horas_ciclo=40.0,
                saldo_horas=0.0
            )
            db.session.add(colab)
            colaboradores.append(colab)
            print(f"  ✓ {colab_data['nome']}")
        
        print(f"✅ {len(colaboradores)} colaboradores criados\n")
        
        # 7. Commit final
        print("💾 Salvando dados no banco de dados...")
        try:
            db.session.commit()
            print("✅ Dados salvos com sucesso!\n")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao salvar dados: {e}\n")
            return False
        
        # 8. Resumo final
        print("=" * 60)
        print("📊 RESUMO DA POPULAÇÃO DO BANCO")
        print("=" * 60)
        print(f"✅ Setores: {Setor.query.count()}")
        print(f"✅ Ciclos Semanais: {CicloSemanal.query.count()}")
        print(f"✅ Ciclos Mensais: {CicloMensal.query.count()}")
        print(f"✅ Colaboradores: {Colaborador.query.count()}")
        print("=" * 60)
        print("\n🎉 População do banco concluída com sucesso!\n")
        
        return True


if __name__ == "__main__":
    try:
        success = populate_database()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
