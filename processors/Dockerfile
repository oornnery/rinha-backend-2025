# Use a imagem oficial do Node.js
FROM node:20-slim

# Defina o diretório de trabalho
WORKDIR /usr/src/app

# Copie os arquivos de dependência
COPY package*.json ./

# Instale as dependências
RUN npm install

# Copie o código da aplicação
COPY . .

# Exponha a porta
EXPOSE 3001
EXPOSE 3002

# Comando para iniciar o servidor
CMD [ "node", "index.js" ]
