## Objetivo

* Tornar a aplicação acessível a outros dispositivos da mesma rede local usando o IP do seu PC e a porta 5000.

## Passos

1. **Descobrir o IP do PC**

* No Windows, execute `ipconfig` e anote o valor de `IPv4` (ex.: `192.168.0.25`).

1. **Iniciar o servidor ouvindo na rede**

* Iniciar o Flask ouvindo em todas as interfaces: `.venv\Scripts\python -m flask --app app run --host 0.0.0.0 --port 5000`.

* Se a porta 5000 já estiver em uso, usar outra porta (ex.: `5010`) e ajustar o firewall.

1. **Liberar a porta no Firewall do Windows**

* Criar regra de entrada para TCP 5000: `New-NetFirewallRule -DisplayName "MultiMax Flask 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow`.

* Se usar outra porta, trocar `5000` pelo número escolhido.

1. **Validar acesso**

* No PC local: abrir `http://127.0.0.1:5000/` e conferir a Home.

* Em outro dispositivo da rede (celular ou outro PC): abrir `http://<IP_DO_PC>:5000/` (ex.: `http://192.168.0.25:5000/`).

* Verificar `http://<IP_DO_PC>:5000/health` para status `ok`.

1. **Encerrar quando terminar**

* Para parar o servidor, use `CTRL+C` na janela do terminal.

## Observações

* Este modo é apenas para visualização em rede local; para produção, considere um servidor WSGI (ex.: `waitress`) e regras de firewall mais restritivas.

* Se houver antivírus/firewall de terceiros, pode ser necessário liberar a porta também nele.

## Próximo passo

* Com sua confirmação, executo os comandos de inicialização e abro a regra de firewall para deixar acessível em `http://<IP_DO_PC>:5000/`.

