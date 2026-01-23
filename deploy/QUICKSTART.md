# 🚀 MultiMax Quick Start (5 Minutos)

> Instalação rápida em Ubuntu 24.04 LTS

## ⚡ Instruções Rápidas

```bash
# 1. Fazer login como root
sudo su -

# 2. Download setup script
curl -sO https://raw.githubusercontent.com/SrLuther/MultiMax/main/deploy/scripts/setup.sh
chmod +x setup.sh

# 3. Executar (tempo total: 5-10 min)
bash setup.sh

# 4. Você verá:
#   ✓ Sistema atualizado
#   ✓ Python 3.11 instalado
#   ✓ PostgreSQL configurado
#   ✓ Código clonado
#   ✓ Nginx + SSL
#   ✓ Systemd service

# 5. Editar configurações
sudo nano /opt/multimax/.env
# Altere: SECRET_KEY e domínio em nginx

# 6. Gerar certificado SSL (Let's Encrypt)
sudo certbot certonly --nginx -d seu-dominio.com

# 7. Iniciar!
sudo systemctl restart multimax nginx

# 8. Pronto! Acesse: https://seu-dominio.com
```

---

## 📋 Pós-Deploy (Imediato)

```bash
# Verificar status
sudo systemctl status multimax postgresql nginx

# Ver logs
sudo journalctl -u multimax -f

# Testar acesso
curl https://seu-dominio.com

# Health check
curl https://seu-dominio.com/health
```

---

## 🔧 Próximos Passos

1. **Criar usuário admin:**
   ```bash
   cd /opt/multimax/app
   source /opt/multimax/venv/bin/activate
   python -c "
   from multimax import create_app, db
   from multimax.models import User
   app = create_app()
   with app.app_context():
       user = User(email='seu@email.com')
       user.set_password('senha123')
       user.is_admin = True
       db.session.add(user)
       db.session.commit()
   print('✓ Admin criado')
   "
   ```

2. **Agendar backups:**
   ```bash
   echo "0 2 * * * /usr/local/bin/multimax-db-backup.sh" | sudo crontab -
   ```

3. **Ler documentação completa:**
   - [README.md](./docs/README.md) - Guia completo
   - [SECURITY.md](./docs/SECURITY.md) - Segurança
   - [TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) - Problemas

---

## ⚠️ Coisas Importantes

```
🔐 SEGURANÇA
✓ Altere SECRET_KEY em .env
✓ Altere senha do banco
✓ Use certificado SSL válido (Let's Encrypt)
✓ Ative firewall (UFW)

📊 MONITORAMENTO  
✓ Ver logs: journalctl -u multimax -f
✓ Status: sudo multimax-status.sh
✓ Backups: ls /opt/multimax/backups/

🆘 PROBLEMAS?
✓ Check README.md Troubleshooting
✓ Ver logs: tail -100 /var/log/multimax/app.log
✓ Test: curl https://seu-dominio.com
```

---

## 📞 Comandos Mais Usados

| Comando | Efeito |
|---------|--------|
| `systemctl status multimax` | Ver status |
| `journalctl -u multimax -f` | Ver logs tempo real |
| `multimax-restart.sh` | Reiniciar |
| `multimax-logs.sh` | Ver últimos logs |
| `multimax-db-backup.sh` | Fazer backup |
| `multimax-status.sh` | Status completo |

---

**Bem-vindo ao MultiMax!** 🎉
