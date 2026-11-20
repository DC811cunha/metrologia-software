# Três estágios:
#   build — compila o frontend (usado só como etapa intermediária do `prod`);
#   prod  — servidor Caddy com o build estático em /srv (docker-compose.prod.yml; o Caddyfile é montado pelo compose);
#   dev   — servidor de desenvolvimento do Vite. É o último estágio, portanto o padrão do docker-compose.yml.

FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./

# --ignore-scripts: scripts de instalação (postinstall etc.) de dependências não rodam no build.
RUN npm ci --ignore-scripts

# Só o que o build usa (em vez de `COPY . .`, que levaria junto qualquer arquivo largado na pasta, como um .env).
COPY index.html vite.config.ts tsconfig.json tsconfig.node.json tailwind.config.js postcss.config.js ./
COPY public ./public
COPY src ./src

# Vazio = mesma origem: o navegador chama /api no próprio domínio do site, e o Caddy encaminha ao backend.
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build


FROM caddy:2-alpine AS prod

COPY --from=build /app/dist /srv

EXPOSE 80 443


FROM node:20-alpine AS dev

WORKDIR /app

# Usuário sem privilégios (`node`, já existe na imagem); o /app precisa ser dele para o Vite gravar seus temporários.
RUN chown node:node /app
USER node

COPY --chown=node:node package*.json ./

# `npm ci`: instala exatamente as versões do package-lock.json.
RUN npm ci --ignore-scripts

# Configuração e código (o docker-compose.yml de desenvolvimento ainda monta ./src/frontend por cima, para o HMR).
COPY --chown=node:node index.html vite.config.ts tsconfig.json tsconfig.node.json tailwind.config.js postcss.config.js      babel.config.js eslint.config.js jest.config.js jest.setup.ts ./
COPY --chown=node:node public ./public
COPY --chown=node:node src ./src
COPY --chown=node:node tests ./tests

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
