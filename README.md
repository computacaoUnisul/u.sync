# Requisitos
A versão atual apenas funciona em SOs baseadas em Linux ou BSD.
- python >= 3.7.1
- pip3

## Instalação
Antes de iniciar, certifique-se de ter lido os requisitos.

### Baixe o repo 
Faça o download do repositório com:
```bash
git clone https://github.com/computacaoUnisul/u.sync.git
```

### Instale as dependências
O projeto usa o [scrapy](https://github.com/scrapy/scrapy) para automatizar os processos HTTP cliente/servidor, além dos ferramentas para extrair dados de texto HTML. Também é utilizado um projeto chamado [scrapy-cookies](https://github.com/scrapedia/scrapy-cookies), que lida com persistência dos cookies de autenticação em memória. Para instalar, entre no diretório raiz do projeto e execute do terminal:

OBS: utilize o binário do seu sistema, no meu caso é o ```pip```, mas se você ter o pip instalado para python versão 2.7, provavelmente o certo para você será ```pip3```.
```bash
pip install -r requirements.txt
```

## Como funciona
Como usamos o scrapy, este nos dá a disposição objetos chamados de ```Spider``` para lidar com a busca que queremos fazer. Cada operação realizada para buscar os materiais na internet é feita por uma Spider diferente, afim de simplificar e especializar cada operação. Tais operações são:
- login no sistema EVA
- extrair todas as matérias do usuário
- extrair todos os materiais de cada matéria
- sincronizar todos os materiais com uma pasta local
- logout do sistema EVA

Você deve estar se perguntando o seguinte: como é possível que os Spiders de extração, que são totalmente independentes, conseguem extrair os dados sem terem feito login?
Bom a resposta é simples, eles não conseguem! Como dito anteriormente, usamos cookies persistentes e assim conseguimos libertar as Spiders. Esses cookies persistentes ficam armazenados em um arquivo, assim como seu navegador também faz.  

## Como usar
Um shell script foi criado com a finalidade de juntar a execução de cada Spider e tranformar em um programa que sincroniza todos os materiais. O script está na pasta raiz com o nome de ```sync.sh```. Aqui darei mais detalhes sobre como usar o script.

### Parâmetros
- -k : Induz o script a manter sua login ativo, ou seja, seus cookies permanecerão salvos, e o logout da conta não será feito. Para o sistema do EVA, existirá um login ativo para o seu usuário.
- -m : Executar o Spider especial do Max. Este não precisa de autenticação.
- -c : Remove qualquer arquivo de sincronização da última vez em que foi executado.
- -x : Especifica um arquivo com os dados de autenticação no EVA. A primeira linha deve ser o usuário e a segunda linha a senha. A principal finalidade é para simplificar testes, então use com precaução, e acima de tudo deixe esse arquivo apenas legível para o seu usuário.
- -d : Caminho para o diretório onde deve ser feita a sincronização. Por padrão sempre será salvo no caminho relativo ```src/book_bot/downloads/```. 

### Sincronizar com o Max Spider
O script anteriormente citado nos limita a executar uma operação por vez, ou o EVA ou o Max, não os dois. Se este é o seu objetivo, existe um outro script que sincroniza os dois, também está na raiz com o nome de ```sync_all.sh```. O script apenas executa o EVA e depois chama o Max Spider, no final é apenas um `helper`.
Os parâmetros são os mesmos do script `sync.sh`.

## Continua...