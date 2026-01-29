FROM node:20-alpine
WORKDIR /app
ARG NEXT_PUBLIC_API_BASE
ARG NEXT_PUBLIC_WISE_API_BASE
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
ENV NEXT_PUBLIC_WISE_API_BASE=$NEXT_PUBLIC_WISE_API_BASE
COPY package.json package-lock.json* /app/
RUN npm install
COPY src /app/src
COPY next.config.mjs /app/next.config.mjs
COPY tsconfig.json /app/tsconfig.json
COPY tailwind.config.ts /app/tailwind.config.ts
COPY postcss.config.js /app/postcss.config.js
COPY next-env.d.ts /app/next-env.d.ts
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build
CMD ["npm", "run", "start", "--", "-p", "3000"]
