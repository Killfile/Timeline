FROM nginx:alpine

WORKDIR /usr/share/nginx/html

# Copy static files
COPY index.html .
COPY *.js .
COPY style.css .

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
