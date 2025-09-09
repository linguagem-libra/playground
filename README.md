## Libra Playground - Versão Experimental

Este é um playground web da linguagem Libra. Ele permite que usuários testem e executem código escrito em Libra diretamente no navegador, sem a necessidade de baixar, instalar ou configurar nada localmente.

Importante: Esta é uma versão EXTREMAMENTE EXPERIMENTAL, desenvolvida apenas para fins de testes, aprendizado e experimentação com a linguagem Libra. Ainda não é adequada para uso em produção ou projetos reais.

### Características:

- Editor de código interativo com realce de sintaxe (via CodeMirror)

- Execução de código em tempo real com saída transmitida via Server-Sent Events (SSE)

- Limite de segurança para tempo de execução e quantidade de saída exibida

- Interface limpa, responsiva e leve

- Nenhuma instalação necessária do lado do usuário

### Requisitos (para rodar localmente):

- Python 3

- Flask

- A linguagem Libra instalada e configurada no sistema (variável de ambiente LIBRA_PATH)

### Aviso:

Como este projeto executa código em tempo real no servidor, nunca deve ser exposto publicamente sem mecanismos de segurança adequados, como sandbox, autenticação e limitação de recursos.