FROM node:20

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ENV HOSTNAME=0.0.0.0

CMD ["sh", "-c", "npm run dev -- --hostname 0.0.0.0"]